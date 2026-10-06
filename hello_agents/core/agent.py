"""Agent基类"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING, AsyncGenerator
import asyncio
from .message import Message
from .llm import HelloAgentsLLM
from .config import Config
from .budget import BudgetExceeded
from .components import AgentComponents, build_agent_components, register_default_tools
from .lifecycle import AgentEvent, EventType, LifecycleHook, ExecutionContext

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry
    from ..observability.trace_logger import TraceLogger
    from ..tools.tool_filter import ToolFilter


class Agent(ABC):
    """Agent基类

    集成能力：
    - HistoryManager: 历史管理与压缩
    - ObservationTruncator: 工具输出截断
    - TraceLogger: 可观测性（JSONL + HTML）
    - ToolRegistry: 工具管理（可选）
    - SkillLoader: 知识外化（可选）

    历史由 HistoryManager 管理，通过 add_message、clear_history、get_history 操作。
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional['ToolRegistry'] = None,
        components: Optional[AgentComponents] = None
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()
        self._component_options = components
        if any((self.config.summary_llm_provider, self.config.summary_llm_model, self.config.subagent_light_llm_provider, self.config.subagent_light_llm_model)):
            raise ValueError("独立摘要或子代理模型请通过 AgentComponents 注入完整 LLM 实例")

        # 工具注册表（可选）
        self.tool_registry = tool_registry

        # 显式注入与默认装配共用一个入口；保留公开组件属性。
        self.components = build_agent_components(self.config, self.llm.model, components)
        self.history_manager = self.components.history_manager
        self.token_counter = self.components.token_counter
        self.truncator = self.components.truncator
        self.session_store = self.components.session_store
        self.skill_loader = self.components.skill_loader
        self._history_token_count = self.token_counter.count_messages(
            self.history_manager.get_history()
        )

        # 新增：可观测性组件
        from hello_agents.observability import TraceLogger

        self.trace_logger: Optional[TraceLogger] = None
        if self.config.trace_enabled:
            self.trace_logger = TraceLogger(
                output_dir=self.config.trace_dir,
                sanitize=self.config.trace_sanitize,
                html_include_raw_response=self.config.trace_html_include_raw_response
            )
            # 记录会话开始
            self.trace_logger.log_event(
                "session_start",
                {
                    "agent_name": self.name,
                    "agent_type": self.__class__.__name__,
                    "config": self.config.model_dump()
                }
            )

        from datetime import datetime

        # 会话元数据（用于保存）
        self._session_metadata = {
            "created_at": datetime.now().isoformat(),
            "total_tokens": 0,
            "total_steps": 0,
            "duration_seconds": 0
        }
        self._start_time = datetime.now()

        register_default_tools(self)

    @property
    def _history(self) -> List[Message]:
        """访问 HistoryManager 的当前历史。"""
        return self.history_manager.get_history()

    @_history.setter
    def _history(self, value: List[Message]):
        """替换完整历史并重新计算 Token 数。"""
        self.history_manager.clear()
        for msg in value:
            self.history_manager.append(msg)
        self._history_token_count = self.token_counter.count_messages(
            self.history_manager.get_history()
        )

    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """运行Agent（同步版本）"""
        pass

    # ==================== 异步生命周期方法 ====================

    async def arun(
        self,
        input_text: str,
        on_start: LifecycleHook = None,
        on_step: LifecycleHook = None,
        on_finish: LifecycleHook = None,
        on_error: LifecycleHook = None,
        **kwargs
    ) -> str:
        """
        异步执行 Agent（基础版本）

        默认实现：在线程池中运行同步 run() 方法
        子类可以覆盖此方法实现更复杂的异步逻辑（如工具并行）

        Args:
            input_text: 输入文本
            on_start: Agent 开始执行时的钩子
            on_step: 每个推理步骤的钩子
            on_finish: Agent 执行完成时的钩子
            on_error: 发生错误时的钩子
            **kwargs: 其他参数

        Returns:
            执行结果

        Example:
            >>> agent = SimpleAgent(...)
            >>> result = await agent.arun("Hello", on_start=my_hook)
        """
        # 触发开始事件
        await self._emit_event(
            EventType.AGENT_START,
            on_start,
            input_text=input_text
        )

        try:
            # 默认实现：在线程池中运行同步 run()
            result = await asyncio.to_thread(self.run, input_text, **kwargs)

            # 触发完成事件
            await self._emit_event(
                EventType.AGENT_FINISH,
                on_finish,
                result=result
            )

            return result

        except Exception as e:
            # 触发错误事件
            await self._emit_event(
                EventType.AGENT_ERROR,
                on_error,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def arun_stream(
        self,
        input_text: str,
        **kwargs
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        流式执行 Agent（基础版本）

        默认实现：执行 arun() 并返回开始/完成事件
        子类应该覆盖此方法实现真正的流式输出

        Args:
            input_text: 输入文本
            **kwargs: 其他参数

        Yields:
            AgentEvent: 生命周期事件

        Example:
            >>> async for event in agent.arun_stream("Hello"):
            ...     print(event.type, event.data)
        """
        # 开始事件
        yield AgentEvent.create(
            EventType.AGENT_START,
            self.name,
            input_text=input_text
        )

        # 执行
        try:
            result = await self.arun(input_text, **kwargs)

            # 完成事件
            yield AgentEvent.create(
                EventType.AGENT_FINISH,
                self.name,
                result=result
            )
        except Exception as e:
            # 错误事件
            yield AgentEvent.create(
                EventType.AGENT_ERROR,
                self.name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def _emit_event(
        self,
        event_type: EventType,
        hook: LifecycleHook,
        **data
    ):
        """触发事件并调用钩子

        Args:
            event_type: 事件类型
            hook: 生命周期钩子（可选）
            **data: 事件数据
        """
        event = AgentEvent.create(event_type, self.name, **data)

        if hook:
            try:
                # 使用 asyncio.wait_for 设置超时
                timeout = getattr(self.config, 'hook_timeout_seconds', 5.0)
                await asyncio.wait_for(hook(event), timeout=timeout)
            except asyncio.TimeoutError:
                # 钩子超时不应中断主流程
                if hasattr(self, 'trace_logger') and self.trace_logger:
                    self.trace_logger.log_event(
                        "hook_timeout",
                        {"event_type": event_type.value, "timeout": timeout}
                    )
            except Exception as e:
                # 钩子异常不应中断主流程
                if hasattr(self, 'trace_logger') and self.trace_logger:
                    self.trace_logger.log_event(
                        "hook_error",
                        {"event_type": event_type.value, "error": str(e)}
                    )

    def add_message(self, message: Message):
        """添加消息到历史记录

        自动检查是否需要压缩历史
        """
        self.history_manager.append(message)

        # 增量更新 Token 计数
        new_tokens = self.token_counter.count_message(message)
        self._history_token_count += new_tokens

        # 检查是否需要压缩
        if self._should_compress():
            self._compress_history()

        # 自动保存（如果启用）
        if self.config.auto_save_enabled and self.session_store is not None:
            history_len = len(self.history_manager.get_history())
            if history_len % self.config.auto_save_interval == 0:
                self._auto_save()

    def clear_history(self):
        """清空历史记录"""
        self.history_manager.clear()
        # 重置 Token 计数
        self._history_token_count = 0
        self.token_counter.clear_cache()

    def get_history(self) -> List[Message]:
        """获取历史记录"""
        return self.history_manager.get_history()

    def _should_compress(self) -> bool:
        """判断是否需要压缩历史

        基于缓存的 Token 数判断（高性能）
        使用增量计算，避免重复遍历历史

        Returns:
            是否需要压缩
        """
        threshold = int(self.config.context_window * self.config.compression_threshold)
        return self._history_token_count > threshold

    def _compress_history(self):
        """压缩历史

        默认使用简单摘要策略
        如果启用 enable_smart_compression，子类可以重写此方法调用 LLM 生成智能摘要
        """
        history = self.history_manager.get_history()

        if self.config.enable_smart_compression:
            # 智能摘要（需要子类实现）
            summary = self._generate_smart_summary(history)
        else:
            # 简单摘要
            summary = self._generate_simple_summary(history)

        self.history_manager.compress(summary)

        # 重新计算 Token 数（压缩后）
        new_history = self.history_manager.get_history()
        self._history_token_count = self.token_counter.count_messages(new_history)

    def _generate_simple_summary(self, history: List[Message]) -> str:
        """生成简单摘要（统计信息）

        Args:
            history: 历史消息列表

        Returns:
            摘要文本
        """
        rounds = self.history_manager.estimate_rounds()
        user_msgs = sum(1 for msg in history if msg.role == "user")
        assistant_msgs = sum(1 for msg in history if msg.role == "assistant")

        return f"""此会话包含 {rounds} 轮对话：
- 用户消息：{user_msgs} 条
- 助手消息：{assistant_msgs} 条
- 总消息数：{len(history)} 条

（历史已压缩，保留最近 {self.history_manager.min_retain_rounds} 轮完整对话）"""

    def _generate_smart_summary(self, history: List[Message]) -> str:
        """生成智能摘要（调用 LLM）

        使用轻量 LLM 生成结构化摘要，保留关键信息：
        - 任务目标
        - 关键决策
        - 已完成工作
        - 待处理事项
        - 重要发现

        Args:
            history: 历史消息列表

        Returns:
            摘要文本
        """
        # 1. 提取要压缩的历史片段
        boundaries = self.history_manager.find_round_boundaries()
        if len(boundaries) <= self.history_manager.min_retain_rounds:
            return self._generate_simple_summary(history)

        # 保留最近 N 轮，压缩之前的
        keep_from_index = boundaries[-self.history_manager.min_retain_rounds]
        to_compress = history[:keep_from_index]

        if not to_compress:
            return self._generate_simple_summary(history)

        # 2. 构建摘要 Prompt
        history_text = self._format_history_for_summary(to_compress)

        summary_prompt = f"""请将以下对话历史压缩为结构化摘要，保留关键信息：

## 对话历史
{history_text}

## 摘要要求
1. **任务目标**：用户想要完成什么？
2. **关键决策**：做了哪些重要决定？
3. **已完成工作**：完成了哪些任务？（列表形式）
4. **待处理事项**：还有什么未完成？
5. **重要发现**：有哪些关键信息或问题？

请用简洁的中文输出，每部分不超过 3 行。"""

        # 3. 调用轻量 LLM（节省成本）
        try:
            summary_llm = self._get_summary_llm()

            messages = [
                {"role": "system", "content": "你是一个专业的对话摘要助手，擅长提取关键信息。"},
                {"role": "user", "content": summary_prompt}
            ]

            # 非流式调用，快速获取结果
            summary = summary_llm.invoke(
                messages,
                temperature=self.config.summary_temperature,
                max_tokens=self.config.summary_max_tokens
            )

            summary = getattr(summary, "content", summary)
            if not isinstance(summary, str) or not summary.strip():
                raise ValueError("摘要模型未返回非空文本")
            return f"""## 历史摘要（{len(to_compress)} 条消息）
{summary}

---
（已压缩，保留最近 {self.history_manager.min_retain_rounds} 轮完整对话）"""

        except BudgetExceeded:
            raise

        except Exception as e:
            # 回退到简单摘要
            print(f"⚠️ 智能摘要生成失败: {e}，使用简单摘要")
            return self._generate_simple_summary(history)

    def _format_history_for_summary(self, history: List[Message]) -> str:
        """格式化历史消息用于摘要生成

        Args:
            history: 历史消息列表

        Returns:
            格式化后的历史文本
        """
        formatted_lines = []
        for msg in history:
            # 截断过长消息（避免摘要 Prompt 过大）
            content = msg.content[:500] if len(msg.content) > 500 else msg.content
            formatted_lines.append(f"[{msg.role}]: {content}")

        return "\n\n".join(formatted_lines)

    def _get_summary_llm(self):
        injected = getattr(self._component_options, "summary_llm", None)
        if injected is not None:
            return injected
        if self.config.summary_llm_provider or self.config.summary_llm_model:
            raise ValueError("独立摘要模型请通过 AgentComponents(summary_llm=...) 注入完整配置")
        return self.llm

    def __str__(self) -> str:
        return f"Agent(name={self.name}, model={self.llm.model})"

    def __repr__(self) -> str:
        return self.__str__()

    # ==================== 工具调用通用能力（从 FunctionCallAgent 提取）====================

    def _build_tool_schemas(self) -> List[Dict[str, Any]]:
        """构建工具 JSON Schema

        统一的工具 schema 构建逻辑，支持：
        - Tool 对象（带参数定义）
        - 函数工具（简化注册）

        Returns:
            工具 schema 列表
        """
        if not self.tool_registry:
            return []

        schemas: List[Dict[str, Any]] = []

        # 完整的 Schema 由工具提供，声明无效时必须明确报错。
        for tool in self.tool_registry.get_all_tools():
            schemas.append(tool.to_openai_schema())

        # 2. 处理函数工具
        function_map = getattr(self.tool_registry, "_functions", {})
        for name, info in function_map.items():
            schemas.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": info.get("description", ""),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "input": {
                                "type": "string",
                                "description": "输入文本"
                            }
                        },
                        "required": ["input"]
                    }
                }
            })

        return schemas

    @staticmethod
    def _map_parameter_type(param_type: str) -> str:
        """将工具参数类型映射为 JSON Schema 允许的类型

        Args:
            param_type: 工具参数类型

        Returns:
            JSON Schema 类型
        """
        normalized = (param_type or "").lower()
        if normalized in {"string", "number", "integer", "boolean", "array", "object"}:
            return normalized
        return "string"

    def _convert_parameter_types(self, tool_name: str, param_dict: Dict[str, Any]) -> Dict[str, Any]:
        """根据工具定义转换参数类型

        Args:
            tool_name: 工具名称
            param_dict: 参数字典

        Returns:
            类型转换后的参数字典
        """
        if not self.tool_registry:
            return param_dict

        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            return param_dict

        try:
            tool_params = tool.get_parameters()
        except Exception:
            return param_dict

        type_mapping = {param.name: param.type for param in tool_params}
        converted: Dict[str, Any] = {}

        for key, value in param_dict.items():
            param_type = type_mapping.get(key)
            if not param_type:
                converted[key] = value
                continue

            try:
                normalized = param_type.lower()
                if normalized in {"number", "float"}:
                    converted[key] = float(value)
                elif normalized in {"integer", "int"}:
                    converted[key] = int(value)
                elif normalized in {"boolean", "bool"}:
                    if isinstance(value, bool):
                        converted[key] = value
                    elif isinstance(value, (int, float)):
                        converted[key] = bool(value)
                    elif isinstance(value, str):
                        converted[key] = value.lower() in {"true", "1", "yes"}
                    else:
                        converted[key] = bool(value)
                else:
                    converted[key] = value
            except (TypeError, ValueError):
                converted[key] = value

        return converted

    def _execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """执行工具调用并返回字符串结果

        统一的工具执行逻辑，支持：
        - Tool 对象（带类型转换）
        - 函数工具（简化调用）

        Args:
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果（字符串格式）
        """
        if not self.tool_registry:
            return "❌ 错误：未配置工具注册表"

        try:
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                parameters = self._convert_parameter_types(tool_name, arguments)
            else:
                # 保留现有函数工具的单 input 调用约定。
                parameters = arguments.get("input", "")
            response = self.tool_registry.execute_tool(tool_name, parameters)
            return response.to_model_text()
        except Exception as exc:
            return f"❌ 工具调用失败：{exc}"

    # ==================== 会话持久化能力 ====================

    def _auto_save(self):
        """自动保存会话（静默失败）"""
        if self.session_store is None:
            return

        try:
            self.session_store.save(
                agent_config=self._get_agent_config(),
                history=self.history_manager.get_history(),
                tool_schema_hash=self._compute_tool_schema_hash(),
                read_cache=self._get_read_cache(),
                metadata=self._session_metadata,
                session_name="session-auto"
            )
        except Exception as e:
            # 自动保存失败不影响主流程
            if self.config.debug:
                print(f"⚠️ 自动保存失败: {e}")

    def save_session(self, session_name: str) -> str:
        """手动保存会话

        Args:
            session_name: 会话名称（不含 .json 后缀）

        Returns:
            保存的文件路径

        Raises:
            RuntimeError: 会话持久化未启用
        """
        if self.session_store is None:
            raise RuntimeError("会话持久化未启用，请使用 Config(session_enabled=True) 或注入 AgentComponents(session_store=...)")

        # 更新元数据
        from datetime import datetime
        self._session_metadata["duration_seconds"] = (datetime.now() - self._start_time).total_seconds()

        filepath = self.session_store.save(
            agent_config=self._get_agent_config(),
            history=self.history_manager.get_history(),
            tool_schema_hash=self._compute_tool_schema_hash(),
            read_cache=self._get_read_cache(),
            metadata=self._session_metadata,
            session_name=session_name
        )

        return filepath

    def load_session(self, filepath: str, check_consistency: bool = True) -> None:
        """加载会话

        Args:
            filepath: 会话文件路径
            check_consistency: 是否检查环境一致性

        Raises:
            RuntimeError: 会话持久化未启用
            FileNotFoundError: 文件不存在
        """
        if self.session_store is None:
            raise RuntimeError("会话持久化未启用，请使用 Config(session_enabled=True) 或注入 AgentComponents(session_store=...)")

        if getattr(self, "_run_active", False):
            raise RuntimeError("运行中不能加载另一个会话")

        # 修改当前会话前，先校验完整快照。
        session_data = self.session_store.load(filepath)
        from .message import Message
        restored_history = [Message.from_dict(item) for item in session_data.get("history", [])]
        restored_metadata = session_data.get("metadata", {})
        restored_cache = session_data.get("read_cache", {})
        if not isinstance(restored_metadata, dict) or not isinstance(restored_cache, dict):
            raise ValueError("会话 metadata 和 read_cache 必须是对象")
        restored_tokens = self.token_counter.count_messages(restored_history)

        # 环境一致性检查
        if check_consistency:
            # 检查配置一致性
            config_check = self.session_store.check_config_consistency(
                saved_config=session_data.get("agent_config", {}),
                current_config=self._get_agent_config()
            )

            if not config_check["consistent"]:
                print("⚠️ 环境配置不一致：")
                for warning in config_check["warnings"]:
                    print(f"  - {warning}")

            # 检查工具 Schema 一致性
            tool_check = self.session_store.check_tool_schema_consistency(
                saved_hash=session_data.get("tool_schema_hash", ""),
                current_hash=self._compute_tool_schema_hash()
            )

            if tool_check["changed"]:
                print(f"⚠️ 工具定义已变化")
                print(f"  建议：{tool_check['recommendation']}")

        # 恢复历史
        self.history_manager.clear()
        for message in restored_history:
            self.history_manager.append(message)
        self._history_token_count = restored_tokens

        # 恢复元数据
        self._session_metadata = restored_metadata
        if hasattr(self, "_messages_since_save"):
            self._messages_since_save = 0

        # 恢复 Read 工具缓存
        if self.tool_registry is not None:
            self.tool_registry.read_metadata_cache = restored_cache

        print(f"✅ 会话已恢复：{session_data.get('session_id', 'unknown')}")

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有可用会话

        Returns:
            会话信息列表
        """
        if self.session_store is None:
            return []

        return self.session_store.list_sessions()

    def _get_agent_config(self) -> Dict[str, Any]:
        """获取 Agent 配置信息

        Returns:
            配置字典
        """
        config = {
            "name": self.name,
            "agent_type": self.__class__.__name__,
            "llm_provider": getattr(self.llm, 'provider', 'unknown'),
            "llm_model": getattr(self.llm, 'model_id', getattr(self.llm, 'model', 'unknown'))
        }

        # 添加 max_steps（如果存在）
        if hasattr(self, 'max_steps'):
            config["max_steps"] = self.max_steps

        return config

    def _compute_tool_schema_hash(self) -> str:
        """对模型可见的完整接口约定计算哈希，不受注册顺序影响。"""
        if self.tool_registry is None:
            return "no-tools"
        import json
        from hashlib import sha256

        schemas = sorted(self._build_tool_schemas(), key=lambda schema: schema["function"]["name"])
        payload = json.dumps(schemas, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return sha256(payload.encode("utf-8")).hexdigest()[:16]

    def _get_read_cache(self) -> Dict[str, Dict]:
        """获取 Read 工具的元数据缓存

        Returns:
            元数据缓存字典
        """
        if self.tool_registry and hasattr(self.tool_registry, 'read_metadata_cache'):
            return self.tool_registry.read_metadata_cache
        return {}

    # ==================== 子代理机制 ====================

    def run_as_subagent(
        self,
        task: str,
        tool_filter: Optional['ToolFilter'] = None,
        return_summary: bool = True,
        max_steps_override: Optional[int] = None
    ) -> Dict[str, Any]:
        """运行隔离的子会话，随后恢复空闲父 Agent 的状态。

        返回成功标记、元数据，以及摘要或结果。注册表映射
        与读取缓存相互隔离，但共享工具产生的外部修改不会回滚。
        不会将子会话内容自动保存到父会话文件。
        """
        from time import perf_counter
        from .subagent_scope import subagent_scope

        with subagent_scope(self, tool_filter, max_steps_override):
            started = perf_counter()
            error = None
            success = False
            try:
                result = self.run(task)
                last_run = getattr(self, "last_run", None)
                success = last_run is None or last_run.status == "completed"
                if not success:
                    error = f"子任务未完成：{last_run.status}"
            except Exception as exc:
                error = str(exc)
                result = f"执行失败: {error}"
            metadata = self._get_subagent_metadata(perf_counter() - started, error)
            if return_summary:
                return {"success": success,
                        "summary": self._generate_subagent_summary(task, result, metadata),
                        "metadata": metadata}
            return {"success": success, "result": result, "metadata": metadata}

    def _apply_tool_filter(self, tool_filter):
        """切换到独立的名称映射，不修改调用方的注册表。"""
        original = self.tool_registry
        self.tool_registry = original.fork(tool_filter.filter(original.list_tools()))
        return original

    def _restore_tools(self, original_tools):
        self.tool_registry = original_tools

    def _get_subagent_metadata(self, duration: float, error: Optional[str]) -> Dict[str, Any]:
        """获取子代理执行元数据

        Args:
            duration: 执行时长（秒）
            error: 错误信息（可选）

        Returns:
            元数据字典
        """
        history = self.history_manager.get_history()

        # 估算步数（用户+助手消息对）
        steps = sum(1 for msg in history if msg.role == "assistant")

        # 估算 Token 数（简化：字符数 / 4）
        total_chars = sum(len(msg.content) for msg in history)
        tokens = total_chars // 4

        # 提取使用的工具
        tools_used = self._extract_tools_from_history(history)

        metadata = {
            "steps": steps,
            "tokens": tokens,
            "duration_seconds": round(duration, 2),
            "tools_used": tools_used
        }

        if error:
            metadata["error"] = error

        return metadata

    def _extract_tools_from_history(self, history: List[Message]) -> List[str]:
        """从历史中提取使用的工具

        Args:
            history: 历史消息列表

        Returns:
            工具名称列表（去重）
        """
        tools = set()

        for msg in history:
            native = (msg.metadata or {}).get("model_message", {})
            for call in native.get("tool_calls", []):
                tools.add(call.get("function", {}).get("name", ""))
            # 检查 tool_calls（FunctionCallAgent）
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if isinstance(tool_call, dict) and 'function' in tool_call:
                        tools.add(tool_call['function'].get('name', ''))

            # 检查内容中的工具调用（ReActAgent）
            if msg.role == "assistant" and "Action:" in msg.content:
                import re
                matches = re.findall(r'Action:\s*(\w+)\[', msg.content)
                tools.update(matches)

        return sorted(list(tools))

    def _generate_subagent_summary(
        self,
        task: str,
        result: str,
        metadata: Dict[str, Any]
    ) -> str:
        """生成子代理执行摘要

        Args:
            task: 任务描述
            result: 执行结果
            metadata: 执行元数据

        Returns:
            摘要文本
        """
        # 截断结果（避免摘要过长）
        max_result_len = 500
        if len(result) > max_result_len:
            result_preview = result[:max_result_len] + "..."
        else:
            result_preview = result

        # 构建摘要
        summary_parts = [
            f"任务: {task}",
            f"结果: {result_preview}",
            f"步数: {metadata['steps']}",
            f"耗时: {metadata['duration_seconds']}秒"
        ]

        if metadata.get('tools_used'):
            summary_parts.append(f"工具: {', '.join(metadata['tools_used'])}")

        if metadata.get('error'):
            summary_parts.append(f"错误: {metadata['error']}")

        return "\n".join(summary_parts)

    def _register_task_tool(self):
        """注册 TaskTool（子代理工具）

        自动注册逻辑，支持用户自定义工厂函数。
        """
        from ..tools.builtin.task_tool import TaskTool
        from ..agents.factory import default_subagent_factory

        # 创建子代理工厂函数
        def agent_factory(agent_type: str) -> Agent:
            """子代理工厂函数"""
            # 决定使用哪个 LLM
            if self.config.subagent_use_light_llm:
                # 使用轻量模型
                light_llm = self._create_light_llm()
            else:
                # 使用主模型
                light_llm = self.llm

            # 使用默认工厂创建子代理
            return default_subagent_factory(
                agent_type=agent_type,
                llm=light_llm,
                tool_registry=self.tool_registry,
                config=self.config
            )

        # 创建并注册 TaskTool
        task_tool = TaskTool(
            agent_factory=agent_factory,
            tool_registry=self.tool_registry,
            config=self.config
        )

        self.tool_registry.register_tool(task_tool)

    def _register_todowrite_tool(self):
        """注册 TodoWriteTool（进度管理工具）

        自动注册逻辑，在 __init__ 中调用（如果启用）
        """
        from ..tools.builtin.todowrite_tool import TodoWriteTool

        # 创建并注册 TodoWriteTool
        todo_tool = TodoWriteTool(
            project_root=str(self.working_dir) if hasattr(self, 'working_dir') else ".",
            persistence_dir=self.config.todowrite_persistence_dir
        )

        self.tool_registry.register_tool(todo_tool)

    def _register_devlog_tool(self):
        """注册 DevLogTool（开发日志工具）

        自动注册逻辑，在 __init__ 中调用（如果启用）
        """
        from ..tools.builtin.devlog_tool import DevLogTool

        # 获取 session_id（如果有 trace_logger 则使用其 session_id）
        session_id = self.trace_logger.session_id if self.trace_logger else self._generate_session_id()

        # 创建并注册 DevLogTool
        devlog_tool = DevLogTool(
            session_id=session_id,
            agent_name=self.name,
            project_root=str(self.working_dir) if hasattr(self, 'working_dir') else ".",
            persistence_dir=self.config.devlog_persistence_dir
        )

        self.tool_registry.register_tool(devlog_tool)

    def _generate_session_id(self) -> str:
        """生成会话 ID（如果没有 trace_logger）"""
        import uuid
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        random_suffix = uuid.uuid4().hex[:4]
        return f"s-{timestamp}-{random_suffix}"

    def _create_light_llm(self) -> HelloAgentsLLM:
        injected = getattr(self._component_options, "subagent_llm", None)
        if injected is not None:
            return injected
        if self.config.subagent_light_llm_provider or self.config.subagent_light_llm_model:
            raise ValueError("独立子代理模型请通过 AgentComponents(subagent_llm=...) 注入完整配置")
        return self.llm
