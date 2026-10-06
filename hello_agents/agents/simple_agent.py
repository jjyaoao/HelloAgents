"""在共享工具与事件运行机制上提供简洁的 Agent 接口。"""

import asyncio
import json
from copy import deepcopy
from contextlib import aclosing
from typing import Optional, List, TYPE_CHECKING
from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.components import AgentComponents
from ..core.message import Message
from ..core.lifecycle import EventType
from ..core.streaming import StreamEvent, StreamEventType
from ..core.budget import BudgetExceeded
from ..core.runtime import RunResult, sync_events, turn_events, close_interrupted_turn
from ..context.providers import ContextAssembler, ContextProvider

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry


class SimpleAgent(Agent):
    """run、arun 与流式事件入口遵循相同的执行语义。"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional["ToolRegistry"] = None,
        enable_tool_calling: bool = True,
        max_tool_iterations: int = 3,
        context_builder: Optional[ContextAssembler] = None,
        context_providers: Optional[List[ContextProvider]] = None,
        components: Optional[AgentComponents] = None,
    ):
        """
        初始化SimpleAgent

        Args:
            name: Agent名称
            llm: LLM实例
            system_prompt: 系统提示词
            config: 配置对象
            tool_registry: 工具注册表（可选，如果提供则启用工具调用）
            enable_tool_calling: 是否启用工具调用（只有在提供tool_registry时生效）
            max_tool_iterations: 最大工具调用迭代次数
            components: 显式组件覆盖；未指定的部分沿用 Config 默认装配
        """
        # 传递 tool_registry 到基类
        super().__init__(
            name,
            llm,
            system_prompt,
            config,
            tool_registry=tool_registry,
            components=components,
        )
        self.enable_tool_calling = enable_tool_calling and tool_registry is not None
        self.max_tool_iterations = max_tool_iterations
        self.context_builder = context_builder
        self.context_providers = list(context_providers or [])
        if self.context_providers and context_builder is None:
            raise ValueError("使用 context_providers 需要显式配置 context_builder")
        self.last_context_diagnostics = None

        if type(max_tool_iterations) is not int or max_tool_iterations < 1:
            raise ValueError("max_tool_iterations 必须是正整数")
        self.last_run = None
        self._run_active = False
        self._messages_since_save = 0

    def run(self, input_text, **kwargs):
        for _ in sync_events(self._events(input_text, stream=False, **kwargs)):
            pass
        return self.last_run.answer

    def stream_run(self, input_text, **kwargs):
        for event in sync_events(self._events(input_text, stream=True, **kwargs)):
            if event.type == StreamEventType.LLM_CHUNK:
                yield event.data["chunk"]

    async def arun(
        self,
        input_text,
        *,
        on_start=None,
        on_step=None,
        on_finish=None,
        on_error=None,
        on_tool_call=None,
        **kwargs,
    ):
        async for _ in self._events(
            input_text,
            stream=False,
            on_start=on_start,
            on_step=on_step,
            on_finish=on_finish,
            on_error=on_error,
            on_tool_call=on_tool_call,
            **kwargs,
        ):
            pass
        return self.last_run.answer

    async def arun_stream(
        self,
        input_text,
        *,
        on_start=None,
        on_step=None,
        on_finish=None,
        on_error=None,
        on_tool_call=None,
        **kwargs,
    ):
        async with aclosing(
            self._events(
                input_text,
                stream=True,
                on_start=on_start,
                on_step=on_step,
                on_finish=on_finish,
                on_error=on_error,
                on_tool_call=on_tool_call,
                **kwargs,
            )
        ) as events:
            async for event in events:
                yield event

    async def _run_loop(self, messages, packets, stream, kwargs):
        async with aclosing(
            turn_events(self, messages, packets, stream=stream, kwargs=kwargs)
        ) as source:
            async for event in source:
                yield event

    def _build_messages(self, input_text):
        messages = (
            [{"role": "system", "content": self.system_prompt}]
            if self.system_prompt
            else []
        )
        for msg in self._history:
            native = (msg.metadata or {}).get("model_message")
            if native is not None:
                messages.append(deepcopy(native))
            else:
                messages.append(
                    {
                        "role": "user" if msg.role == "summary" else msg.role,
                        "content": (
                            "[历史摘要，供参考]\n" + msg.content
                            if msg.role == "summary"
                            else msg.content
                        ),
                    }
                )
        messages.append({"role": "user", "content": input_text})
        return messages

    def _commit_messages(self, messages, *, compress=True):
        # 在压缩、保存或发出 AGENT_FINISH 事件前，写入完整的交互记录。
        for item in messages:
            self.history_manager.append(
                Message(
                    item.get("content") or "",
                    item["role"],
                    metadata={"model_message": deepcopy(item)},
                )
            )
        self._history_token_count = self.token_counter.count_messages(
            self.get_history()
        )
        if compress and self._should_compress():
            self._compress_history()
        self._messages_since_save += len(messages)
        if (
            self.config.auto_save_enabled
            and self.session_store is not None
            and self._messages_since_save >= self.config.auto_save_interval
        ):
            self._auto_save()
            self._messages_since_save = 0

    async def _aexecute_tool_call(self, name, arguments):
        parameters = (
            self._convert_parameter_types(name, arguments)
            if self.tool_registry.get_tool(name)
            else arguments.get("input", "")
        )
        response = await self.tool_registry.aexecute_tool(name, parameters)
        text = response.to_model_text()
        truncated = self.truncator.truncate(name, text)
        if truncated.get("truncated"):
            return json.dumps(
                {
                    "status": "partial",
                    "text": "工具结果过长，以下为预览",
                    "data": {
                        "preview": truncated["preview"],
                        "full_output_path": truncated.get("full_output_path"),
                    },
                },
                ensure_ascii=False,
            )
        return text

    async def _events(
        self,
        input_text,
        *,
        stream,
        on_start=None,
        on_step=None,
        on_finish=None,
        on_error=None,
        on_tool_call=None,
        **kwargs,
    ):
        if self._run_active:
            raise RuntimeError(
                "同一个 Agent 不能并发修改会话，请为独立任务创建独立实例"
            )
        self._run_active = True
        self.last_run = RunResult()
        logger = self.trace_logger
        messages = None
        committed = False
        try:
            if self.config.trace_enabled and (
                logger is None or logger.jsonl_file.closed
            ):
                from ..observability import TraceLogger

                logger = self.trace_logger = TraceLogger(
                    self.config.trace_dir,
                    sanitize=self.config.trace_sanitize,
                    html_include_raw_response=self.config.trace_html_include_raw_response,
                )
                logger.log_event("session_start", {"agent_name": self.name})
            packets = self._context_packets(kwargs)
            messages = self._build_messages(input_text)
            start = len(messages) - 1
            await self._emit_event(
                EventType.AGENT_START, on_start, input_text=input_text
            )
            yield StreamEvent.create(
                StreamEventType.AGENT_START, self.name, input_text=input_text
            )
            async with aclosing(
                self._run_loop(messages, packets, stream, kwargs)
            ) as source:
                async for event in source:
                    kind = event["kind"]
                    if kind in ("tool_start", "tool_finish"):
                        event = dict(
                            event, tool_name=event["name"], tool_call_id=event["id"]
                        )
                    if kind == "tool_start":
                        try:
                            event["args"] = json.loads(event["arguments"])
                        except (TypeError, ValueError):
                            event["args"] = None
                    if logger and kind != "chunk":
                        trace_kind = {
                            "model": "model_output",
                            "tool_start": "tool_call",
                            "tool_finish": "tool_result",
                        }.get(kind, kind)
                        logger.log_event(trace_kind, event, step=event.get("step"))
                    if kind == "chunk":
                        yield StreamEvent.create(
                            (
                                StreamEventType.THINKING
                                if event.get("phase") == "reflection"
                                else StreamEventType.LLM_CHUNK
                            ),
                            self.name,
                            chunk=event["text"],
                            **{
                                k: v
                                for k, v in event.items()
                                if k not in {"kind", "text"}
                            },
                        )
                    elif kind == "model":
                        if not getattr(self, "_parallel_tools", False):
                            await self._emit_event(
                                EventType.STEP_FINISH, on_step, **event
                            )
                    elif kind in ("step_start", "step_finish"):
                        event_type = (
                            StreamEventType.STEP_START
                            if kind == "step_start"
                            else StreamEventType.STEP_FINISH
                        )
                        if event.get("phase") == "tool_loop":
                            await self._emit_event(
                                (
                                    EventType.STEP_START
                                    if kind == "step_start"
                                    else EventType.STEP_FINISH
                                ),
                                on_step,
                                **event,
                            )
                        yield StreamEvent.create(event_type, self.name, **event)
                    elif kind == "tool_start":
                        await self._emit_event(
                            EventType.TOOL_CALL, on_tool_call, **event
                        )
                        yield StreamEvent.create(
                            StreamEventType.TOOL_CALL_START, self.name, **event
                        )
                    elif kind == "tool_finish":
                        yield StreamEvent.create(
                            StreamEventType.TOOL_CALL_FINISH, self.name, **event
                        )
            self._session_metadata.update(
                total_steps=self.last_run.model_calls,
                total_tokens=self.last_run.usage.get("total_tokens", 0),
            )
            committed = True
            self._commit_messages(messages[start:])
            await self._emit_event(
                EventType.AGENT_FINISH,
                on_finish,
                result=self.last_run.answer,
                status=self.last_run.status,
                total_steps=self.last_run.model_calls,
                total_tokens=self.last_run.usage.get("total_tokens", 0),
            )
            yield StreamEvent.create(
                StreamEventType.AGENT_FINISH,
                self.name,
                result=self.last_run.answer,
                status=self.last_run.status,
                stop_reason=self.last_run.stop_reason,
                total_steps=getattr(
                    self, "_plan_total_steps", self.last_run.model_calls
                ),
                total_tokens=self.last_run.usage.get("total_tokens", 0),
                max_steps_reached=self.last_run.status == "max_iterations",
                **(
                    {"total_iterations": self._reflection_iterations}
                    if hasattr(self, "_reflection_iterations")
                    else {}
                ),
            )
        except (asyncio.CancelledError, GeneratorExit):
            if not committed:
                self.last_run.status = "cancelled"
            raise
        except Exception as exc:
            self.last_run.status = "budget_exhausted" if isinstance(exc, BudgetExceeded) else "failed"
            if logger:
                logger.log_event(
                    "error", {"message": str(exc), "error_type": type(exc).__name__}
                )
            await self._emit_event(
                EventType.AGENT_ERROR,
                on_error,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            yield StreamEvent.create(
                StreamEventType.ERROR,
                self.name,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise
        finally:
            try:
                if messages is not None and not committed:
                    self._session_metadata.update(
                        total_steps=self.last_run.model_calls,
                        total_tokens=self.last_run.usage.get("total_tokens", 0),
                    )
                    self._commit_messages(
                        close_interrupted_turn(messages[start:]), compress=False
                    )
            finally:
                try:
                    if logger:
                        logger.log_event(
                            "session_end",
                            {
                                "status": self.last_run.status,
                                "final_answer": self.last_run.answer,
                                "total_steps": self.last_run.model_calls,
                                "usage": self.last_run.usage,
                            },
                        )
                        logger.finalize()
                finally:
                    self._run_active = False

    def _context_packets(self, kwargs):
        packets = list(kwargs.pop("context_packets", None) or [])
        if packets and self.context_builder is None:
            raise ValueError("使用 context_packets 需要显式配置 context_builder")
        return packets

    def _prepare_context(self, messages, packets, tool_schemas=None):
        if self.context_builder is None:
            return messages
        query = next(
            (
                message.get("content") or ""
                for message in reversed(messages)
                if message.get("role") == "user"
            ),
            "",
        )
        gathered = list(packets)
        for provider in self.context_providers:
            gathered.extend(provider.get_context(query))
        result = self.context_builder.build_messages(
            messages, additional_packets=gathered, tool_schemas=tool_schemas
        )
        self.last_context_diagnostics = result.diagnostics
        return result.messages

    def add_tool(self, tool, auto_expand: bool = True) -> None:
        """
        添加工具到Agent（便利方法）

        Args:
            tool: Tool对象
            auto_expand: 是否自动展开可展开的工具（默认True）

        如果工具是可展开的（expandable=True），会自动展开为多个独立工具
        """
        if not self.tool_registry:
            from ..tools.registry import ToolRegistry

            self.tool_registry = ToolRegistry()
            self.enable_tool_calling = True

        # 直接使用 ToolRegistry 的 register_tool 方法
        # ToolRegistry 会自动处理工具展开
        self.tool_registry.register_tool(tool, auto_expand=auto_expand)

    def remove_tool(self, tool_name: str) -> bool:
        """移除工具（便利方法）"""
        if self.tool_registry and tool_name in self.tool_registry.list_tools():
            self.tool_registry.unregister(tool_name)
            return True
        return False

    def list_tools(self) -> list:
        """列出所有可用工具"""
        if self.tool_registry:
            return self.tool_registry.list_tools()
        return []

    def has_tools(self) -> bool:
        """检查是否有可用工具"""
        return self.enable_tool_calling and self.tool_registry is not None
