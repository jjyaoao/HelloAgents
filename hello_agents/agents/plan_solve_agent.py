from contextlib import aclosing

"""通过通用 Agent 运行机制完成规划与分步执行。"""

import asyncio
import json
from typing import Optional, List, Dict, TYPE_CHECKING
from .simple_agent import SimpleAgent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.components import AgentComponents
from ..core.runtime import turn_events, stopped_by_limit, deadline

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry


class Planner:
    def __init__(self, llm_client: HelloAgentsLLM, system_prompt: Optional[str] = None):
        self.llm_client = llm_client
        self.system_prompt = (
            system_prompt
            or """你是一个顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。"""
        )

    def plan(self, question: str, **kwargs) -> List[str]:
        """
        生成执行计划（使用 Function Calling）

        Args:
            question: 要解决的问题
            **kwargs: LLM调用参数

        Returns:
            步骤列表
        """

        # 定义计划生成工具
        plan_tool = {
            "type": "function",
            "function": {
                "name": "generate_plan",
                "description": "生成解决问题的分步计划",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "按顺序排列的执行步骤列表",
                        }
                    },
                    "required": ["steps"],
                },
            },
        }

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": f"请调用 generate_plan 工具提交以下问题的执行计划，不要仅用文字描述：\n\n{question}",
            },
        ]

        kwargs = dict(kwargs)
        kwargs.pop("tool_choice", None)  # 业务工具的选择设置不用于规划阶段。

        response = self.llm_client.invoke_with_tools(
            messages=messages,
            tools=[plan_tool],
            tool_choice="auto",
            **kwargs,
        )

        if stopped_by_limit(response.finish_reason):
            raise ValueError("计划输出超过模型限制，未执行不完整计划")
        if len(response.tool_calls or []) != 1 or response.tool_calls[0].name != "generate_plan":
            raise ValueError("模型未返回 generate_plan 请求")
        arguments = json.loads(response.tool_calls[0].arguments)
        steps = arguments.get("steps") if isinstance(arguments, dict) else None
        if (
            not isinstance(steps, list)
            or not steps
            or any(not isinstance(step, str) or not step.strip() for step in steps)
        ):
            raise ValueError("计划必须包含非空的步骤字符串列表")
        self.last_response = response
        return steps


class Executor:
    def __init__(
        self,
        llm_client: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        tool_registry: Optional["ToolRegistry"] = None,
        enable_tool_calling: bool = True,
        max_tool_iterations: int = 3,
    ):
        self.llm_client = llm_client
        self.system_prompt = (
            system_prompt
            or """你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。
请专注于解决当前步骤，并输出该步骤的最终答案。"""
        )
        self.tool_registry = tool_registry
        self.enable_tool_calling = enable_tool_calling and tool_registry is not None
        self.max_tool_iterations = max_tool_iterations

    def _format_plan(self, plan: List[str]) -> str:
        """格式化计划列表"""
        return "\n".join([f"{i}. {step}" for i, step in enumerate(plan, 1)])

    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """格式化历史记录"""
        return "\n\n".join(
            [
                f"步骤 {i}: {h['step']}\n结果: {h['result']}"
                for i, h in enumerate(history, 1)
            ]
        )

    def step_prompt(self, question, plan, history, step):
        return (
            f"原始任务：{question}\n完整计划：\n{self._format_plan(plan)}\n"
            f"已完成的步骤：\n{self._format_history(history) or '无'}\n"
            f"当前步骤：{step}\n请执行当前步骤并给出结果。"
        )

    def execute(self, question, plan, **kwargs):
        if not plan:
            raise ValueError("执行计划不能为空")
        history = []
        for step in plan:
            result = self._execute_step(
                self.step_prompt(question, plan, history, step), **kwargs
            )
            history.append({"step": step, "result": result})
        return history[-1]["result"]

    def _execute_step(self, context, **kwargs):
        # 独立的 Executor 借用注册表，不向其中注册工具。
        config = Config(
            trace_enabled=False,
            session_enabled=False,
            skills_enabled=False,
            subagent_enabled=False,
            todowrite_enabled=False,
            devlog_enabled=False,
        )
        agent = SimpleAgent(
            "executor",
            self.llm_client,
            self.system_prompt,
            config,
            tool_registry=self.tool_registry,
            enable_tool_calling=self.enable_tool_calling,
            max_tool_iterations=self.max_tool_iterations,
        )
        answer = agent.run(context, **kwargs)
        if agent.last_run.status != "completed":
            raise RuntimeError(f"步骤未完成：{agent.last_run.status}")
        return answer


class PlanSolveAgent(SimpleAgent):
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        planner_prompt: Optional[str] = None,
        executor_prompt: Optional[str] = None,
        tool_registry: Optional["ToolRegistry"] = None,
        enable_tool_calling: bool = True,
        max_tool_iterations: int = 3,
        components: Optional[AgentComponents] = None,
    ):
        """
        初始化PlanSolveAgent

        Args:
            name: Agent名称
            llm: LLM实例
            system_prompt: 系统提示词（Agent级别）
            config: 配置对象
            planner_prompt: 规划器的系统提示词（可选）
            executor_prompt: 执行器的系统提示词（可选）
            tool_registry: 工具注册表（可选）
            enable_tool_calling: 是否启用工具调用
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
            enable_tool_calling=enable_tool_calling,
            max_tool_iterations=max_tool_iterations,
            components=components,
        )

        self.planner = Planner(self.llm, planner_prompt)
        self.executor = Executor(
            self.llm,
            executor_prompt,
            tool_registry=tool_registry,
            enable_tool_calling=enable_tool_calling,
            max_tool_iterations=max_tool_iterations,
        )

    async def _run_loop(self, messages, packets, stream, kwargs):
        task = messages[-1]["content"]
        yield {"kind": "step_start", "phase": "planning", "description": "生成执行计划"}
        async with deadline(self.config.llm_async_timeout):
            plan = await asyncio.to_thread(self.planner.plan, task, **kwargs)
        self.last_run.model_calls += 1
        response = getattr(self.planner, "last_response", None)
        yield {
            "kind": "model",
            "usage": getattr(response, "usage", {}) or {},
            "step": self.last_run.model_calls,
            "content": "",
            "phase": "planning",
        }
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            self.last_run.usage[key] = self.last_run.usage.get(key, 0) + (
                getattr(response, "usage", {}) or {}
            ).get(key, 0)
        self._plan_total_steps = len(plan)
        yield {
            "kind": "step_finish",
            "phase": "planning",
            "plan": plan,
            "total_steps": len(plan),
        }
        history = []
        for index, step in enumerate(plan, 1):
            messages.append(
                {
                    "role": "user",
                    "content": self.executor.step_prompt(task, plan, history, step),
                }
            )
            # 添加执行器角色时，保留调用方的系统指令。
            execution = [
                {"role": "system", "content": self.executor.system_prompt},
                *messages,
            ]
            boundary = len(execution)
            self.last_run.status = "running"
            yield {
                "kind": "step_start",
                "phase": "execution",
                "step": index,
                "total_steps": len(plan),
                "description": step,
            }
            try:
                async with aclosing(
                    turn_events(self, execution, packets, stream=stream, kwargs=kwargs)
                ) as source:
                    async for event in source:
                        yield dict(
                            event, phase="execution", plan_step=index, step=index
                        )
            finally:
                messages.extend(execution[boundary:])
            history.append({"step": step, "result": self.last_run.answer})
            yield {
                "kind": "step_finish",
                "phase": "execution",
                "step": index,
                "result": self.last_run.answer,
            }
            if self.last_run.status != "completed":
                return
