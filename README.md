# HelloAgents

> 🤖 从零开始构建的多智能体框架 - 轻量级、原生、教学友好

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![OpenAI Compatible](https://img.shields.io/badge/OpenAI-Compatible-green.svg)](https://platform.openai.com/docs/api-reference)

HelloAgents是一个专为学习和教学设计的多智能体框架，基于OpenAI原生API构建，提供了从简单对话到复杂推理的完整Agent范式实现。

为了彻底贯彻轻量级与教学友好的理念，HelloAgents在架构上做出了一个关键的简化：除了核心的Agent类，一切皆为Tools。在许多其他框架中需要独立学习的Memory（记忆）、RAG（检索增强生成）、RL（强化学习）、MCP（协议）等模块，在HelloAgents中都被统一抽象为一种“工具”。这种设计的初衷是消除不必要的抽象层，让学习者可以回归到最直观的“智能体调用工具”这一核心逻辑上，从而真正实现快速上手和深入理解的统一。

## 🚀 快速开始

### 系统要求

- **Python 3.10+** （必需）
- 支持的操作系统：Windows、macOS、Linux

### 安装

####  标准安装方式

**基础功能（核心Agent）**
```bash
pip install hello-agents
```

**按需选择功能模块**
```bash
# 搜索功能
pip install hello-agents[search]

# 记忆系统
pip install hello-agents[memory]

# RAG文档问答
pip install hello-agents[rag]

# 记忆+RAG完整功能
pip install hello-agents[memory-rag]

# 协议系统
pip install hello-agents[protocols]

# 智能体性能评估
pip install hello-agents[evaluation]

# 强化学习训练
pip install hello-agents[rl]

# 全部功能（推荐）
pip install hello-agents[all]
```

**从源码安装**
```bash
git clone https://github.com/your-repo/hello-agents.git
cd hello-agents
pip install -e .[all]
```

#### 🔧 环境配置

创建 `.env` 文件：
```bash
# 模型名称
LLM_MODEL_ID=your-model-name

# API密钥
LLM_API_KEY=your-api-key-here

# 服务地址
LLM_BASE_URL=your-api-base-url
```

> 📖 详细安装指南请参考 [CONFIGURATION.md](https://github.com/jjyaoao/HelloAgents/blob/main/docs/tutorials/CONFIGURATION.md)

### 基本使用

```python
from hello_agents import SimpleAgent, HelloAgentsLLM

# 创建LLM实例 - 框架自动检测provider
llm = HelloAgentsLLM()

# 或手动指定provider（可选）
# llm = HelloAgentsLLM(provider="modelscope")

# 创建SimpleAgent
agent = SimpleAgent(
    name="AI助手",
    llm=llm,
    system_prompt="你是一个有用的AI助手"
)

# 开始对话
response = agent.run("你好！请介绍一下自己")
print(response)

# 流式对话
print("助手: ", end="", flush=True)
for chunk in agent.stream_run("什么是人工智能？"):
    print(chunk, end="", flush=True)
print()

# 检查自动检测结果
print(f"自动检测的provider: {llm.provider}")
```

## 🤖 Agent范式详解

### 1. ReActAgent - 推理与行动结合

适用场景：需要外部信息、工具调用的任务

```python
from hello_agents import ReActAgent, ToolRegistry, search, calculate

# 创建工具注册表
tool_registry = ToolRegistry()
tool_registry.register_function("search", "网页搜索工具", search)
tool_registry.register_function("calculate", "数学计算工具", calculate)

# 创建ReAct Agent
react_agent = ReActAgent(
    name="研究助手",
    llm=llm,
    tool_registry=tool_registry,
    max_steps=5
)

# 执行需要工具的任务
result = react_agent.run("搜索最新的GPT-4发展情况，并计算其参数量相比GPT-3的增长倍数")
```

### 2. ReflectionAgent - 自我反思与迭代优化

适用场景：代码生成、文档写作等需要迭代优化的任务

```python
from hello_agents import ReflectionAgent

# 创建Reflection Agent
reflection_agent = ReflectionAgent(
    name="代码专家",
    llm=llm,
    max_iterations=3
)

# 生成并优化代码
code = reflection_agent.run("编写一个高效的素数筛选算法，要求时间复杂度尽可能低")
print(f"最终代码:\n{code}")
```

### 3. PlanAndSolveAgent - 分解规划与逐步执行

适用场景：复杂多步骤问题、数学应用题、逻辑推理

```python
from hello_agents import PlanAndSolveAgent

# 创建Plan and Solve Agent
plan_agent = PlanAndSolveAgent(name="问题解决专家", llm=llm)

# 解决复杂问题
problem = """
一家公司第一年营收100万，第二年增长20%，第三年增长15%。
如果每年的成本是营收的70%，请计算三年的总利润。
"""
answer = plan_agent.run(problem)
```

## 🛠️ 工具系统

HelloAgents提供了完整的工具生态系统：

### 内置工具

```python
from hello_agents import ToolRegistry, SearchTool, CalculatorTool

# 方式1：使用Tool对象（推荐）
registry = ToolRegistry()
registry.register_tool(SearchTool())
registry.register_tool(CalculatorTool())

# 方式2：直接注册函数（简便）
def my_tool(input_text: str) -> str:
    return f"处理结果: {input_text}"

registry.register_function("my_tool", "自定义工具描述", my_tool)
```

### 目前支持的工具

- **🔍 SearchTool**: 网页搜索（支持Tavily、SerpApi、模拟搜索）
- **🧮 CalculatorTool**: 数学计算（支持复杂表达式和数学函数）
- **🔧 自定义工具**: 支持任意Python函数注册为工具

## ⚙️ 配置详解

HelloAgents支持灵活的配置方式，**参数优先，环境变量兜底**：

### 🎯 统一配置格式（推荐）

编辑 `.env` 文件，配置你的API密钥。

只需配置4个环境变量，框架自动检测provider：

```env
LLM_MODEL_ID=your-model-id
LLM_API_KEY=ms-your_api_key_here
LLM_BASE_URL=your-api-base-url
LLM_TIMEOUT=60
```

```python
# 自动检测provider
llm = HelloAgentsLLM()  # 框架自动检测为modelscope
print(f"检测到的provider: {llm.provider}")
```

> 💡 **智能检测**: 框架会根据API密钥格式和Base URL自动选择合适的provider

### 支持的LLM提供商

| 提供商 | 自动检测 | 专用环境变量 | 统一配置示例 |
|--------|----------|-------------|-------------|
| **ModelScope** | ✅ | `MODELSCOPE_API_KEY` | `LLM_API_KEY=ms-xxx...` |
| **OpenAI** | ✅ | `OPENAI_API_KEY` | `LLM_API_KEY=sk-xxx...` |
| **DeepSeek** | ✅ | `DEEPSEEK_API_KEY` | `LLM_BASE_URL=api.deepseek.com` |
| **通义千问** | ✅ | `DASHSCOPE_API_KEY` | `LLM_BASE_URL=dashscope.aliyuncs.com` |
| **月之暗面 Kimi** | ✅ | `KIMI_API_KEY` | `LLM_BASE_URL=api.moonshot.cn` |
| **智谱AI GLM** | ✅ | `ZHIPU_API_KEY` | `LLM_BASE_URL=open.bigmodel.cn` |
| **Ollama** | ✅ | `OLLAMA_API_KEY` | `LLM_BASE_URL=localhost:11434` |
| **vLLM** | ✅ | `VLLM_API_KEY` | `LLM_BASE_URL=localhost:8000` |
| **其他本地部署** | ✅ | - | `LLM_BASE_URL=localhost:PORT` |


## 🎮 完整示例

运行完整的交互式演示：

```bash
python examples/chapter07_basic_setup.py
```

这个示例包含：
- ✅ 四种Agent范式的演示
- ✅ 工具系统的使用
- ✅ 交互式Agent选择
- ✅ 流式响应体验

## 🏗️ 项目结构

```
hello-agents/
├── hello_agents/           # 主包
│   ├── core/              # 核心组件
│   │   ├── llm.py         # LLM抽象层
│   │   ├── agent.py       # Agent基类
│   │   └── ...
│   ├── agents/            # Agent实现
│   │   ├── simple.py      # SimpleAgent
│   │   ├── react_agent.py # ReActAgent
│   │   └── ...
│   └── tools/             # 工具系统
│       ├── registry.py    # 工具注册表
│       └── builtin/       # 内置工具
├── examples/              # 示例代码
└── tests/                 # 测试用例
```

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

**许可证要点**：
- ✅ **署名** (Attribution): 使用时需要注明原作者
- ✅ **相同方式共享** (ShareAlike): 修改后的作品需使用相同许可证
- ⚠️ **非商业性使用** (NonCommercial): 不得用于商业目的

如需商业使用，请联系项目维护者获取授权。

## 🙏 致谢

- 感谢 [Datawhale](https://github.com/datawhalechina) 提供的优秀开源教程
- 感谢 [Hello-Agents 教程](https://github.com/datawhalechina/hello-agents) 的所有贡献者
- 感谢所有为智能体技术发展做出贡献的研究者和开发者

## 📚 文档资源

### 📋 API文档
- **[LLM接口](./docs/api/core/llm.md)** - 统一LLM接口
- **[Agent系统](./docs/api/agents/index.md)** - 经典Agent范式
- **[工具系统](./docs/api/tools/index.md)** - 工具注册和自定义开发

### 📖 教程指南
- **[配置指南](./docs/tutorials/CONFIGURATION.md)** - 详细的配置说明
- **[本地部署指南](./docs/tutorials/LOCAL_DEPLOYMENT_GUIDE.md)** - Ollama、vLLM部署
- **[Datawhale Hello-Agents 教程](https://github.com/datawhalechina/hello-agents)** - 原版教程

### 示例代码

- **[快速开始](./examples/chapter07_basic_setup.py)** - 立即体验

---

<div align="center">

**HelloAgents** - 让智能体开发变得简单而强大 🚀
</div>

