"""简单Agent实现 - 基于 Function Calling"""

from typing import Optional, Iterator, TYPE_CHECKING, List, Dict, Any, AsyncGenerator
import json

from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.message import Message
from ..core.streaming import StreamEvent, StreamEventType
from ..core.lifecycle import LifecycleHook

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry

class SimpleAgent(Agent):
    """简单的对话Agent，支持可选的工具调用

    特性：
    - 纯对话模式（无工具）
    - Function Calling 工具调用（可选）
    - 自动多轮工具调用
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        tool_registry: Optional['ToolRegistry'] = None,
        enable_tool_calling: bool = True,
        max_tool_iterations: int = 3
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
        """
        # 传递 tool_registry 到基类
        super().__init__(
            name,
            llm,
            system_prompt,
            config,
            tool_registry=tool_registry
        )
        self.enable_tool_calling = enable_tool_calling and tool_registry is not None
        self.max_tool_iterations = max_tool_iterations

    def run(self, input_text: str, **kwargs) -> str:
        """
        运行 SimpleAgent（基于 Function Calling）

        Args:
            input_text: 用户输入
            **kwargs: 其他参数

        Returns:
            最终回复
        """
        from datetime import datetime
        from hello_agents.observability import TraceLogger

        session_start_time = datetime.now()

        # 为每次 run 创建新的 TraceLogger（避免多轮对话时文件已关闭的问题）
        trace_logger = None
        if self.config.trace_enabled:
            trace_logger = TraceLogger(
                output_dir=self.config.trace_dir,
                sanitize=self.config.trace_sanitize,
                html_include_raw_response=self.config.trace_html_include_raw_response
            )
            trace_logger.log_event(
                "session_start",
                {
                    "agent_name": self.name,
                    "agent_type": self.__class__.__name__,
                }
            )

        # 构建消息列表
        messages = self._build_messages(input_text)

        # 记录用户消息
        if trace_logger:
            trace_logger.log_event(
                "message_written",
                {"role": "user", "content": input_text}
            )

        # 如果没有启用工具调用，直接返回 LLM 响应
        if not self.enable_tool_calling or not self.tool_registry:
            llm_response = self.llm.invoke(messages, **kwargs)
            response_text = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

            # 保存到历史记录
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(response_text, "assistant"))

            if trace_logger:
                duration = (datetime.now() - session_start_time).total_seconds()
                trace_logger.log_event(
                    "session_end",
                    {
                        "duration": duration,
                        "final_answer": response_text,
                        "status": "success",
                        "usage": llm_response.usage if hasattr(llm_response, 'usage') else {},
                        "latency_ms": llm_response.latency_ms if hasattr(llm_response, 'latency_ms') else 0
                    }
                )
                trace_logger.finalize()

            return response_text

        # 启用工具调用模式
        tool_schemas = self._build_tool_schemas()

        current_iteration = 0
        final_response = ""

        while current_iteration < self.max_tool_iterations:
            current_iteration += 1

            # 调用 LLM（Function Calling）
            try:
                response = self.llm.invoke_with_tools(
                    messages=messages,
                    tools=tool_schemas,
                    tool_choice="auto",
                    **kwargs
                )
            except Exception as e:
                print(f"❌ LLM 调用失败: {e}")
                if trace_logger:
                    trace_logger.log_event(
                        "error",
                        {"error_type": "LLM_ERROR", "message": str(e)},
                        step=current_iteration
                    )
                break

            # 获取响应消息
            response_message = response.choices[0].message

            # 记录模型输出
            if trace_logger:
                usage = response.usage
                trace_logger.log_event(
                    "model_output",
                    {
                        "content": response_message.content,
                        "tool_calls": len(response_message.tool_calls) if response_message.tool_calls else 0,
                        "usage": {
                            "prompt_tokens": usage.prompt_tokens if usage else 0,
                            "completion_tokens": usage.completion_tokens if usage else 0,
                            "total_tokens": usage.total_tokens if usage else 0
                        }
                    },
                    step=current_iteration
                )

            # 处理工具调用
            tool_calls = response_message.tool_calls
            if not tool_calls:
                # 没有工具调用，直接返回文本响应
                final_response = response_message.content or "抱歉，我无法回答这个问题。"
                break

            # 将助手消息添加到历史
            messages.append({
                "role": "assistant",
                "content": response_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in tool_calls
                ]
            })

            # 执行所有工具调用
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_call_id = tool_call.id

                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError as e:
                    print(f"❌ 工具参数解析失败: {e}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": f"错误：参数格式不正确 - {str(e)}"
                    })
                    continue

                # 记录工具调用
                if trace_logger:
                    trace_logger.log_event(
                        "tool_call",
                        {
                            "tool_name": tool_name,
                            "tool_call_id": tool_call_id,
                            "args": arguments
                        },
                        step=current_iteration
                    )

                # 执行工具（复用基类方法）
                result = self._execute_tool_call(tool_name, arguments)

                # 记录工具结果
                if trace_logger:
                    trace_logger.log_event(
                        "tool_result",
                        {
                            "tool_name": tool_name,
                            "tool_call_id": tool_call_id,
                            "result": result
                        },
                        step=current_iteration
                    )

                # 添加工具结果到消息
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result
                })

        # 如果超过最大迭代次数，获取最后一次回答
        if current_iteration >= self.max_tool_iterations and not final_response:
            llm_response = self.llm.invoke(messages, **kwargs)
            final_response = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_response, "assistant"))

        if trace_logger:
            duration = (datetime.now() - session_start_time).total_seconds()
            trace_logger.log_event(
                "session_end",
                {
                    "duration": duration,
                    "total_steps": current_iteration,
                    "final_answer": final_response,
                    "status": "success"
                }
            )
            trace_logger.finalize()

        return final_response

    def _build_messages(self, input_text: str) -> List[Dict[str, str]]:
        """构建消息列表"""
        messages = []

        # 添加系统提示词
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })

        # 添加历史消息
        for msg in self._history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # 添加用户问题
        messages.append({
            "role": "user",
            "content": input_text
        })

        return messages

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
        if self.tool_registry:
            return self.tool_registry.unregister_tool(tool_name)
        return False

    def list_tools(self) -> list:
        """列出所有可用工具"""
        if self.tool_registry:
            return self.tool_registry.list_tools()
        return []

    def has_tools(self) -> bool:
        """检查是否有可用工具"""
        return self.enable_tool_calling and self.tool_registry is not None

    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        """
        流式运行Agent
        
        Args:
            input_text: 用户输入
            **kwargs: 其他参数
            
        Yields:
            Agent响应片段
        """
        # 构建消息列表
        messages = []
        
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        
        for msg in self._history:
            messages.append({"role": msg.role, "content": msg.content})
        
        messages.append({"role": "user", "content": input_text})
        
        # 流式调用LLM
        full_response = ""
        for chunk in self.llm.stream_invoke(messages, **kwargs):
            full_response += chunk
            yield chunk
        
        # 保存完整对话到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(full_response, "assistant"))

    async def arun_stream(
        self,
        input_text: str,
        on_start: LifecycleHook = None,
        on_finish: LifecycleHook = None,
        on_error: LifecycleHook = None,
        **kwargs
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        SimpleAgent 真正的流式执行

        实时返回 LLM 输出的每个文本块

        Args:
            input_text: 用户输入
            on_start: 开始钩子
            on_finish: 完成钩子
            on_error: 错误钩子
            **kwargs: 其他参数

        Yields:
            StreamEvent: 流式事件
        """
        # 发送开始事件
        yield StreamEvent.create(
            StreamEventType.AGENT_START,
            self.name,
            input_text=input_text
        )

        try:
            # 构建消息列表
            messages = []

            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})

            for msg in self._history:
                messages.append({"role": msg.role, "content": msg.content})

            messages.append({"role": "user", "content": input_text})

            # LLM 流式调用
            full_response = ""
            async for chunk in self.llm.astream_invoke(messages, **kwargs):
                full_response += chunk

                # 发送 LLM 输出块
                yield StreamEvent.create(
                    StreamEventType.LLM_CHUNK,
                    self.name,
                    chunk=chunk
                )

            # 发送完成事件
            yield StreamEvent.create(
                StreamEventType.AGENT_FINISH,
                self.name,
                result=full_response
            )

            # 保存到历史
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(full_response, "assistant"))

        except Exception as e:
            # 发送错误事件
            yield StreamEvent.create(
                StreamEventType.ERROR,
                self.name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
