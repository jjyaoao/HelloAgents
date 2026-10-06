"""在共享 Agent 运行机制上实现 ReAct 提示策略。"""

import asyncio
import json
from typing import Any, Dict, List, Optional
from .simple_agent import SimpleAgent
from ..tools.registry import ToolRegistry
from ..core.runtime import deadline
from ..core.llm import HelloAgentsLLM
from ..core.config import Config

DEFAULT_REACT_SYSTEM_PROMPT = """你是一个通过工具解决任务的助手。
按需调用业务工具获取信息或执行操作。Thought 可记录简短的行动说明；
取得足够依据后用 Finish 返回最终答案。不要把计划当成已完成的操作。"""


class ReActAgent(SimpleAgent):
    """各调用入口使用同一循环，通过 Thought 和 Finish 工具表达思考与结束。"""

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: Optional[ToolRegistry] = None,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 5,
        components=None,
    ):
        super().__init__(
            name,
            llm,
            system_prompt or DEFAULT_REACT_SYSTEM_PROMPT,
            config,
            tool_registry=(
                tool_registry if tool_registry is not None else ToolRegistry()
            ),
            max_tool_iterations=max_steps,
            components=components,
        )
        self.max_steps = max_steps
        self._builtin_tools = {"Thought", "Finish"}
        self._parallel_tools = True

    @property
    def max_steps(self) -> int:
        return self.max_tool_iterations

    @max_steps.setter
    def max_steps(self, value: int) -> None:
        if type(value) is not int or value < 1:
            raise ValueError("max_steps 必须是正整数")
        self.max_tool_iterations = value

    def _build_tool_schemas(self) -> List[Dict[str, Any]]:
        """构建工具 JSON Schema（包含内置工具和用户工具）

        复用基类的 _build_tool_schemas()，并追加 ReAct 内置工具
        """
        schemas = []

        # 1. 添加内置工具：Thought
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": "Thought",
                    "description": "分析问题，制定策略，记录简短的行动说明。在需要思考时调用此工具。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reasoning": {
                                "type": "string",
                                "description": "简短的行动计划或结论",
                            }
                        },
                        "required": ["reasoning"],
                    },
                },
            }
        )

        # 2. 添加内置工具：Finish
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": "Finish",
                    "description": "当你有足够信息得出结论时，使用此工具返回最终答案。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "answer": {"type": "string", "description": "最终答案"}
                        },
                        "required": ["answer"],
                    },
                },
            }
        )

        # 3. 添加用户工具（复用基类方法）
        if self.tool_registry:
            user_tool_schemas = super()._build_tool_schemas()
            if any(
                s["function"]["name"] in self._builtin_tools for s in user_tool_schemas
            ):
                raise ValueError("用户工具不能使用 ReAct 保留名称 Thought 或 Finish")
            schemas.extend(user_tool_schemas)

        return schemas

    def _handle_builtin_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理内置工具调用"""
        if tool_name == "Thought":
            reasoning = arguments.get("reasoning", "")
            return {"content": f"推理: {reasoning}", "finished": False}
        elif tool_name == "Finish":
            answer = arguments.get("answer", "")
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("Finish.answer 必须是非空字符串")
            return {
                "content": f"最终答案: {answer}",
                "finished": True,
                "final_answer": answer,
            }
        else:
            return {"content": f"未知的内置工具: {tool_name}", "finished": False}

    async def _execute_tools_async(
        self, tool_calls, current_step=1, on_result=None, **kwargs
    ):
        """按配置限制执行一批请求，由注册表负责原生异步调度与错误处理。"""
        semaphore = asyncio.Semaphore(self.config.max_concurrent_tools)
        failed = asyncio.Event()

        async def one(call):
            async with semaphore:
                if failed.is_set():
                    raise asyncio.CancelledError()
                try:
                    arguments = json.loads(call.arguments)
                    if not isinstance(arguments, dict):
                        raise ValueError("工具参数必须是 JSON 对象")
                    if call.name in self._builtin_tools:
                        result = self._handle_builtin_tool(call.name, arguments)
                    else:
                        async with deadline(self.config.tool_async_timeout):
                            result = {
                                "content": await self._aexecute_tool_call(
                                    call.name, arguments
                                ),
                                "finished": False,
                            }
                except (ValueError, TypeError) as exc:
                    result = {
                        "content": json.dumps(
                            {"status": "error", "text": str(exc)}, ensure_ascii=False
                        ),
                        "finished": False,
                    }
                except BaseException:
                    failed.set()
                    raise
                if on_result is not None:
                    on_result(call.id, result)
                return call.name, call.id, result

        tasks = [asyncio.create_task(one(call)) for call in tool_calls]
        try:
            return await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

