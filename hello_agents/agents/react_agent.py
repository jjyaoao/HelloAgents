"""ReAct Agent - 基于 Function Calling 的实现"""

import json
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any, AsyncGenerator
from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.message import Message
from ..core.lifecycle import AgentEvent, EventType, LifecycleHook
from ..core.streaming import StreamEvent, StreamEventType
from ..tools.registry import ToolRegistry
from ..tools.response import ToolStatus
from ..tools.errors import ToolErrorCode

# 新的系统提示词
DEFAULT_REACT_SYSTEM_PROMPT = """你是一个具备推理和行动能力的 AI 助手。

## 工作流程
你可以通过调用工具来完成任务：

1. **Thought 工具**：用于记录你的推理过程和分析
   - 在需要思考时调用
   - 参数：reasoning（你的推理内容）

2. **业务工具**：用于获取信息或执行操作
   - 根据任务需求选择合适的工具
   - 可以多次调用不同工具

3. **Finish 工具**：用于返回最终答案
   - 当你有足够信息得出结论时调用
   - 参数：answer（最终答案）

## 重要提醒
- 主动使用 Thought 工具记录推理过程
- 可以多次调用工具获取信息
- 只有在确信有足够信息时才调用 Finish
"""


class ReActAgent(Agent):
    """
    ReAct Agent - 基于 Function Calling 的推理与行动

    核心改进：
    - 使用 OpenAI Function Calling（结构化输出）
    - 支持 Thought 工具（显式推理）
    - 支持 Finish 工具（结束流程）
    - 无需正则解析，解析成功率 99%+
    """
    
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: Optional[ToolRegistry] = None,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 5
    ):
        """
        初始化 ReActAgent

        Args:
            name: Agent 名称
            llm: LLM 实例
            tool_registry: 工具注册表（可选）
            system_prompt: 系统提示词（可选，默认使用 DEFAULT_REACT_SYSTEM_PROMPT）
            config: 配置对象
            max_steps: 最大执行步数
        """
        # 传递 tool_registry 到基类
        super().__init__(
            name,
            llm,
            system_prompt or DEFAULT_REACT_SYSTEM_PROMPT,
            config,
            tool_registry=tool_registry or ToolRegistry()
        )

        self.max_steps = max_steps

        # 内置工具标记（用于特殊处理）
        self._builtin_tools = {"Thought", "Finish"}
    
    def add_tool(self, tool):
        """添加工具到工具注册表"""
        self.tool_registry.register_tool(tool)
    
    def run(self, input_text: str, **kwargs) -> str:
        """
        运行 ReAct Agent

        Args:
            input_text: 用户问题
            **kwargs: 其他参数

        Returns:
            最终答案
        """
        session_start_time = datetime.now()

        try:
            # 执行主逻辑
            final_answer = self._run_impl(input_text, session_start_time, **kwargs)

            # 更新元数据
            self._session_metadata["total_steps"] = getattr(self, '_current_step', 0)
            self._session_metadata["total_tokens"] = getattr(self, '_total_tokens', 0)

            return final_answer

        except KeyboardInterrupt:
            # Ctrl+C 时自动保存
            print("\n⚠️ 用户中断，自动保存会话...")
            if self.session_store:
                try:
                    filepath = self.save_session("session-interrupted")
                    print(f"✅ 会话已保存: {filepath}")
                except Exception as e:
                    print(f"❌ 保存失败: {e}")
            raise

        except Exception as e:
            # 错误时也尝试保存
            print(f"\n❌ 发生错误: {e}")
            if self.session_store:
                try:
                    filepath = self.save_session("session-error")
                    print(f"✅ 会话已保存: {filepath}")
                except Exception as save_error:
                    print(f"❌ 保存失败: {save_error}")
            raise

    def _run_impl(self, input_text: str, session_start_time, **kwargs) -> str:
        """
        ReAct Agent 主逻辑实现

        Args:
            input_text: 用户问题
            session_start_time: 会话开始时间
            **kwargs: 其他参数

        Returns:
            最终答案
        """
        # 构建消息列表
        messages = self._build_messages(input_text)

        # 构建工具 schemas（包含内置工具和用户工具）
        tool_schemas = self._build_tool_schemas()

        current_step = 0
        total_tokens = 0

        # 记录用户消息
        if self.trace_logger:
            self.trace_logger.log_event(
                "message_written",
                {"role": "user", "content": input_text}
            )

        print(f"\n🤖 {self.name} 开始处理问题: {input_text}")

        while current_step < self.max_steps:
            current_step += 1
            print(f"\n--- 第 {current_step} 步 ---")

            # 保存当前步数（用于异常时保存）
            self._current_step = current_step

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
                if self.trace_logger:
                    self.trace_logger.log_event(
                        "error",
                        {"error_type": "LLM_ERROR", "message": str(e)},
                        step=current_step
                    )
                break

            # 获取响应消息
            response_message = response.choices[0].message

            # 累计 tokens
            if response.usage:
                total_tokens += response.usage.total_tokens
                self._total_tokens = total_tokens

            # 记录模型输出
            if self.trace_logger:
                self.trace_logger.log_event(
                    "model_output",
                    {
                        "content": response_message.content or "",
                        "tool_calls": len(response_message.tool_calls) if response_message.tool_calls else 0,
                        "usage": {
                            "total_tokens": response.usage.total_tokens if response.usage else 0,
                            "cost": 0.0
                        }
                    },
                    step=current_step
                )

            # 处理工具调用
            tool_calls = response_message.tool_calls
            if not tool_calls:
                # 没有工具调用，直接返回文本响应
                final_answer = response_message.content or "抱歉，我无法回答这个问题。"
                print(f"💬 直接回复: {final_answer}")

                # 保存到历史记录
                self.add_message(Message(input_text, "user"))
                self.add_message(Message(final_answer, "assistant"))

                if self.trace_logger:
                    duration = (datetime.now() - session_start_time).total_seconds()
                    self.trace_logger.log_event(
                        "session_end",
                        {
                            "duration": duration,
                            "total_steps": current_step,
                            "final_answer": final_answer,
                            "status": "success"
                        }
                    )
                    self.trace_logger.finalize()

                return final_answer

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
                if self.trace_logger:
                    self.trace_logger.log_event(
                        "tool_call",
                        {
                            "tool_name": tool_name,
                            "tool_call_id": tool_call_id,
                            "args": arguments
                        },
                        step=current_step
                    )

                # 检查是否是内置工具
                if tool_name in self._builtin_tools:
                    result = self._handle_builtin_tool(tool_name, arguments)
                    print(f"🔧 {tool_name}: {result['content']}")

                    # 记录工具结果
                    if self.trace_logger:
                        self.trace_logger.log_event(
                            "tool_result",
                            {
                                "tool_name": tool_name,
                                "tool_call_id": tool_call_id,
                                "status": "success",
                                "result": result['content']
                            },
                            step=current_step
                        )

                    # 检查是否是 Finish
                    if tool_name == "Finish" and result.get("finished"):
                        final_answer = result["final_answer"]
                        print(f"🎉 最终答案: {final_answer}")

                        # 保存到历史记录
                        self.add_message(Message(input_text, "user"))
                        self.add_message(Message(final_answer, "assistant"))

                        if self.trace_logger:
                            duration = (datetime.now() - session_start_time).total_seconds()
                            self.trace_logger.log_event(
                                "session_end",
                                {
                                    "duration": duration,
                                    "total_steps": current_step,
                                    "final_answer": final_answer,
                                    "status": "success"
                                }
                            )
                            self.trace_logger.finalize()

                        return final_answer

                    # 添加工具结果到消息
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result['content']
                    })
                else:
                    # 用户工具
                    print(f"🎬 调用工具: {tool_name}({arguments})")

                    # 执行工具（使用基类方法，支持字典参数）
                    result = self._execute_tool_call(tool_name, arguments)

                    # 记录工具结果
                    if self.trace_logger:
                        self.trace_logger.log_event(
                            "tool_result",
                            {
                                "tool_name": tool_name,
                                "tool_call_id": tool_call_id,
                                "result": result
                            },
                            step=current_step
                        )

                    # 检查是否是错误
                    if result.startswith("❌"):
                        print(result)
                    else:
                        print(f"👀 观察: {result}")

                    # 添加工具结果到消息
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result
                    })

        # 达到最大步数
        print("⏰ 已达到最大步数，流程终止。")
        final_answer = "抱歉，我无法在限定步数内完成这个任务。"

        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_answer, "assistant"))

        # 记录会话结束（超时）
        if self.trace_logger:
            duration = (datetime.now() - session_start_time).total_seconds()
            self.trace_logger.log_event(
                "session_end",
                {
                    "duration": duration,
                    "total_steps": current_step,
                    "final_answer": final_answer,
                    "status": "timeout"
                }
            )
            self.trace_logger.finalize()

        return final_answer

    def _build_messages(self, input_text: str) -> List[Dict[str, str]]:
        """构建消息列表"""
        messages = []

        # 添加系统提示词
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })

        # 添加用户问题
        messages.append({
            "role": "user",
            "content": input_text
        })

        return messages

    def _build_tool_schemas(self) -> List[Dict[str, Any]]:
        """构建工具 JSON Schema（包含内置工具和用户工具）

        复用基类的 _build_tool_schemas()，并追加 ReAct 内置工具
        """
        schemas = []

        # 1. 添加内置工具：Thought
        schemas.append({
            "type": "function",
            "function": {
                "name": "Thought",
                "description": "分析问题，制定策略，记录推理过程。在需要思考时调用此工具。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {
                            "type": "string",
                            "description": "你的推理过程和分析"
                        }
                    },
                    "required": ["reasoning"]
                }
            }
        })

        # 2. 添加内置工具：Finish
        schemas.append({
            "type": "function",
            "function": {
                "name": "Finish",
                "description": "当你有足够信息得出结论时，使用此工具返回最终答案。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "answer": {
                       "type": "string",
                            "description": "最终答案"
                        }
                    },
                    "required": ["answer"]
                }
            }
        })

        # 3. 添加用户工具（复用基类方法）
        if self.tool_registry:
            user_tool_schemas = super()._build_tool_schemas()
            schemas.extend(user_tool_schemas)

        return schemas

    def _handle_builtin_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """处理内置工具调用"""
        if tool_name == "Thought":
            reasoning = arguments.get("reasoning", "")
            return {
                "content": f"推理: {reasoning}",
                "finished": False
            }
        elif tool_name == "Finish":
            answer = arguments.get("answer", "")
            return {
                "content": f"最终答案: {answer}",
                "finished": True,
                "final_answer": answer
            }
        else:
            return {
                "content": f"未知的内置工具: {tool_name}",
                "finished": False
            }

    # ==================== 异步方法 ====================

    async def arun(
        self,
        input_text: str,
        on_start: LifecycleHook = None,
        on_step: LifecycleHook = None,
        on_tool_call: LifecycleHook = None,
        on_finish: LifecycleHook = None,
        on_error: LifecycleHook = None,
        **kwargs
    ) -> str:
        """
        异步执行 ReAct Agent（完整版本）

        支持：
        - 工具并行执行（独立工具）
        - 生命周期钩子
        - 异步 LLM 调用

        Args:
            input_text: 用户问题
            on_start: Agent 开始执行时的钩子
            on_step: 每个推理步骤的钩子
            on_tool_call: 工具调用时的钩子
            on_finish: Agent 执行完成时的钩子
            on_error: 发生错误时的钩子
            **kwargs: 其他参数

        Returns:
            最终答案
        """
        session_start_time = datetime.now()

        # 触发开始事件
        await self._emit_event(
            EventType.AGENT_START,
            on_start,
            input_text=input_text
        )

        try:
            # 构建消息列表
            messages = self._build_messages(input_text)
            tool_schemas = self._build_tool_schemas()

            current_step = 0
            total_tokens = 0

            # 记录用户消息
            if self.trace_logger:
                self.trace_logger.log_event(
                    "message_written",
                    {"role": "user", "content": input_text}
                )

            print(f"\n🤖 {self.name} 开始处理问题: {input_text}")

            while current_step < self.max_steps:
                current_step += 1
                print(f"\n--- 第 {current_step} 步 ---")

                # 触发步骤开始事件
                await self._emit_event(
                    EventType.STEP_START,
                    on_step,
                    step=current_step
                )

                # 异步调用 LLM
                try:
                    response = await self.llm.ainvoke_with_tools(
                        messages=messages,
                        tools=tool_schemas,
                        tool_choice="auto",
                        **kwargs
                    )
                except Exception as e:
                    print(f"❌ LLM 调用失败: {e}")
                    await self._emit_event(
                        EventType.AGENT_ERROR,
                        on_error,
                        error=str(e),
                        step=current_step
                    )
                    break

                # 获取响应消息
                response_message = response.choices[0].message

                # 累计 tokens
                if response.usage:
                    total_tokens += response.usage.total_tokens

                # 记录模型输出
                if self.trace_logger:
                    self.trace_logger.log_event(
                        "model_output",
                        {
                            "content": response_message.content or "",
                            "tool_calls": len(response_message.tool_calls) if response_message.tool_calls else 0,
                            "usage": {
                                "total_tokens": response.usage.total_tokens if response.usage else 0,
                                "cost": 0.0
                            }
                        },
                        step=current_step
                    )

                # 处理工具调用
                tool_calls = response_message.tool_calls
                if not tool_calls:
                    # 没有工具调用，直接返回
                    final_answer = response_message.content or "抱歉，我无法回答这个问题。"
                    print(f"💬 直接回复: {final_answer}")

                    self.add_message(Message(input_text, "user"))
                    self.add_message(Message(final_answer, "assistant"))

                    await self._emit_event(
                        EventType.AGENT_FINISH,
                        on_finish,
                        result=final_answer,
                        total_steps=current_step,
                        total_tokens=total_tokens
                    )

                    if self.trace_logger:
                        duration = (datetime.now() - session_start_time).total_seconds()
                        self.trace_logger.log_event(
                            "session_end",
                            {
                                "duration": duration,
                                "total_steps": current_step,
                                "final_answer": final_answer,
                                "status": "success"
                            }
                        )
                        self.trace_logger.finalize()

                    return final_answer

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

                # 异步并行执行工具
                tool_results = await self._execute_tools_async(
                    tool_calls,
                    current_step,
                    on_tool_call
                )

                # 检查是否有 Finish 工具
                for tool_name, tool_call_id, result in tool_results:
                    if tool_name == "Finish" and result.get("finished"):
                        final_answer = result["final_answer"]
                        print(f"🎉 最终答案: {final_answer}")

                        self.add_message(Message(input_text, "user"))
                        self.add_message(Message(final_answer, "assistant"))

                        await self._emit_event(
                            EventType.AGENT_FINISH,
                            on_finish,
                            result=final_answer,
                            total_steps=current_step,
                            total_tokens=total_tokens
                        )

                        if self.trace_logger:
                            duration = (datetime.now() - session_start_time).total_seconds()
                            self.trace_logger.log_event(
                                "session_end",
                                {
                                    "duration": duration,
                                    "total_steps": current_step,
                                    "final_answer": final_answer,
                                    "status": "success"
                                }
                            )
                            self.trace_logger.finalize()

                        return final_answer

                    # 添加工具结果到消息
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result.get('content', str(result))
                    })

                # 触发步骤完成事件
                await self._emit_event(
                    EventType.STEP_FINISH,
                    on_step,
                    step=current_step,
                    tool_calls=len(tool_calls)
                )

            # 达到最大步数
            print("⏰ 已达到最大步数，流程终止。")
            final_answer = "抱歉，我无法在限定步数内完成这个任务。"

            self.add_message(Message(input_text, "user"))
            self.add_message(Message(final_answer, "assistant"))

            await self._emit_event(
                EventType.AGENT_FINISH,
                on_finish,
                result=final_answer,
                total_steps=current_step,
                total_tokens=total_tokens,
                status="timeout"
            )

            if self.trace_logger:
                duration = (datetime.now() - session_start_time).total_seconds()
                self.trace_logger.log_event(
                    "session_end",
                    {
                        "duration": duration,
                        "total_steps": current_step,
                        "final_answer": final_answer,
                        "status": "timeout"
                    }
                )
                self.trace_logger.finalize()

            return final_answer

        except Exception as e:
            await self._emit_event(
                EventType.AGENT_ERROR,
                on_error,
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def _execute_tools_async(
        self,
        tool_calls: List[Any],
        current_step: int,
        on_tool_call: LifecycleHook = None
    ) -> List[tuple]:
        """
        异步并行执行工具

        策略：
        1. 内置工具（Thought/Finish）串行执行
        2. 用户工具并行执行（最多 max_concurrent_tools 个）

        Args:
            tool_calls: 工具调用列表
            current_step: 当前步骤
            on_tool_call: 工具调用钩子

        Returns:
            [(tool_name, tool_call_id, result), ...]
        """
        results = []

        # 分组：内置工具 vs 用户工具
        builtin_calls = []
        user_calls = []

        for tc in tool_calls:
            if tc.function.name in self._builtin_tools:
                builtin_calls.append(tc)
            else:
                user_calls.append(tc)

        # 1. 串行执行内置工具
        for tc in builtin_calls:
            tool_name = tc.function.name
            tool_call_id = tc.id

            try:
                arguments = json.loads(tc.function.arguments)
            except json.JSONDecodeError as e:
                results.append((tool_name, tool_call_id, {"content": f"错误：参数格式不正确 - {str(e)}"}))
                continue

            # 触发工具调用事件
            await self._emit_event(
                EventType.TOOL_CALL,
                on_tool_call,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                args=arguments,
                step=current_step
            )

            result = self._handle_builtin_tool(tool_name, arguments)
            print(f"🔧 {tool_name}: {result['content']}")

            # 记录工具结果
            if self.trace_logger:
                self.trace_logger.log_event(
                    "tool_result",
                    {
                        "tool_name": tool_name,
                        "tool_call_id": tool_call_id,
                        "status": "success",
                        "result": result['content']
                    },
                    step=current_step
                )

            results.append((tool_name, tool_call_id, result))

        # 2. 并行执行用户工具
        if user_calls:
            max_concurrent = getattr(self.config, 'max_concurrent_tools', 3)

            # 使用 Semaphore 限制并发数
            semaphore = asyncio.Semaphore(max_concurrent)

            async def execute_one(tc):
                async with semaphore:
                    tool_name = tc.function.name
                    tool_call_id = tc.id

                    try:
                        arguments = json.loads(tc.function.arguments)
                    except json.JSONDecodeError as e:
                        return (tool_name, tool_call_id, {"content": f"错误：参数格式不正确 - {str(e)}"})

                    # 触发工具调用事件
                    await self._emit_event(
                        EventType.TOOL_CALL,
                        on_tool_call,
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                        args=arguments,
                        step=current_step
                    )

                    print(f"🎬 调用工具: {tool_name}({arguments})")

                    # 异步执行工具
                    tool = self.tool_registry.get_tool(tool_name)
                    if not tool:
                        result_content = f"❌ 工具 {tool_name} 不存在"
                    else:
                        try:
                            tool_response = await tool.arun_with_timing(arguments)
                            result_content = tool_response.text

                            # 应用截断
                            truncate_result = self.truncator.truncate(
                                tool_name=tool_name,
                                output=result_content
                            )
                            result_content = truncate_result.get('preview', result_content)
                        except Exception as e:
                            result_content = f"❌ 工具执行失败: {str(e)}"

                    # 记录工具结果
                    if self.trace_logger:
                        self.trace_logger.log_event(
                            "tool_result",
                            {
                                "tool_name": tool_name,
                                "tool_call_id": tool_call_id,
                                "result": result_content
                            },
                            step=current_step
                        )

                    if result_content.startswith("❌"):
                        print(result_content)
                    else:
                        print(f"👀 观察: {result_content}")

                    return (tool_name, tool_call_id, {"content": result_content})

            # 并行执行
            user_results = await asyncio.gather(*[execute_one(tc) for tc in user_calls])
            results.extend(user_results)

        return results

    async def arun_stream(
        self,
        input_text: str,
        on_start: LifecycleHook = None,
        on_step: LifecycleHook = None,
        on_tool_call: LifecycleHook = None,
        on_finish: LifecycleHook = None,
        on_error: LifecycleHook = None,
        **kwargs
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        ReActAgent 真正的流式执行

        实时返回：
        - LLM 输出的每个文本块
        - 工具调用的开始和结束
        - 步骤的开始和结束

        Args:
            input_text: 用户问题
            on_start: 开始钩子
            on_step: 步骤钩子
            on_tool_call: 工具调用钩子
            on_finish: 完成钩子
            on_error: 错误钩子
            **kwargs: 其他参数

        Yields:
            StreamEvent: 流式事件
        """
        session_start_time = datetime.now()

        # 发送开始事件
        yield StreamEvent.create(
            StreamEventType.AGENT_START,
            self.name,
            input_text=input_text
        )

        await self._emit_event(EventType.AGENT_START, on_start, input_text=input_text)

        try:
            # 构建消息列表
            messages = self._build_messages(input_text)
            tool_schemas = self._build_tool_schemas()

            current_step = 0
            final_answer = None

            print(f"\n🤖 {self.name} 开始处理问题: {input_text}")

            while current_step < self.max_steps:
                current_step += 1

                # 发送步骤开始事件
                yield StreamEvent.create(
                    StreamEventType.STEP_START,
                    self.name,
                    step=current_step,
                    max_steps=self.max_steps
                )

                await self._emit_event(EventType.STEP_START, on_step, step=current_step)

                print(f"\n--- 第 {current_step} 步 ---")

                # LLM 流式调用
                full_response = ""
                tool_calls_data = []

                try:
                    # 使用 LLM 的异步流式方法
                    async for chunk in self.llm.astream_invoke(messages, **kwargs):
                        full_response += chunk

                        # 发送 LLM 输出块
                        yield StreamEvent.create(
                            StreamEventType.LLM_CHUNK,
                            self.name,
                            chunk=chunk,
                            step=current_step
                        )

                        print(chunk, end="", flush=True)

                    print()  # 换行

                except Exception as e:
                    error_msg = f"LLM 调用失败: {str(e)}"
                    print(f"❌ {error_msg}")

                    yield StreamEvent.create(
                        StreamEventType.ERROR,
                        self.name,
                        error=error_msg,
                        step=current_step
                    )

                    await self._emit_event(EventType.AGENT_ERROR, on_error, error=error_msg)
                    break

                # 解析工具调用（需要完整响应）
                # 注意：流式输出后需要重新调用 LLM 获取 tool_calls
                # 这里简化处理：使用非流式调用获取工具调用
                try:
                    response = self.llm.invoke_with_tools(
                        messages=messages,
                        tools=tool_schemas,
                        tool_choice="auto",
                        **kwargs
                    )

                    response_message = response.choices[0].message
                    tool_calls = response_message.tool_calls

                    if not tool_calls:
                        # 没有工具调用，直接返回
                        final_answer = response_message.content or full_response or "抱歉，我无法回答这个问题。"

                        yield StreamEvent.create(
                            StreamEventType.AGENT_FINISH,
                            self.name,
                            result=final_answer,
                            total_steps=current_step
                        )

                        await self._emit_event(EventType.AGENT_FINISH, on_finish, result=final_answer)

                        # 保存到历史
                        self.add_message(Message(input_text, "user"))
                        self.add_message(Message(final_answer, "assistant"))

                        return

                    # 添加助手消息到历史
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

                    # 执行工具调用
                    tool_results = await self._execute_tools_async_stream(
                        tool_calls,
                        current_step,
                        on_tool_call
                    )

                    # 发送工具结果事件并添加到消息
                    for tool_name, tool_call_id, result_dict in tool_results:
                        yield StreamEvent.create(
                            StreamEventType.TOOL_CALL_FINISH,
                            self.name,
                            tool_name=tool_name,
                            tool_call_id=tool_call_id,
                            result=result_dict["content"],
                            step=current_step
                        )

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result_dict["content"]
                        })

                        # 检查是否是 Finish 工具
                        if tool_name == "Finish":
                            try:
                                args = json.loads(tool_calls[0].function.arguments)
                                final_answer = args.get("answer", result_dict["content"])
                            except:
                                final_answer = result_dict["content"]

                            yield StreamEvent.create(
                                StreamEventType.AGENT_FINISH,
                                self.name,
                                result=final_answer,
                                total_steps=current_step
                            )

                            await self._emit_event(EventType.AGENT_FINISH, on_finish, result=final_answer)

                            # 保存到历史
                            self.add_message(Message(input_text, "user"))
                            self.add_message(Message(final_answer, "assistant"))

                            return

                    # 发送步骤完成事件
                    yield StreamEvent.create(
                        StreamEventType.STEP_FINISH,
                        self.name,
                        step=current_step
                    )

                except Exception as e:
                    error_msg = f"工具执行失败: {str(e)}"
                    print(f"❌ {error_msg}")

                    yield StreamEvent.create(
                        StreamEventType.ERROR,
                        self.name,
                        error=error_msg,
                        step=current_step
                    )

                    await self._emit_event(EventType.AGENT_ERROR, on_error, error=error_msg)
                    break

            # 达到最大步数
            if not final_answer:
                final_answer = "抱歉，已达到最大步数限制，无法完成任务。"

                yield StreamEvent.create(
                    StreamEventType.AGENT_FINISH,
                    self.name,
                    result=final_answer,
                    total_steps=current_step,
                    max_steps_reached=True
                )

                await self._emit_event(EventType.AGENT_FINISH, on_finish, result=final_answer)

                # 保存到历史
                self.add_message(Message(input_text, "user"))
                self.add_message(Message(final_answer, "assistant"))

        except Exception as e:
            error_msg = f"Agent 执行失败: {str(e)}"

            yield StreamEvent.create(
                StreamEventType.ERROR,
                self.name,
                error=error_msg,
                error_type=type(e).__name__
            )

            await self._emit_event(EventType.AGENT_ERROR, on_error, error=error_msg)
            raise

    async def _execute_tools_async_stream(
        self,
        tool_calls: List[Any],
        current_step: int,
        on_tool_call: LifecycleHook = None
    ) -> List[tuple]:
        """
        异步执行工具调用（流式版本，发送工具调用开始事件）

        Args:
            tool_calls: 工具调用列表
            current_step: 当前步骤
            on_tool_call: 工具调用钩子

        Returns:
            List[tuple]: (tool_name, tool_call_id, result_dict) 列表
        """
        results = []

        # 分组：内置工具 vs 用户工具
        builtin_calls = [tc for tc in tool_calls if tc.function.name in self._builtin_tools]
        user_calls = [tc for tc in tool_calls if tc.function.name not in self._builtin_tools]

        # 1. 串行执行内置工具
        for tc in builtin_calls:
            tool_name = tc.function.name
            tool_call_id = tc.id

            try:
                arguments = json.loads(tc.function.arguments)
            except json.JSONDecodeError as e:
                results.append((tool_name, tool_call_id, {"content": f"错误：参数格式不正确 - {str(e)}"}))
                continue

            # 触发工具调用事件
            await self._emit_event(
                EventType.TOOL_CALL,
                on_tool_call,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                args=arguments,
                step=current_step
            )

            # 执行内置工具
            if tool_name == "Thought":
                reasoning = arguments.get("reasoning", "")
                print(f"💭 思考: {reasoning}")
                result_content = f"已记录推理过程: {reasoning}"
            elif tool_name == "Finish":
                answer = arguments.get("answer", "")
                print(f"✅ 最终答案: {answer}")
                result_content = answer
            else:
                result_content = f"未知的内置工具: {tool_name}"

            results.append((tool_name, tool_call_id, {"content": result_content}))

        # 2. 并行执行用户工具
        if user_calls:
            max_concurrent = getattr(self.config, 'max_concurrent_tools', 3)
            semaphore = asyncio.Semaphore(max_concurrent)

            async def execute_one(tc):
                async with semaphore:
                    tool_name = tc.function.name
                    tool_call_id = tc.id

                    try:
                        arguments = json.loads(tc.function.arguments)
                    except json.JSONDecodeError as e:
                        return (tool_name, tool_call_id, {"content": f"错误：参数格式不正确 - {str(e)}"})

                    # 触发工具调用事件
                    await self._emit_event(
                        EventType.TOOL_CALL,
                        on_tool_call,
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                        args=arguments,
                        step=current_step
                    )

                    print(f"🔧 调用工具: {tool_name}({arguments})")

                    # 异步执行工具
                    tool = self.tool_registry.get_tool(tool_name)
                    if not tool:
                        result_content = f"❌ 工具 {tool_name} 不存在"
                    else:
                        try:
                            tool_response = await tool.arun_with_timing(arguments)
                            result_content = tool_response.text

                            # 应用截断
                            truncate_result = self.truncator.truncate(
                                tool_name=tool_name,
                                output=result_content
                            )
                            result_content = truncate_result.get('preview', result_content)
                        except Exception as e:
                            result_content = f"❌ 工具执行失败: {str(e)}"

                    if result_content.startswith("❌"):
                        print(result_content)
                    else:
                        print(f"👀 观察: {result_content}")

                    return (tool_name, tool_call_id, {"content": result_content})

            # 并行执行
            user_results = await asyncio.gather(*[execute_one(tc) for tc in user_calls])
            results.extend(user_results)

        return results


