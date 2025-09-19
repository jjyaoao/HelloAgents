# Agent系统 API 文档

## 概述

HelloAgents提供了多种Agent实现，支持不同的AI范式和使用场景。所有Agent都继承自`Agent`基类，提供统一的接口。

## Agent基类

```python
class Agent(ABC):
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None
    )
    
    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str
    
    def add_message(self, message: Message)
    def clear_history(self)
    def get_history(self) -> list[Message]
```

## SimpleAgent

最基础的对话Agent，适合简单的问答场景。

### 类定义

```python
class SimpleAgent(Agent):
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None
    )
    
    def run(self, input_text: str, **kwargs) -> str
    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]
```

### 使用示例

```python
from hello_agents import HelloAgentsLLM, SimpleAgent

# 创建LLM
llm = HelloAgentsLLM()

# 创建SimpleAgent
agent = SimpleAgent(
    name="AI助手",
    llm=llm,
    system_prompt="你是一个有用的AI助手，请用中文回答问题。"
)

# 同步对话
response = agent.run("你好！请介绍一下自己")
print(response)

# 流式对话
print("助手: ", end="", flush=True)
for chunk in agent.stream_run("什么是人工智能？"):
    print(chunk, end="", flush=True)
print()

# 查看对话历史
history = agent.get_history()
for msg in history:
    print(f"{msg.role}: {msg.content}")
```

### 特点

- ✅ 简单易用，适合快速开始
- ✅ 支持流式响应
- ✅ 自动管理对话历史
- ✅ 支持自定义系统提示

## ReActAgent

基于ReAct（Reasoning and Acting）范式的Agent，支持工具调用和推理。

### 类定义

```python
class ReActAgent(Agent):
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: ToolRegistry,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 5,
        custom_prompt: Optional[str] = None
    )

    def run(self, input_text: str, **kwargs) -> str
```

### 参数说明

- **tool_registry** (`ToolRegistry`): 工具注册表
- **max_steps** (`int`): 最大推理步数，默认5
- **custom_prompt** (`Optional[str]`): 自定义ReAct提示词模板，替换默认模板

### 使用示例

#### 默认配置
```python
from hello_agents import HelloAgentsLLM, ReActAgent, ToolRegistry
from hello_agents.tools.builtin import calculate

# 创建LLM
llm = HelloAgentsLLM()

# 创建工具注册表
registry = ToolRegistry()
registry.register_function("calculate", "数学计算工具", calculate)

# 创建ReActAgent（使用默认提示词）
agent = ReActAgent(
    name="工具助手",
    llm=llm,
    tool_registry=registry,
    max_steps=3
)

# 使用工具解决问题
response = agent.run("计算 123 * 456 + 789 的结果")
print(response)
```

#### 自定义配置
```python
# 自定义ReAct提示词模板
custom_prompt = """
你是一个专业的数学解题专家。

可用工具：{tools}

解题格式：
Thought: 分析数学问题的类型和解题策略
Action: 使用工具计算或给出最终答案

问题：{question}
历史：{history}
"""

# 创建自定义ReActAgent
custom_agent = ReActAgent(
    name="数学专家",
    llm=llm,
    tool_registry=registry,
    custom_prompt=custom_prompt,
    max_steps=3
)

# 使用自定义Agent
response = custom_agent.run("如果一个正方形的面积是64，那么它的周长是多少？")
print(response)
```

### ReAct工作流程

1. **思考（Think）**: 分析问题，决定下一步行动
2. **行动（Act）**: 调用工具或给出答案
3. **观察（Observe）**: 观察工具执行结果
4. **重复**: 直到找到答案或达到最大步数

### 特点

- ✅ 支持工具调用
- ✅ 具备推理能力
- ✅ 可处理复杂的多步骤任务
- ✅ 透明的推理过程

## ReflectionAgent

基于反思机制的Agent，能够自我评估和改进答案。

### 类定义

```python
class ReflectionAgent(Agent):
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_iterations: int = 3,
        custom_prompts: Optional[Dict[str, str]] = None
    )

    def run(self, input_text: str, **kwargs) -> str
```

### 参数说明

- **max_iterations** (`int`): 最大反思迭代次数，默认3
- **custom_prompts** (`Optional[Dict[str, str]]`): 自定义提示词模板，包含`initial`、`reflect`、`refine`三个键

### 使用示例

#### 默认配置
```python
from hello_agents import HelloAgentsLLM, ReflectionAgent

# 创建LLM
llm = HelloAgentsLLM()

# 创建ReflectionAgent（使用默认提示词）
agent = ReflectionAgent(
    name="反思助手",
    llm=llm,
    max_iterations=2
)

# 通用任务
response = agent.run("解释什么是机器学习")
print(response)
```

#### 自定义配置
```python
# 代码生成专家的自定义提示词
code_prompts = {
    "initial": """
你是一位资深的程序员。请根据以下要求编写代码：

要求: {task}

请提供完整的代码实现，包含必要的注释和文档。
""",
    "reflect": """
你是一位严格的代码评审专家。请审查以下代码：

# 原始任务: {task}
# 待审查的代码: {content}

请分析代码的质量，包括算法效率、可读性、错误处理等。
如果代码质量良好，请回答"无需改进"。
""",
    "refine": """
请根据代码评审意见优化你的代码：

# 原始任务: {task}
# 上一轮代码: {last_attempt}
# 评审意见: {feedback}

请提供优化后的代码。
"""
}

# 创建代码生成专家
code_agent = ReflectionAgent(
    name="代码专家",
    llm=llm,
    custom_prompts=code_prompts,
    max_iterations=2
)

# 代码生成与优化
response = code_agent.run("编写一个Python函数来计算斐波那契数列")
print(response)
```

### 反思工作流程

1. **初始回答**: 生成初始答案
2. **自我评估**: 评估答案质量，找出问题
3. **改进**: 基于评估结果改进答案
4. **重复**: 直到满意或达到最大迭代次数

### 特点

- ✅ 自我改进能力
- ✅ 提高答案质量
- ✅ 适合创作和代码生成
- ✅ 透明的改进过程

## PlanAndSolveAgent

基于计划和解决范式的Agent，先制定计划再逐步执行。

### 类定义

```python
class PlanAndSolveAgent(Agent):
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        custom_prompts: Optional[Dict[str, str]] = None
    )

    def run(self, input_text: str, **kwargs) -> str
```

### 参数说明

- **custom_prompts** (`Optional[Dict[str, str]]`): 自定义提示词模板，包含`planner`和`executor`两个键

### 使用示例

#### 默认配置
```python
from hello_agents import HelloAgentsLLM, PlanAndSolveAgent

# 创建LLM
llm = HelloAgentsLLM()

# 创建PlanAndSolveAgent（使用默认提示词）
agent = PlanAndSolveAgent(
    name="规划助手",
    llm=llm
)

# 通用问题分解
response = agent.run("如何学习Python编程？")
print(response)
```

#### 自定义配置
```python
# 数学问题专家的自定义提示词
math_prompts = {
    "planner": """
你是一个数学问题分解专家。请将以下数学问题分解为清晰的计算步骤。
每个步骤应该是一个具体的数学运算或逻辑推理。

数学问题: {question}

请按以下格式输出计算计划:
```python
["步骤1: 具体计算", "步骤2: 具体计算", ...]
```
""",
    "executor": """
你是一个数学计算专家。请严格按照计划执行数学计算。

# 原始问题: {question}
# 计算计划: {plan}
# 已完成的计算: {history}
# 当前计算步骤: {current_step}

请执行当前步骤的计算，只输出计算结果:
"""
}

# 创建数学专家
math_agent = PlanAndSolveAgent(
    name="数学专家",
    llm=llm,
    custom_prompts=math_prompts
)

# 数学问题分解与求解
response = math_agent.run("一个圆形花园的半径是8米，如果要在花园周围建一条宽2米的小径，小径的面积是多少？")
print(response)
```

### 工作流程

1. **理解问题**: 分析问题的复杂性和要求
2. **制定计划**: 将问题分解为可执行的步骤
3. **逐步执行**: 按计划逐步解决子问题
4. **整合答案**: 将各部分结果整合为最终答案

### 特点

- ✅ 结构化问题解决
- ✅ 适合复杂任务分解
- ✅ 清晰的执行步骤
- ✅ 提高解决方案质量

## Agent配置

### Config类

```python
class Config:
    def __init__(
        self,
        max_history: int = 10,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    )
```

### 使用配置

```python
from hello_agents import Config, SimpleAgent, HelloAgentsLLM

# 创建配置
config = Config(
    max_history=20,
    temperature=0.8,
    max_tokens=1000
)

# 使用配置创建Agent
llm = HelloAgentsLLM()
agent = SimpleAgent("配置助手", llm, config=config)
```

## 消息管理

### Message类

```python
class Message:
    def __init__(self, content: str, role: str, timestamp: Optional[datetime] = None)
    
    content: str
    role: str
    timestamp: datetime
```

### 历史记录管理

```python
# 添加消息
from hello_agents.core.message import Message

agent.add_message(Message("自定义消息", "user"))

# 获取历史记录
history = agent.get_history()
for msg in history:
    print(f"[{msg.timestamp}] {msg.role}: {msg.content}")

# 清空历史记录
agent.clear_history()
```

## 多Agent协作

### 顺序执行

```python
from hello_agents import HelloAgentsLLM, SimpleAgent, ReActAgent, ToolRegistry
from hello_agents.tools.builtin import calculate

llm = HelloAgentsLLM()

# 创建多个Agent
analyst = SimpleAgent("分析师", llm, "你是数据分析专家")
calculator = ReActAgent("计算器", llm, ToolRegistry())
calculator.tool_registry.register_function("calculate", "计算", calculate)

# 顺序协作
question = "分析一下如果投资10万元，年化收益率8%，10年后的收益"

# 第一步：分析
analysis = analyst.run(question)
print("分析结果:", analysis)

# 第二步：计算
calculation = calculator.run(f"根据分析：{analysis}，计算具体数值")
print("计算结果:", calculation)
```

### 并行处理

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def parallel_agents():
    llm = HelloAgentsLLM()
    
    agents = [
        SimpleAgent("助手1", llm, "你专注于技术分析"),
        SimpleAgent("助手2", llm, "你专注于市场分析"),
        SimpleAgent("助手3", llm, "你专注于风险分析")
    ]
    
    question = "分析人工智能行业的发展前景"
    
    # 并行执行
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(agent.run, question) for agent in agents]
        results = [future.result() for future in futures]
    
    return results

# 运行并行分析
results = asyncio.run(parallel_agents())
for i, result in enumerate(results, 1):
    print(f"助手{i}的分析: {result}")
```

## Agent自定义配置

### 设计理念

HelloAgents采用"默认优秀，自定义灵活"的设计理念：

- **默认即可用**: 所有Agent都提供高质量的默认提示词模板，无需配置即可使用
- **完全可定制**: 用户可以通过`custom_prompts`或`custom_prompt`参数完全替换默认模板
- **简洁API**: 避免过多的预设选项，保持API简洁易用

### 自定义提示词格式

#### ReflectionAgent
```python
custom_prompts = {
    "initial": "初始任务处理提示词，包含{task}占位符",
    "reflect": "反思评估提示词，包含{task}和{content}占位符",
    "refine": "改进优化提示词，包含{task}、{last_attempt}和{feedback}占位符"
}
```

#### ReActAgent
```python
custom_prompt = """
自定义ReAct提示词，包含以下占位符：
- {tools}: 可用工具列表
- {question}: 用户问题
- {history}: 执行历史
"""
```

#### PlanAndSolveAgent
```python
custom_prompts = {
    "planner": "规划器提示词，包含{question}占位符",
    "executor": "执行器提示词，包含{question}、{plan}、{history}、{current_step}占位符"
}
```

## 最佳实践

### 1. Agent选择指南

- **SimpleAgent**: 简单问答、对话聊天
- **ReActAgent**: 需要工具调用、多步推理
- **ReflectionAgent**: 代码生成、文章写作、需要质量优化
- **PlanAndSolveAgent**: 复杂问题分解、项目规划

### 2. 何时使用自定义配置

- **使用默认配置**: 快速原型开发、通用任务、学习教学
- **使用自定义配置**: 特定领域专业任务、特殊输出格式、明确工作流程要求

### 3. 系统提示优化

```python
# 好的系统提示
system_prompt = """
你是一个专业的Python编程助手。
请遵循以下原则：
1. 提供清晰、可运行的代码
2. 包含必要的注释和文档
3. 考虑错误处理和边界情况
4. 推荐最佳实践
"""

agent = SimpleAgent("Python助手", llm, system_prompt)
```

### 4. 自定义提示词设计原则

```python
# 好的自定义提示词示例
custom_prompts = {
    "initial": """
你是一个{专业角色}。请根据以下要求完成任务：

任务: {task}

请按照以下格式输出：
1. 分析: [你的分析]
2. 方案: [你的方案]
3. 总结: [关键要点]
""",
    "reflect": """
请评估以下工作成果的质量：

# 原始任务: {task}
# 当前成果: {content}

评估维度：
- 完整性: 是否完整回答了问题
- 准确性: 信息是否准确可靠
- 实用性: 是否具有实际应用价值

如果质量良好，请回答"无需改进"。
""",
    "refine": """
请根据评估意见改进工作成果：

# 原始任务: {task}
# 上一版成果: {last_attempt}
# 改进建议: {feedback}

请提供改进后的版本。
"""
}
```

### 5. 错误处理

```python
from hello_agents.core.exceptions import HelloAgentsException

try:
    response = agent.run("你的问题")
except HelloAgentsException as e:
    print(f"Agent执行失败: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

### 6. 性能优化

```python
# 使用流式响应提升用户体验
for chunk in agent.stream_run("长文本生成任务"):
    print(chunk, end="", flush=True)

# 合理设置历史记录长度
config = Config(max_history=5)  # 避免上下文过长

# 使用合适的温度参数
config = Config(temperature=0.1)  # 需要准确性
config = Config(temperature=0.8)  # 需要创造性
```

## 完整示例

### 默认配置示例
```python
from hello_agents import (
    HelloAgentsLLM, SimpleAgent, ReActAgent, ReflectionAgent, PlanAndSolveAgent,
    ToolRegistry
)
from hello_agents.tools.builtin import calculate

# 1. 创建LLM
llm = HelloAgentsLLM()

# 2. 创建不同类型的Agent（使用默认配置）
simple_agent = SimpleAgent("聊天助手", llm)
react_agent = ReActAgent("工具助手", llm, ToolRegistry())
reflection_agent = ReflectionAgent("反思助手", llm, max_iterations=2)
plan_agent = PlanAndSolveAgent("规划助手", llm)

# 3. 注册工具
react_agent.tool_registry.register_function("calculate", "计算", calculate)

# 4. 使用不同Agent
print("=== 简单对话 ===")
print(simple_agent.run("你好，介绍一下自己"))

print("\n=== 工具调用 ===")
print(react_agent.run("计算 123 * 456"))

print("\n=== 反思改进 ===")
print(reflection_agent.run("解释什么是递归算法"))

print("\n=== 计划执行 ===")
print(plan_agent.run("如何学习Python编程？"))
```

### 自定义配置示例
```python
# 创建专业化的Agent
code_prompts = {
    "initial": "你是代码专家。请编写代码：{task}",
    "reflect": "请检查代码质量：{content}",
    "refine": "请优化代码：{last_attempt}"
}

research_prompt = """
你是研究专家。可用工具：{tools}
Thought: 分析研究问题
Action: 使用工具或给出结论
问题：{question}
"""

math_prompts = {
    "planner": "分解数学问题：{question}",
    "executor": "执行计算步骤：{current_step}"
}

# 创建专业化Agent
code_agent = ReflectionAgent("代码专家", llm, custom_prompts=code_prompts)
research_agent = ReActAgent("研究专家", llm, ToolRegistry(), custom_prompt=research_prompt)
math_agent = PlanAndSolveAgent("数学专家", llm, custom_prompts=math_prompts)

# 使用专业化Agent
print("=== 代码生成 ===")
print(code_agent.run("写一个快速排序函数"))

print("\n=== 专业研究 ===")
print(research_agent.run("研究人工智能的发展趋势"))

print("\n=== 数学解题 ===")
print(math_agent.run("计算圆的面积公式"))
```
