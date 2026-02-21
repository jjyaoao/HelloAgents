# HelloAgents

> 🤖 生产级多智能体框架 - 工具响应协议、上下文工程、会话持久化、子代理机制等16项核心能力

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

HelloAgents 是一个基于 OpenAI 原生 API 构建的生产级多智能体框架，集成了工具响应协议（ToolResponse）、上下文工程（HistoryManager/TokenCounter）、会话持久化（SessionStore）、子代理机制（TaskTool）、乐观锁（文件编辑）、熔断器（CircuitBreaker）、Skills 知识外化、TodoWrite 进度管理、DevLog 决策记录、流式输出（SSE）、异步生命周期、可观测性（TraceLogger）、日志系统（四种范式）、LLM/Agent 基类重构等 16 项核心能力，为构建复杂智能体应用提供完整的工程化支持。

## 📌 版本说明

> **重要提示**：本仓库目前维护两个版本

- **📚 学习版本（推荐初学者）**：[learn_version 分支](https://github.com/jjyaoao/HelloAgents/tree/learn_version)
  与 [Datawhale Hello-Agents 教程](https://github.com/datawhalechina/hello-agents) 正文完全对应的稳定版本，适合跟随教程学习使用。

- **🚀 开发版本（当前分支）**：持续迭代中的最新代码(V1.0.0)，包含新功能和改进，部分实现可能与教程内容存在差异。如需学习教程，请切换到 `learn_version` 分支。

- **📦 历史版本**：[Releases 页面](https://github.com/jjyaoao/HelloAgents/releases)
  提供从 v0.1.1 到 v0.2.9 的所有版本，每个版本对应教程的特定章节，可根据学习进度选择对应版本。

## 🚀 快速开始

### 安装

```bash
pip install hello-agents
```

### 基本使用

```python
from hello_agents import ReActAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools.builtin import ReadTool, WriteTool, TodoWriteTool

llm = HelloAgentsLLM()
registry = ToolRegistry()
registry.register_tool(ReadTool())
registry.register_tool(WriteTool())
registry.register_tool(TodoWriteTool())

agent = ReActAgent("assistant", llm, tool_registry=registry)
agent.run("分析项目结构并生成报告")
```

### 环境配置

创建 `.env` 文件：
```bash
LLM_MODEL_ID=your-model-name
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=your-api-base-url
```

```python
# 自动检测provider
llm = HelloAgentsLLM()  # 框架自动检测为modelscope
print(f"检测到的provider: {llm.provider}")
```

> 💡 **智能检测**: 框架会根据API密钥格式和Base URL自动选择合适的provider

### 支持的LLM提供商

框架基于 **3 种适配器** 支持所有主流 LLM 服务：

#### 1. OpenAI 兼容适配器（默认）

支持所有提供 OpenAI 兼容接口的服务：

| 提供商类型   | 示例服务                               | 配置示例                             |
| ------------ | -------------------------------------- | ------------------------------------ |
| **云端 API** | OpenAI、DeepSeek、Qwen、Kimi、智谱 GLM | `LLM_BASE_URL=api.deepseek.com`      |
| **本地推理** | vLLM、Ollama、SGLang                   | `LLM_BASE_URL=http://localhost:8000` |
| **其他兼容** | 任何 OpenAI 格式接口                   | `LLM_BASE_URL=your-endpoint`         |

#### 2. Anthropic 适配器

| 提供商     | 检测条件                        | 配置示例                                 |
| ---------- | ------------------------------- | ---------------------------------------- |
| **Claude** | `base_url` 包含 `anthropic.com` | `LLM_BASE_URL=https://api.anthropic.com` |

#### 3. Gemini 适配器

| 提供商            | 检测条件                                                 | 配置示例                                                 |
| ----------------- | -------------------------------------------------------- | -------------------------------------------------------- |
| **Google Gemini** | `base_url` 包含 `googleapis.com` 或 `generativelanguage` | `LLM_BASE_URL=https://generativelanguage.googleapis.com` |

> 💡 **自动适配**：框架根据 `base_url` 自动选择适配器，无需手动指定。

## 🏗️ 项目结构

```
hello-agents/
├── hello_agents/              # 主包
│   ├── core/                  # 核心组件
│   │   ├── llm.py             # LLM 基类与配置
│   │   ├── llm_adapters.py    # 三种适配器（OpenAI/Anthropic/Gemini）
│   │   ├── agent.py           # Agent 基类（Function Calling 架构）
│   │   ├── session_store.py   # 会话持久化
│   │   ├── lifecycle.py       # 异步生命周期
│   │   └── streaming.py       # SSE 流式输出
│   ├── agents/                # Agent 实现
│   │   ├── simple_agent.py    # SimpleAgent
│   │   ├── react_agent.py     # ReActAgent
│   │   ├── reflection_agent.py # ReflectionAgent
│   │   └── plan_solve_agent.py # PlanAndSolveAgent
│   ├── tools/                 # 工具系统
│   │   ├── registry.py        # 工具注册表
│   │   ├── response.py        # ToolResponse 协议
│   │   ├── circuit_breaker.py # 熔断器
│   │   ├── tool_filter.py     # 工具过滤（子代理机制）
│   │   └── builtin/           # 内置工具
│   │       ├── file_tools.py  # 文件工具（乐观锁）
│   │       ├── task_tool.py   # 子代理工具
│   │       ├── todowrite_tool.py # 进度管理
│   │       ├── devlog_tool.py # 决策日志
│   │       └── skill_tool.py  # Skills 知识外化
│   ├── context/               # 上下文工程
│   │   ├── history.py         # HistoryManager
│   │   ├── token_counter.py   # TokenCounter
│   │   ├── truncator.py       # ObservationTruncator
│   │   └── builder.py         # ContextBuilder
│   ├── observability/         # 可观测性
│   │   └── trace_logger.py    # TraceLogger
│   └── skills/                # Skills 系统
│       └── loader.py          # SkillLoader
├── docs/                      # 文档
├── examples/                  # 示例代码
└── tests/                     # 测试用例
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

详细了解 HelloAgents v1.0.0 的 16 项核心能力：

### 基础设施
- **[工具响应协议](./docs/tool-response-protocol.md)** - ToolResponse 统一返回格式
- **[上下文工程](./docs/context-engineering-guide.md)** - HistoryManager/TokenCounter/Truncator

### 核心能力
- **[可观测性](./docs/observability-guide.md)** - TraceLogger 追踪系统
- **[熔断器](./docs/circuit-breaker-guide.md)** - CircuitBreaker 容错机制
- **[会话持久化](./docs/session-persistence-guide.md)** - SessionStore 会话管理

### 增强能力
- **[子代理机制](./docs/subagent-guide.md)** - TaskTool 与 ToolFilter
- **[Skills 知识外化](./docs/skills-usage-guide.md)** - 技能系统使用指南
- **[乐观锁](./docs/file_tools.md)** - 文件编辑工具的并发控制
- **[TodoWrite 进度管理](./docs/todowrite-usage-guide.md)** - 任务进度追踪

### 辅助功能
- **[DevLog 决策日志](./docs/devlog-guide.md)** - 开发决策记录
- **[异步生命周期](./docs/async-agent-guide.md)** - 异步 Agent 实现

### 核心架构
- **[流式输出](./docs/streaming-sse-guide.md)** - SSE 流式响应
- **[Function Calling 架构](./docs/function-calling-architecture.md)** - LLM/Agent 基类重构
- **[日志系统](./docs/logging-system-guide.md)** - 四种日志范式

### 扩展能力
- **[自定义工具扩展](./docs/custom_tools_guide.md)** - 三种工具实现方式（函数式/标准类/可展开）

---

<div align="center">

**HelloAgents** - 让智能体开发变得简单而强大 🚀
</div>

