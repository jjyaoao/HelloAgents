# HelloAgents

> 🤖 组件化多智能体框架 - Agent Loop、工具执行、上下文工程、知识检索与持久记忆

<p>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12--3.13-blue.svg" alt="Python 3.12–3.13" style="display: inline-block; vertical-align: middle; margin: 0;" /></a>
  <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/"><img src="https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg" alt="License: CC BY-NC-SA 4.0" style="display: inline-block; vertical-align: middle; margin: 0;" /></a>
</p>

HelloAgents 是一个围绕原生 Function Calling 构建的**组件化多智能体框架**，从简单的工具调用循环，到具备上下文管理、知识检索、持久记忆与多智能体协作的应用，为智能体开发提供可组合的工程组件。

框架集成**工具响应协议、上下文工程、会话持久化、子代理、Skills、流式输出与运行追踪**，并提供 **MCP 工具接入、RAG 与 GraphRAG、结构化用户画像、语义记忆检索和后台任务**。通过 `SimpleAgent` 快速搭建 Agent Loop，再按需加入执行权限、调用预算、熔断与恢复机制；检索、记忆和上下文组件也可独立使用。

## 📌 版本说明

> **重要提示**：本仓库目前维护两个版本

- **📚 学习版本（推荐初学者）**：[learn_version 分支](https://github.com/jjyaoao/HelloAgents/tree/learn_version)
  与 [Datawhale Hello-Agents 教程](https://github.com/datawhalechina/hello-agents) 正文完全对应的稳定版本，适合跟随教程学习使用。

- **🚀 当前版本（v1.0.1）**：提供工具调用、上下文、检索记忆与组件组合，文档和案例均按当前源码维护。跟随 Hello-Agents 原教程时，请使用 `learn_version` 分支。

- **🔁 AtomGit 镜像仓库**：[https://atomgit.com/jjyaoao/HelloAgents](https://atomgit.com/jjyaoao/HelloAgents) — 用于同步 GitHub 仓库内容，便于国内网络环境访问。

- **📦 历史版本**：[Releases 页面](https://github.com/jjyaoao/HelloAgents/releases)
  提供从 v0.1.1 到 v0.2.9 的所有版本，每个版本对应教程的特定章节，可根据学习进度选择对应版本。

- **🐹 Golang 开发版本**：[HelloAgents-go](https://github.com/chaojixinren/HelloAgents-go)
  社区贡献的 HelloAgents 的 Go 语言重实现版本，适合 Go 语言开发者使用。

- **🔷 TypeScript 开发版本**：[HelloAgents-ts](https://github.com/JunLang-7/HelloAgents-ts)
  社区贡献的 HelloAgents 的 TypeScript 语言重实现版本，适合 TypeScript 语言开发者使用。

## 🚀 快速开始

### 安装

推荐使用 64 位 Python 3.13，也支持 Python 3.12。在仓库根目录选择一种安装方式；3.12 运行时显示推荐提示，不会因此停止。

使用 uv：

```bash
uv sync --locked
uv run --locked python -X utf8 -m examples.agents.async_agent_demo
```

使用 pip（先创建并激活虚拟环境）：

```bash
python -m pip install -r requirements.txt
python -X utf8 -m examples.agents.async_agent_demo
```

更多安装选项见[安装指南](docs/installation.md)，按功能查看[示例代码](examples/README.md)。

### 基本使用

```python
from dotenv import load_dotenv
from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools import CalculatorTool

load_dotenv()  # 显式加载当前应用的 .env

registry = ToolRegistry()
registry.register_tool(CalculatorTool())
with HelloAgentsLLM() as llm:
    agent = SimpleAgent("assistant", llm, tool_registry=registry)
    print(agent.run("调用计算器计算两晚住宿每晚 320 元，加上 180 元交通费的总预算"))
```

`SimpleAgent` 执行“模型请求 → 工具执行 → 回执 → 再次调用”的循环。默认不自动注册 Skills、子代理、待办或日志工具，也不创建会话与追踪目录；需要时通过 `Config` 或 `AgentComponents` 开启。详见[运行循环](docs/runtime-guide.md)。

### 环境配置

创建 `.env` 文件：
```bash
LLM_MODEL_ID=your-model-name
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=your-api-base-url
```

```python
# 根据服务地址选择适配器
llm = HelloAgentsLLM()
print(f"检测到的 provider: {llm.provider}")
```

> 💡 **智能检测**: 框架根据 Base URL 选择适配器；模型名称与密钥由环境配置提供

### 支持的 LLM 提供商

框架提供 **3 种适配器**。服务需要支持对应的消息与工具调用协议：

#### 1. OpenAI 兼容适配器（默认）

支持所有提供 OpenAI 兼容接口的服务：

| 提供商类型   | 示例服务                               | 配置示例                             |
| ------------ | -------------------------------------- | ------------------------------------ |
| **云端 API** | OpenAI、DeepSeek、Qwen、Kimi、智谱 GLM | `LLM_BASE_URL=https://api.deepseek.com`      |
| **本地推理** | vLLM、Ollama、SGLang                   | `LLM_BASE_URL=http://localhost:8000/v1` |
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

### 组件扩展

检索、记忆与上下文可以独立使用，也可以通过 `AgentComponents` 注入运行组件。示例：[旅行助手](examples/applications/travel_assistant.py) · [工具与会话恢复](examples/agents/runtime_features.py)。两者默认均可离线运行，具体用法见下方文档。

## 🏗️ 项目结构

```
hello-agents/
├── hello_agents/                      # 主包
│   ├── core/                          # 核心组件
│   │   ├── llm.py                     # LLM 基类与配置
│   │   ├── llm_adapters.py            # OpenAI / Anthropic / Gemini
│   │   ├── agent.py                   # Agent 基类（Function Calling 架构）
│   │   ├── components.py              # AgentComponents
│   │   ├── runtime.py                 # 模型与工具运行循环
│   │   ├── budget.py                  # 跨模型共享调用预算
│   │   ├── session_store.py           # 会话持久化
│   │   ├── lifecycle.py               # 异步生命周期
│   │   └── streaming.py               # SSE 流式输出
│   ├── agents/                        # Agent 实现
│   │   ├── simple_agent.py            # SimpleAgent
│   │   ├── react_agent.py             # ReActAgent
│   │   ├── reflection_agent.py        # ReflectionAgent
│   │   └── plan_solve_agent.py        # PlanSolveAgent
│   ├── tools/                         # 工具系统
│   │   ├── registry.py                # 工具注册表
│   │   ├── response.py                # ToolResponse 协议
│   │   ├── circuit_breaker.py         # 熔断器
│   │   ├── mcp.py                     # MCP stdio / HTTP 工具桥接
│   │   ├── permissions.py             # 宿主执行权限
│   │   ├── tool_filter.py             # 工具过滤（子代理机制）
│   │   └── builtin/                   # 内置工具
│   │       ├── file_tools.py          # 文件工具（乐观锁）
│   │       ├── task_tool.py           # 子代理工具
│   │       ├── todowrite_tool.py      # 进度管理
│   │       ├── devlog_tool.py         # 决策日志
│   │       ├── skill_tool.py          # Skills 知识外化
│   │       ├── rag_tool.py            # 检索与来源回读
│   │       ├── memory_tool.py         # 记忆维护
│   │       ├── graphrag_tool.py       # 图检索与全局综合
│   │       └── relation_tool.py       # 关系证据检索
│   ├── context/                       # 上下文工程
│   │   ├── history.py                 # HistoryManager
│   │   ├── token_counter.py           # TokenCounter
│   │   ├── truncator.py               # ObservationTruncator
│   │   ├── builder.py                 # ContextBuilder 与预算诊断
│   │   ├── types.py                   # ContextPacket / ContextBuildResult
│   │   └── providers.py               # 上下文收集与组装
│   ├── retrieval/                     # 检索组件
│   │   ├── store.py                   # RAGStore / BM25
│   │   ├── embeddings.py              # 可替换向量模型
│   │   ├── qdrant.py                  # Qdrant 向量索引
│   │   ├── hybrid.py                  # 多路排名融合
│   │   ├── pipeline.py                # 召回后端与重排协议
│   │   ├── rerank.py                  # 模型重排
│   │   ├── evaluation.py              # 检索效果评测
│   │   ├── graph/                     # 抽取、Leiden 社区与图查询
│   │   └── relations.py               # RelationStore
│   ├── memory/                        # 用户画像、记忆记录与召回
│   │   ├── store.py                   # 记忆存储与修订
│   │   ├── search.py                  # 语义与混合记忆召回
│   │   └── profile.py                 # ProfileStore 用户画像与上下文注入
│   ├── background/                    # 持久任务、租约与恢复
│   ├── storage.py                     # 数据库版本、迁移与备份
│   ├── observability/                 # 可观测性
│   │   └── trace_logger.py            # TraceLogger
│   └── skills/                        # Skills 系统
│       └── loader.py                  # SkillLoader
├── docs/                              # 文档
├── examples/                          # 按功能组织的示例
│   ├── agents/                        # Agent Loop 与异步执行
│   ├── tools/                         # 工具、MCP 与 Skills
│   ├── context/                       # 上下文与会话
│   ├── retrieval/                     # RAG 与 GraphRAG
│   ├── memory/                        # 用户画像与语义记忆
│   ├── runtime/                       # 后台任务与运行观测
│   ├── applications/                  # 综合案例
│   └── web/                           # SSE 服务与客户端
├── tests/                             # 测试用例
├── requirements/                      # 按功能导出的 pip 锁定清单
├── scripts/sync_requirements.py        # 从 uv.lock 导出并检查清单
├── pyproject.toml                     # 依赖范围与包配置
├── uv.lock                            # uv 锁定结果
└── requirements.txt                   # 基础安装的 pip 清单
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

从基础运行到检索与记忆，按功能选择使用指南。每份文档说明组件用法与配置，配套程序见[示例索引](examples/README.md)。

### 基础设施

- **[安装与依赖管理](docs/installation.md)** - uv、pip 与版本锁定
- **[运行可靠性与验收](docs/reliability-guide.md)** - 模型关闭、共享预算与数据维护
- **[工具响应协议](docs/tool-response-protocol.md)** - ToolResponse 统一返回格式
- **[上下文工程](docs/context-engineering-guide.md)** - 历史管理、输入组装与预算
- **[组件组合](docs/component-composition-guide.md)** - AgentComponents 按需注入

### 核心能力

- **[可观测性](docs/observability-guide.md)** - TraceLogger 追踪系统
- **[熔断器](docs/circuit-breaker-guide.md)** - CircuitBreaker 容错机制
- **[会话持久化](docs/session-persistence-guide.md)** - 保存、中断与恢复

### 知识与记忆

- **[知识检索](docs/rag-guide.md)** - RAG、召回重排与关系证据
- **[检索评测与模型重排](docs/retrieval-evaluation-guide.md)** - Recall、MRR、nDCG 与候选排序
- **[向量与混合检索](docs/qdrant_retrieval.md)** - Qdrant、Embedding 与 RRF
- **[云端检索入门](docs/cloud-retrieval-guide.md)** - 注册一个账号，配置地址与密钥，运行 RAG 和记忆检索
- **[GraphRAG](docs/graphrag-guide.md)** - 实体关系、社区报告与局部/全局查询
- **[持久化记忆](docs/memory-guide.md)** - 偏好、事实、经历与做法的记录管理
- **[用户画像（Profile）](docs/profile-memory-guide.md)** - 结构化偏好、来源、并发修订与跨会话使用
- **[记忆语义检索](docs/semantic-memory-guide.md)** - 向量召回、修订同步与用户隔离

### 增强能力

- **[子代理机制](docs/subagent-guide.md)** - TaskTool 与 ToolFilter
- **[Skills 知识外化](docs/skills-usage-guide.md)** - 按需加载操作指导
- **[文件编辑](docs/file_tools.md)** - 乐观锁与批量编辑
- **[TodoWrite 进度管理](docs/todowrite-usage-guide.md)** - 任务进度追踪

### 辅助功能

- **[DevLog 决策日志](docs/devlog-guide.md)** - 开发决策记录
- **[异步生命周期](docs/async-agent-guide.md)** - 异步执行与回调
- **[后台任务](docs/background-jobs-guide.md)** - 持久队列、进度、重试与恢复

### 核心架构

- **[运行循环](docs/runtime-guide.md)** - 调用入口与结束状态
- **[流式输出](docs/streaming-sse-guide.md)** - 流式事件与 SSE
- **[Function Calling](docs/function-calling-architecture.md)** - 模型请求与工具执行
- **[LLM 消息格式](docs/llm-message-guide.md)** - 消息与工具调用格式
- **[日志系统](docs/logging-system-guide.md)** - 日志与运行轨迹

### 扩展能力

- **[MCP 工具](docs/mcp-guide.md)** - 工具发现、调用与连接管理
- **[工具权限](docs/tool-policy-guide.md)** - 宿主策略与执行边界
- **[自定义工具](docs/custom_tools_guide.md)** - 函数式、标准类与可展开工具

---

<div align="center">

**HelloAgents** - 让智能体开发变得简单而强大 🚀
</div>

