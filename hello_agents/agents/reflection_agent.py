"""Reflection Agent实现 - 自我反思与迭代优化的智能体"""

from typing import Optional, List, Dict, Any, TYPE_CHECKING, AsyncGenerator
import json
from datetime import datetime

from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.message import Message
from ..core.streaming import StreamEvent, StreamEventType
from ..core.lifecycle import LifecycleHook

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
        print(f"📝 记忆已更新，新增一条 '{record_type}' 记录。")

    def get_trajectory(self) -> str:
        """将所有记忆记录格式化为一个连贯的字符串文本"""
        trajectory = ""
        for record in self.records:
            if record['type'] == 'execution':
                trajectory += f"--- 上一轮尝试 (代码) ---\n{record['content']}\n\n"
            elif record['type'] == 'reflection':
                trajectory += f"--- 评审员反馈 ---\n{record['content']}\n\n"
        return trajectory.strip()

    def get_last_execution(self) -> str:
        """获取最近一次的执行结果"""
        for record in reversed(self.records):
            if record['type'] == 'execution':
                return record['content']
        return ""

class ReflectionAgent(Agent):
    """
    Reflection Agent - 自我反思与迭代优化的智能体

    这个Agent能够：
    1. 执行初始任务
    2. 对结果进行自我反思
    3. 根据反思结果进行优化
    4. 迭代改进直到满意
    5. 支持工具调用（可选）

    特别适合代码生成、文档写作、分析报告等需要迭代优化的任务。

    使用标准 Function Calling 格式，通过 system_prompt 定义角色和行为。
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_iterations: int = 3,
        tool_registry: Optional['ToolRegistry'] = None,
        enable_tool_calling: bool = True,
        max_tool_iterations: int = 3
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
            tool_registry=tool_registry
        )
        self.max_iterations = max_iterations
        self.memory = Memory()
        self.enable_tool_calling = enable_tool_calling and tool_registry is not None
        self.max_tool_iterations = max_tool_iterations

    def run(self, input_text: str, **kwargs) -> str:
        """
        运行Reflection Agent

        Args:
            input_text: 任务描述
            **kwargs: 其他参数

        Returns:
            最终优化后的结果
        """
        print(f"\n🤖 {self.name} 开始处理任务: {input_text}")

        # 重置记忆
        self.memory = Memory()

        # 1. 初始执行
        print("\n--- 正在进行初始尝试 ---")
        initial_result = self._execute_task(input_text, **kwargs)
        self.memory.add_record("execution", initial_result)

        # 2. 迭代循环：反思与优化
        for i in range(self.max_iterations):
            print(f"\n--- 第 {i+1}/{self.max_iterations} 轮迭代 ---")

            # a. 反思
            print("\n-> 正在进行反思...")
            last_result = self.memory.get_last_execution()
            feedback = self._reflect_on_result(input_text, last_result, **kwargs)
            self.memory.add_record("reflection", feedback)

            # b. 检查是否需要停止
            if "无需改进" in feedback or "no need for improvement" in feedback.lower():
                print("\n✅ 反思认为结果已无需改进，任务完成。")
                break

            # c. 优化
            print("\n-> 正在进行优化...")
            refined_result = self._refine_result(input_text, last_result, feedback, **kwargs)
            self.memory.add_record("execution", refined_result)

        final_result = self.memory.get_last_execution()
        print(f"\n--- 任务完成 ---\n最终结果:\n{final_result}")

        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(final_result, "assistant"))

        return final_result

    def _execute_task(self, task: str, **kwargs) -> str:
        """执行初始任务"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"请完成以下任务：\n\n{task}"}
        ]
        return self._get_llm_response(messages, **kwargs)

    def _reflect_on_result(self, task: str, result: str, **kwargs) -> str:
        """对结果进行反思"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""请仔细审查以下回答，并找出可能的问题或改进空间：

# 原始任务:
{task}

# 当前回答:
{result}

请分析这个回答的质量，指出不足之处，并提出具体的改进建议。
如果回答已经很好，请回答"无需改进"。"""}
        ]
        return self._get_llm_response(messages, **kwargs)

    def _refine_result(self, task: str, last_attempt: str, feedback: str, **kwargs) -> str:
        """根据反馈优化结果"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""请根据反馈意见改进你的回答：

# 原始任务:
{task}

# 上一轮回答:
{last_attempt}

# 反馈意见:
{feedback}

请提供一个改进后的回答。"""}
        ]
        return self._get_llm_response(messages, **kwargs)

    def _get_llm_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        调用LLM并获取完整响应（支持 Function Calling）

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            LLM响应文本
        """
        # 如果没有启用工具调用，直接返回
        if not self.enable_tool_calling or not self.tool_registry:
            llm_response = self.llm.invoke(messages, **kwargs)
            return llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

        # 启用工具调用模式
        tool_schemas = self._build_tool_schemas()
        current_iteration = 0

        while current_iteration < self.max_tool_iterations:
            current_iteration += 1

            try:
                response = self.llm.invoke_with_tools(
                    messages=messages,
                    tools=tool_schemas,
                    tool_choice="auto",
                    **kwargs
                )
            except Exception as e:
                print(f"❌ LLM 调用失败: {e}")
                break

            # 处理工具调用
            tool_calls = response.tool_calls
            if not tool_calls:
                # 没有工具调用，返回文本响应
                return response.content or ""

            # 将助手消息添加到历史
            messages.append({
                "role": "assistant",
                "content": response.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments
                        }
                    }
                    for tc in tool_calls
                ]
            })

            # 执行所有工具调用
            for tool_call in tool_calls:
                tool_name = tool_call.name
                tool_call_id = tool_call.id

                try:
                    arguments = json.loads(tool_call.arguments)
                except json.JSONDecodeError as e:
                    print(f"❌ 工具参数解析失败: {e}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": f"错误：参数格式不正确 - {str(e)}"
                    })
                    continue

                # 执行工具（复用基类方法）
                result = self._execute_tool_call(tool_name, arguments)

                # 添加工具结果到消息
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result
                })

        # 如果超过最大迭代次数，获取最后一次回答
        if current_iteration >= self.max_tool_iterations:
            llm_response = self.llm.invoke(messages, **kwargs)
            return llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

        return ""

    async def arun_stream(
        self,
        input_text: str,
        on_start: LifecycleHook = None,
        on_finish: LifecycleHook = None,
        on_error: LifecycleHook = None,
        **kwargs
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        ReflectionAgent 真正的流式执行

        实时返回：
        - 初始执行阶段的 LLM 输出
        - 反思阶段的思考过程
        - 优化阶段的 LLM 输出

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
            # 阶段 1：初始执行
            yield StreamEvent.create(
                StreamEventType.STEP_START,
                self.name,
                phase="initial_execution",
                description="生成初始回答"
            )

            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})

            for msg in self._history:
                messages.append({"role": msg.role, "content": msg.content})

            messages.append({"role": "user", "content": input_text})

            # 流式获取初始回答
            initial_response = ""
            async for chunk in self.llm.astream_invoke(messages, **kwargs):
                initial_response += chunk
                yield StreamEvent.create(
                    StreamEventType.LLM_CHUNK,
                    self.name,
                    chunk=chunk,
                    phase="execution"
                )

            yield StreamEvent.create(
                StreamEventType.STEP_FINISH,
                self.name,
                phase="initial_execution",
                result=initial_response
            )

            # 阶段 2：反思与优化循环
            current_response = initial_response

            for iteration in range(self.max_iterations):
                # 反思阶段
                yield StreamEvent.create(
                    StreamEventType.STEP_START,
                    self.name,
                    phase="reflection",
                    iteration=iteration + 1,
                    description=f"第 {iteration + 1} 次反思"
                )

                reflection_prompt = self._build_reflection_prompt(input_text, current_response)
                reflection_messages = [{"role": "user", "content": reflection_prompt}]

                reflection = ""
                async for chunk in self.llm.astream_invoke(reflection_messages, **kwargs):
                    reflection += chunk
                    yield StreamEvent.create(
                        StreamEventType.THINKING,
                        self.name,
                        chunk=chunk,
                        phase="reflection",
                        iteration=iteration + 1
                    )

                yield StreamEvent.create(
                    StreamEventType.STEP_FINISH,
                    self.name,
                    phase="reflection",
                    iteration=iteration + 1,
                    reflection=reflection
                )

                # 优化阶段
                yield StreamEvent.create(
                    StreamEventType.STEP_START,
                    self.name,
                    phase="refinement",
                    iteration=iteration + 1,
                    description=f"第 {iteration + 1} 次优化"
                )

                refinement_prompt = self._build_refinement_prompt(
                    input_text,
                    current_response,
                    reflection
                )
                refinement_messages = [{"role": "user", "content": refinement_prompt}]

                refined_response = ""
                async for chunk in self.llm.astream_invoke(refinement_messages, **kwargs):
                    refined_response += chunk
                    yield StreamEvent.create(
                        StreamEventType.LLM_CHUNK,
                        self.name,
                        chunk=chunk,
                        phase="refinement",
                        iteration=iteration + 1
                    )

                yield StreamEvent.create(
                    StreamEventType.STEP_FINISH,
                    self.name,
                    phase="refinement",
                    iteration=iteration + 1,
                    result=refined_response
                )

                current_response = refined_response

            # 发送完成事件
            yield StreamEvent.create(
                StreamEventType.AGENT_FINISH,
                self.name,
                result=current_response,
                total_iterations=self.max_iterations
            )

            # 保存到历史
            self.add_message(Message(input_text, "user"))
            self.add_message(Message(current_response, "assistant"))

        except Exception as e:
            # 发送错误事件
            yield StreamEvent.create(
                StreamEventType.ERROR,
                self.name,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
