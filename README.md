# HelloAgents

[![PyPI version](https://badge.fury.io/py/hello-agents.svg)](https://badge.fury.io/py/hello-agents)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`HelloAgents` 是一个灵活、可扩展的开源多智能体框架，旨在帮助开发者快速构建、测试和部署基于大型语言模型（LLM）的智能体应用。无论是单个智能体、RAG（检索增强生成）应用，还是复杂的多智能体协作系统，`HelloAgents` 都提供了坚实的基础和便捷的工具。

## ✨ 核心特性

- 🧠 **统一LLM接口**: 支持OpenAI、Anthropic、阿里云等主流LLM厂商
- 🔧 **模块化设计**: 核心组件可独立使用，灵活组合
- 🤝 **多智能体协作**: 内置多种编排模式，支持复杂协作场景
- 📚 **上下文工程**: 先进的上下文管理和优化技术
- 🧠 **智能记忆**: 支持工作记忆、向量记忆和RAG系统
- 🌐 **标准协议**: 支持MCP、A2A、ANP等通信协议
- 📊 **完整评估**: 内置多维度评估指标和基准测试

## 🚀 快速开始

### 安装

```bash
pip install hello-agents
```

### 基础使用

```python
from hello_agents import SimpleAgent, HelloAgentsLLM

# 创建LLM实例
llm = HelloAgentsLLM(
    model="gpt-4",
    api_key="your-openai-api-key"
)

# 创建智能体
agent = SimpleAgent(
    name="assistant",
    llm=llm,
    system_prompt="你是一个有用的AI助手"
)

# 开始对话
response = agent.run("你好，请介绍一下自己")
print(response)
```

### 工具智能体

```python
from hello_agents import ToolAgent, HelloAgentsLLM
from hello_agents.tools.builtin import SearchTool, CalculatorTool

# 创建带工具的智能体
agent = ToolAgent(
    name="research_assistant",
    llm=HelloAgentsLLM(model="gpt-4", api_key="your-key"),
    tools=[SearchTool(), CalculatorTool()]
)

# 使用工具解决问题
response = agent.run("帮我搜索一下2024年AI发展趋势，并计算相关数据")
```

### 多智能体协作

```python
from hello_agents.orchestration import SequentialOrchestrator
from hello_agents import SimpleAgent, HelloAgentsLLM

# 创建多个智能体
researcher = SimpleAgent("researcher", llm, "你是一个研究员")
writer = SimpleAgent("writer", llm, "你是一个技术写手")
reviewer = SimpleAgent("reviewer", llm, "你是一个内容审核员")

# 创建协作流程
orchestrator = SequentialOrchestrator([researcher, writer, reviewer])

# 执行协作任务
result = orchestrator.run("写一篇关于AI Agent的技术文章")
```

## 📖 核心概念

### 智能体类型

- **SimpleAgent**: 基础对话智能体
- **ToolAgent**: 支持工具调用的智能体
- **ConversationalAgent**: 带记忆的对话智能体

### 编排模式

- **Sequential**: 顺序执行
- **Parallel**: 并行执行
- **Hierarchical**: 分层管理
- **Debate**: 辩论模式
- **Consensus**: 共识决策

### 通信协议

- **MCP**: Model Context Protocol
- **A2A**: Agent-to-Agent Protocol
- **ANP**: Agent Network Protocol

## 🏗️ 架构设计

```
hello_agents/
├── core/           # 核心框架
├── agents/         # 智能体实现
├── tools/          # 工具系统
├── context/        # 上下文工程
├── memory/         # 记忆系统
├── protocols/      # 通信协议
├── orchestration/  # 多智能体编排
└── evaluation/     # 评估指标
```

## 📚 文档与教程

- [快速开始指南](./docs/quickstart.md)
- [API文档](./docs/api/)
- [教程示例](./examples/)
- [最佳实践](./docs/best_practices.md)

## 🤝 贡献

我们欢迎来自社区的任何贡献！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者和研究者。

---

**HelloAgents** - 让智能体开发变得简单而强大 🚀

