from contextlib import aclosing

"""反思的各个阶段复用共享的工具与事件运行机制。"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING
from .simple_agent import SimpleAgent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.components import AgentComponents
from ..core.runtime import turn_events

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry


class Memory:
    """
    简单的短期记忆模块，用于存储智能体的行动与反思轨迹。
    """

    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def add_record(self, record_type: str, content: str):
        """向记忆中添加一条新记录"""
        self.records.append({"type": record_type, "content": content})

    def get_trajectory(self) -> str:
        """将所有记忆记录格式化为一个连贯的字符串文本"""
        trajectory = ""
        for record in self.records:
            if record["type"] == "execution":
                trajectory += f"--- 上一轮尝试 (代码) ---\n{record['content']}\n\n"
            elif record["type"] == "reflection":
                trajectory += f"--- 评审员反馈 ---\n{record['content']}\n\n"
        return trajectory.strip()

    def get_last_execution(self) -> str:
        """获取最近一次的执行结果"""
        for record in reversed(self.records):
            if record["type"] == "execution":
                return record["content"]
        return ""


class ReflectionAgent(SimpleAgent):
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_iterations: int = 3,
        tool_registry: Optional["ToolRegistry"] = None,
        enable_tool_calling: bool = True,
        max_tool_iterations: int = 3,
        components: Optional[AgentComponents] = None,
    ):
        """
        初始化ReflectionAgent

        Args:
            name: Agent名称
            llm: LLM实例
            system_prompt: 系统提示词（定义角色和反思策略）
            config: 配置对象
            max_iterations: 最大迭代次数
            tool_registry: 工具注册表（可选）
            enable_tool_calling: 是否启用工具调用
            max_tool_iterations: 最大工具调用迭代次数
            components: 显式组件覆盖；未指定的部分沿用 Config 默认装配
        """
        # 默认 system_prompt
        default_system_prompt = """你是一个具有自我反思能力的AI助手。你的工作流程是：
1. 首先尝试完成用户的任务
2. 然后反思你的回答，找出可能的问题或改进空间
3. 根据反思结果优化你的回答
4. 如果回答已经很好，在反思时回复"无需改进"

请始终保持批判性思维，追求更高质量的输出。"""

        # 传递 tool_registry 到基类
        super().__init__(
            name,
            llm,
            system_prompt or default_system_prompt,
            config,
            tool_registry=tool_registry,
            max_tool_iterations=max_tool_iterations,
            enable_tool_calling=enable_tool_calling,
            components=components,
        )
        self.max_iterations = max_iterations
        self.memory = Memory()
        self._reflection_iterations = 0
        self.enable_tool_calling = enable_tool_calling and tool_registry is not None
        self.max_tool_iterations = max_tool_iterations

        if type(max_iterations) is not int or max_iterations < 0:
            raise ValueError("max_iterations 必须是非负整数")

    async def _run_loop(self, messages, packets, stream, kwargs):
        task = messages[-1]["content"]
        self.memory = Memory()
        self._reflection_iterations = 0
        async with aclosing(
            self._phase(messages, packets, stream, kwargs, "execution")
        ) as source:
            async for event in source:
                yield event
        self.memory.add_record("execution", self.last_run.answer)
        if self.last_run.status != "completed":
            return
        for iteration in range(1, self.max_iterations + 1):
            self._reflection_iterations = iteration
            messages.append(
                {
                    "role": "user",
                    "content": self._build_reflection_prompt(
                        task, self.memory.get_last_execution()
                    ),
                }
            )
            async with aclosing(
                self._phase(messages, packets, stream, kwargs, "reflection")
            ) as source:
                async for event in source:
                    yield event
            feedback = self.last_run.answer
            self.memory.add_record("reflection", feedback)
            if self.last_run.status != "completed":
                return
            if "无需改进" in feedback or "no need for improvement" in feedback.lower():
                self.last_run.answer = self.memory.get_last_execution()
                messages.append({"role": "assistant", "content": self.last_run.answer})
                return
            messages.append(
                {
                    "role": "user",
                    "content": self._build_refinement_prompt(
                        task, self.memory.get_last_execution(), feedback
                    ),
                }
            )
            async with aclosing(
                self._phase(messages, packets, stream, kwargs, "refinement")
            ) as source:
                async for event in source:
                    yield event
            self.memory.add_record("execution", self.last_run.answer)
            if self.last_run.status != "completed":
                return

    async def _phase(self, messages, packets, stream, kwargs, phase):
        self.last_run.status = "running"
        stage = "initial_execution" if phase == "execution" else phase
        details = (
            {} if phase == "execution" else {"iteration": self._reflection_iterations}
        )
        yield {"kind": "step_start", "phase": stage, **details}
        async with aclosing(
            turn_events(self, messages, packets, stream=stream, kwargs=kwargs)
        ) as source:
            async for event in source:
                yield dict(event, phase=phase, **details)
        result = {"reflection": self.last_run.answer} if phase == "reflection" else {}
        yield {
            "kind": "step_finish",
            "phase": stage,
            "result": self.last_run.answer,
            **details,
            **result,
        }

    def _build_reflection_prompt(self, task, result):
        return f"请评审回答，提出具体改进意见；若已满足任务，只回答“无需改进”。\n任务：{task}\n回答：{result}"

    def _build_refinement_prompt(self, task, result, feedback):
        return f"请根据反馈改进回答。\n任务：{task}\n上一轮回答：{result}\n反馈：{feedback}"
