"""Agent基类"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Union, TYPE_CHECKING, AsyncGenerator
import asyncio
from .message import Message
from .llm import HelloAgentsLLM
from .config import Config
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

    向后兼容：
    - self._history 属性仍然可用（通过 property 代理）
    - add_message/clear_history/get_history 方法保持不变
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional['ToolRegistry'] = None
    ):
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or Config()

        # 工具注册表（可选）
        self.tool_registry = tool_registry

        # 新增：上下文工程组件
        from hello_agents.context.history import HistoryManager
        from hello_agents.context.truncator import ObservationTruncator

        self.history_manager = HistoryManager(
            min_retain_rounds=self.config.min_retain_rounds,
            compression_threshold=self.config.compression_threshold
        )

        self.truncator = ObservationTruncator(
            max_lines=self.config.tool_output_max_lines,
            max_bytes=self.config.tool_output_max_bytes,
            truncate_direction=self.config.tool_output_truncate_direction,
            output_dir=self.config.tool_output_dir
        )

        # 新增：Token 计数器（缓存 + 增量计算）
        from ..context.token_counter import TokenCounter
        self.token_counter = TokenCounter(model=self.llm.model)
        self._history_token_count = 0  # 缓存历史 Token 数

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
                    "config": self.config.dict()
                }
            )

        # 新增：Skills 知识外化组件
        from pathlib import Path
        from hello_agents.skills import SkillLoader

        self.skill_loader: Optional[SkillLoader] = None
        if self.config.skills_enabled:
            skills_path = Path(self.config.skills_dir)
            self.skill_loader = SkillLoader(skills_dir=skills_path)

            # 自动注册 SkillTool
            if self.config.skills_auto_register and self.tool_registry:
                from hello_agents.tools.builtin.skill_tool import SkillTool
                skill_tool = SkillTool(skill_loader=self.skill_loader)
                self.tool_registry.register_tool(skill_tool)

        # 新增：会话持久化组件
        from datetime import datetime
        from .session_store import SessionStore

        self.session_store: Optional[SessionStore] = None
        if self.config.session_enabled:
            self.session_store = SessionStore(session_dir=self.config.session_dir)

        # 会话元数据（用于保存）
        self._session_metadata = {
            "created_at": datetime.now().isoformat(),
            "total_tokens": 0,
            "total_steps": 0,
            "duration_seconds": 0
        }
        self._start_time = datetime.now()

        # 新增：子代理机制组件
        if self.config.subagent_enabled and self.tool_registry:
            self._register_task_tool()

        # 新增：TodoWrite 进度管理组件
        if self.config.todowrite_enabled and self.tool_registry:
            self._register_todowrite_tool()

        # 新增：DevLog 开发日志组件
        if self.config.devlog_enabled and self.tool_registry:
            self._register_devlog_tool()

    @property
    def _history(self) -> List[Message]:
        """向后兼容：通过 property 代理到 HistoryManager"""
        return self.history_manager.get_history()

    @_history.setter
    def _history(self, value: List[Message]):
        """向后兼容：允许直接设置历史"""
        self.history_manager.clear()
        for msg in value:
            self.history_manager.append(msg)

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
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.run(input_text, **kwargs)
            )

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
        if self.config.auto_save_enabled and self.session_store:
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

（历史已压缩，保留最近 {self.config.min_retain_rounds} 轮完整对话）"""

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
        if len(boundaries) <= self.config.min_retain_rounds:
            return self._generate_simple_summary(history)

        # 保留最近 N 轮，压缩之前的
        keep_from_index = boundaries[-self.config.min_retain_rounds]
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

            return f"""## 历史摘要（{len(to_compress)} 条消息）
{summary}

---
（已压缩，保留最近 {self.config.min_retain_rounds} 轮完整对话）"""

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
        """获取摘要专用 LLM（轻量模型）

        使用独立的轻量 LLM 实例，节省成本

        Returns:
            HelloAgentsLLM 实例
        """
        if not hasattr(self, '_summary_llm'):
            from ..core.llm import HelloAgentsLLM

            # 使用配置中的轻量模型
            provider = self.config.summary_llm_provider
            model = self.config.summary_llm_model

            self._summary_llm = HelloAgentsLLM(
                provider=provider,
                model=model,
                temperature=self.config.summary_temperature,
                max_tokens=self.config.summary_max_tokens
            )

        return self._summary_llm

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

        # 1. 处理 Tool 对象
        for tool in self.tool_registry.get_all_tools():
            properties: Dict[str, Any] = {}
            required: List[str] = []

            try:
                parameters = tool.get_parameters()
            except Exception:
                parameters = []

            for param in parameters:
                properties[param.name] = {
                    "type": self._map_parameter_type(param.type),
                    "description": param.description or ""
                }
                if param.default is not None:
                    properties[param.name]["default"] = param.default
                if getattr(param, "required", True):
                    required.append(param.name)

            schema: Dict[str, Any] = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": {
                        "type": "object",
                        "properties": properties
                    }
                }
            }
            if required:
                schema["function"]["parameters"]["required"] = required
            schemas.append(schema)

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

        # 1. 尝试执行 Tool 对象
        tool = self.tool_registry.get_tool(tool_name)
        if tool:
            try:
                typed_arguments = self._convert_parameter_types(tool_name, arguments)
                response = tool.run_with_timing(typed_arguments)

                # 根据状态添加前缀
                from ..tools.response import ToolStatus
                if response.status == ToolStatus.ERROR:
                    error_code = response.error_info.get("code", "UNKNOWN") if response.error_info else "UNKNOWN"
                    return f"❌ 错误 [{error_code}]: {response.text}"
                elif response.status == ToolStatus.PARTIAL:
                    return f"⚠️ 部分成功: {response.text}"
                else:
                    return response.text
            except Exception as exc:
                return f"❌ 工具调用失败：{exc}"

        # 2. 尝试执行函数工具
        func = self.tool_registry.get_function(tool_name)
        if func:
            try:
                input_text = arguments.get("input", "")
                response = self.tool_registry.execute_tool(tool_name, input_text)

                # 根据状态添加前缀
                from ..tools.response import ToolStatus
                if response.status == ToolStatus.ERROR:
                    error_code = response.error_info.get("code", "UNKNOWN") if response.error_info else "UNKNOWN"
                    return f"❌ 错误 [{error_code}]: {response.text}"
                elif response.status == ToolStatus.PARTIAL:
                    return f"⚠️ 部分成功: {response.text}"
                else:
                    return response.text
            except Exception as exc:
                return f"❌ 工具调用失败：{exc}"

        return f"❌ 错误：未找到工具 '{tool_name}'"

    # ==================== 会话持久化能力 ====================

    def _auto_save(self):
        """自动保存会话（静默失败）"""
        if not self.session_store:
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
        if not self.session_store:
            raise RuntimeError("会话持久化未启用，请在 Config 中设置 session_enabled=True")

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
        if not self.session_store:
            raise RuntimeError("会话持久化未启用，请在 Config 中设置 session_enabled=True")

        # 加载会话数据
        session_data = self.session_store.load(filepath)

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
        from .message import Message
        self.history_manager.clear()
        for msg_data in session_data.get("history", []):
            self.history_manager.append(Message.from_dict(msg_data))

        # 恢复元数据
        self._session_metadata = session_data.get("metadata", {})

        # 恢复 Read 工具缓存
        if self.tool_registry and session_data.get("read_cache"):
            self.tool_registry.read_metadata_cache = session_data["read_cache"]

        print(f"✅ 会话已恢复：{session_data.get('session_id', 'unknown')}")

    def list_sessions(self) -> List[Dict[str, Any]]:
        """列出所有可用会话

        Returns:
            会话信息列表
        """
        if not self.session_store:
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
        """计算工具 Schema 哈希

        用于检测工具定义是否变化

        Returns:
            工具 Schema 哈希值（16位）
        """
        if not self.tool_registry:
            return "no-tools"

        import json
        from hashlib import sha256

        # 收集所有工具的签名
        tools_signature = {}
        for tool_name in sorted(self.tool_registry.list_tools()):
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                tools_signature[tool_name] = {
                    "name": tool.name,
                    "description": tool.description[:100] if tool.description else "",
                    "parameters": list(tool.parameters.keys()) if hasattr(tool, 'parameters') and tool.parameters else []
                }

        schema_str = json.dumps(tools_signature, sort_keys=True)
        return sha256(schema_str.encode()).hexdigest()[:16]

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
        """作为子代理运行（上下文隔离模式）

        特性：
        - 上下文隔离：创建独立的历史记录，不污染主 Agent 上下文
        - 工具过滤：可选的工具访问控制
        - 摘要返回：返回结构化摘要而非完整历史
        - 状态恢复：执行后自动恢复原始状态

        Args:
            task: 子任务描述
            tool_filter: 工具过滤器（可选），用于限制可用工具
            return_summary: 是否返回摘要（True）或完整结果（False）
            max_steps_override: 覆盖最大步数（可选）

        Returns:
            {
                "success": bool,           # 是否成功完成
                "summary": str,            # 任务摘要（如果 return_summary=True）
                "result": str,             # 完整结果（如果 return_summary=False）
                "metadata": {              # 执行元数据
                    "steps": int,          # 执行步数
                    "tokens": int,         # 消耗 Token 数（估算）
                    "duration_seconds": float,  # 执行时长
                    "tools_used": List[str],    # 使用的工具列表
                    "error": Optional[str]      # 错误信息（如果失败）
                }
            }
        """
        from datetime import datetime
        import time

        # 1. 保存当前状态
        original_history = self.history_manager.get_history().copy()
        original_tools = None
        original_max_steps = None

        # 2. 创建隔离的新历史
        self.history_manager.clear()

        # 3. 应用工具过滤（如果提供）
        if tool_filter and self.tool_registry:
            original_tools = self._apply_tool_filter(tool_filter)

        # 4. 覆盖最大步数（如果提供）
        if max_steps_override is not None and hasattr(self, 'max_steps'):
            original_max_steps = self.max_steps
            self.max_steps = max_steps_override

        # 记录开始时间
        start_time = time.time()
        success = False
        result = ""
        error_msg = None

        try:
            # 5. 执行任务
            result = self.run(task)
            success = True

        except KeyboardInterrupt:
            error_msg = "用户中断"
            raise

        except Exception as e:
            error_msg = str(e)
            result = f"执行失败: {error_msg}"

        finally:
            # 记录执行时长
            duration = time.time() - start_time

            # 6. 收集元数据
            metadata = self._get_subagent_metadata(duration, error_msg)

            # 7. 生成摘要（如果需要）
            if return_summary:
                summary = self._generate_subagent_summary(task, result, metadata)

            # 8. 恢复原始状态
            self.history_manager.clear()
            for msg in original_history:
                self.history_manager.append(msg)

            if original_tools is not None:
                self._restore_tools(original_tools)

            if original_max_steps is not None:
                self.max_steps = original_max_steps

        # 9. 返回结果
        if return_summary:
            return {
                "success": success,
                "summary": summary,
                "metadata": metadata
            }
        else:
            return {
                "success": success,
                "result": result,
                "metadata": metadata
            }

    def _apply_tool_filter(self, tool_filter: 'ToolFilter') -> List[str]:
        """应用工具过滤器

        Args:
            tool_filter: 工具过滤器实例

        Returns:
            原始工具列表（用于恢复）
        """
        if not self.tool_registry:
            return []

        # 保存原始工具列表
        original_tools = self.tool_registry.list_tools()

        # 获取过滤后的工具列表
        filtered_tools = tool_filter.filter(original_tools)

        # 临时移除不允许的工具
        for tool_name in original_tools:
            if tool_name not in filtered_tools:
                self.tool_registry._temp_disabled_tools = getattr(
                    self.tool_registry, '_temp_disabled_tools', {}
                )
                tool = self.tool_registry.get_tool(tool_name)
                if tool:
                    self.tool_registry._temp_disabled_tools[tool_name] = tool
                    # 从注册表中临时移除
                    if tool_name in self.tool_registry._tools:
                        del self.tool_registry._tools[tool_name]

        return original_tools

    def _restore_tools(self, original_tools: List[str]):
        """恢复原始工具列表

        Args:
            original_tools: 原始工具名称列表
        """
        if not self.tool_registry:
            return

        # 恢复被禁用的工具
        if hasattr(self.tool_registry, '_temp_disabled_tools'):
            for tool_name, tool in self.tool_registry._temp_disabled_tools.items():
                self.tool_registry._tools[tool_name] = tool

            # 清空临时禁用列表
            self.tool_registry._temp_disabled_tools = {}

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

        自动注册逻辑，在 __init__ 中调用（如果启用）
        """
        from ..agents.factory import default_subagent_factory
        from ..tools.builtin.task_tool import TaskTool

        # 创建 Agent 工厂函数
        def agent_factory(agent_type: str) -> Agent:
            """为 TaskTool 创建子代理实例"""
            # 决定使用哪个 LLM
            if self.config.subagent_use_light_llm:
                # 使用轻量模型
                from ..core.llm import HelloAgentsLLM
                light_llm = HelloAgentsLLM(
                    provider=self.config.subagent_light_llm_provider,
                    model=self.config.subagent_light_llm_model
                )
                llm = light_llm
            else:
                # 使用主模型
                llm = self.llm

            # 使用默认工厂创建子代理
            return default_subagent_factory(
                agent_type=agent_type,
                llm=llm,
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
        """创建轻量模型 LLM 实例

        Returns:
            轻量模型 LLM 实例
        """
        # 复用主 LLM 的配置，但使用轻量模型
        light_llm = HelloAgentsLLM(
            provider=self.config.subagent_light_llm_provider,
            model=self.config.subagent_light_llm_model,
            temperature=self.llm.temperature if hasattr(self.llm, 'temperature') else 0.7,
            max_tokens=self.llm.max_tokens if hasattr(self.llm, 'max_tokens') else None
        )

        return light_llm