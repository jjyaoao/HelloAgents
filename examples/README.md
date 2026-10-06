# 功能示例

按[安装说明](../docs/installation.md)选择 uv 或 pip。下面使用已激活的虚拟环境，从仓库根目录安装并运行，代码与当前源码保持一致：

```bash
python -m pip install -r requirements.txt
python -X utf8 -m examples.agents.async_agent_demo
python -X utf8 -m examples.memory.profile_memory_demo
python -X utf8 -m examples.runtime.background_jobs_demo
```

默认案例不需要 API 密钥。涉及 Agent 的离线案例使用明确的预设模型响应，实际执行工具、存储和运行循环；它们用于观察协议和组件行为，不用于评估模型能力。文件操作案例使用临时目录；进度与决策日志案例把数据写入当前目录的 `memory/`。支持 `--workspace` 的案例可自行指定输出位置。

可选扩展独立安装，不增加基础 Agent 的默认依赖：

```bash
python -m pip install -r requirements/mcp.txt
python -X utf8 -m examples.tools.mcp_agent_demo
# 云端检索：在 .env 配置 QDRANT_URL 和 QDRANT_API_KEY，不下载嵌入模型
python -m pip install -r requirements/qdrant.txt
python -X utf8 -m examples.retrieval.cloud_retrieval_demo
# 独立嵌入 API：在 .env 配置 EMBEDDING_*，向量存储在本地
python -X utf8 -m examples.retrieval.qdrant_retrieval_demo --provider openai --workspace workspace/api-rag
# 本地嵌入模型路线：首次运行需要下载权重
python -m pip install -r requirements/fastembed.txt
python -X utf8 -m examples.retrieval.qdrant_retrieval_demo --help
python -X utf8 -m examples.memory.semantic_memory_demo --help
python -m pip install -r requirements/graphrag.txt
python -X utf8 -m examples.retrieval.graphrag_demo
```

Profile、MCP、GraphRAG 与记忆语义检索示例支持 `--live`。向量检索示例与评测参数见 [Qdrant 指南](../docs/qdrant_retrieval.md)。GraphRAG 默认预设模型抽取响应，但实际执行 Leiden 社区划分与检索；语义记忆实验始终使用实际嵌入模型。

嵌入服务按需选择：[Qdrant 云端嵌入](../docs/cloud-retrieval-guide.md)、[独立 Embedding API](../docs/qdrant_retrieval.md#使用云端-embedding-api)或 FastEmbed 本地模型。前两种无需下载模型；独立 API 不要求另开 Qdrant 云端账号。GraphRAG 默认无需 Neo4j 或嵌入服务，真实抽取与生成需配置聊天模型，见 [GraphRAG 指南](../docs/graphrag-guide.md)。

## 目录导航

```text
examples/
├── agents/          # Agent Loop、异步执行与子代理
├── tools/           # 工具调用、MCP、Skills 与进度管理
│   └── custom_tools/ # 自定义工具模板
├── context/         # 上下文与会话恢复
├── retrieval/       # 云端检索、向量检索与 GraphRAG
├── memory/          # 用户画像与语义记忆
├── runtime/         # 后台任务、可观测性与熔断
├── applications/    # 旅行助手综合案例
└── web/             # SSE 服务与网页客户端
```

从仓库根目录使用 `python -m examples.<分类>.<示例名>` 运行。根目录的 `_support.py` 为案例共用辅助代码。

## 按功能选择

- 工具：[`tools.tool_response_demo`](tools/tool_response_demo.py)、[`tools.file_tools_demo`](tools/file_tools_demo.py)、[`tools.custom_tools.complete_example`](tools/custom_tools/complete_example.py)。分别演示成功与错误回执、文件冲突，以及三种工具注册方式。
- 运行：[`agents.async_agent_demo`](agents/async_agent_demo.py)、[`agents.parallel_tools_demo`](agents/parallel_tools_demo.py)、[`agents.subagent_demo`](agents/subagent_demo.py)。观察异步回调、相同任务批次的并发峰值、只读子任务与结果回传。
- 上下文与会话：[`context.context_engineering_demo`](context/context_engineering_demo.py)、[`context.session_persistence_demo`](context/session_persistence_demo.py)、[`agents.runtime_features`](agents/runtime_features.py)。查看输入预算、整轮压缩、长输出回读、会话恢复和取消后的工具回执。
- 检索与记忆：[`applications.travel_assistant`](applications/travel_assistant.py)。通过旅行约束修订、检索来源回读和会话恢复，组合 SQLite 存储与上下文组件。
- 用户画像：[`memory.profile_memory_demo`](memory/profile_memory_demo.py)。保存结构化偏好、修订步行上限，在新 Agent 中读取最新资料并验证用户隔离，见[用户画像指南](../docs/profile-memory-guide.md)。基础安装即可运行，添加 `--live` 使用真实模型。
- 图检索：[`retrieval.graphrag_demo`](retrieval/graphrag_demo.py)。跨文档抽取关系、生成社区报告，比较局部证据与全局综合。
- 语义记忆：[`memory.semantic_memory_demo`](memory/semantic_memory_demo.py)。真实嵌入、偏好修订、索引同步与工具调用，见[功能指南](../docs/semantic-memory-guide.md)。
- 后台任务：[`runtime.background_jobs_demo`](runtime/background_jobs_demo.py)。导入失败后重试，从持久化进度继续，见[恢复指南](../docs/background-jobs-guide.md)。
- 操作指导与进度：[`tools.skills_demo`](tools/skills_demo.py)、[`tools.todowrite_demo`](tools/todowrite_demo.py)、[`tools.devlog_demo`](tools/devlog_demo.py)。实际加载技能、写入进度与决策日志。另有 [`tools.todowrite_real_world`](tools/todowrite_real_world.py)，只演示项目进度维护，不执行软件开发。
- 可观测性与容错：[`runtime.observability_demo`](runtime/observability_demo.py)、[`runtime.circuit_breaker_demo`](runtime/circuit_breaker_demo.py)。核对实际运行轨迹和熔断状态。
- 自定义工具模板：[`simple_tool_template`](tools/custom_tools/simple_tool_template.py)、[`advanced_tool_template`](tools/custom_tools/advanced_tool_template.py)、[`expandable_tool_template`](tools/custom_tools/expandable_tool_template.py)。另有 [`weather_tool`](tools/custom_tools/weather_tool.py) 和 [`code_formatter_tool`](tools/custom_tools/code_formatter_tool.py)。天气数据为固定教学样本。

以上名称均可加在 `python -X utf8 -m examples.` 后运行，例如：

```bash
python -X utf8 -m examples.tools.custom_tools.complete_example
python -X utf8 -m examples.runtime.observability_demo --workspace workspace/traces
python -X utf8 -m examples.agents.runtime_features --workspace workspace/runtime
python -X utf8 -m examples.applications.travel_assistant --mode local --workspace workspace/travel
```

## 接入真实模型

在环境变量或仓库根目录的 `.env` 中配置服务，不在代码中填写密钥：

```dotenv
LLM_MODEL_ID=服务商提供的模型名称
LLM_API_KEY=你的密钥
LLM_BASE_URL=服务商提供的接口地址
```

`async_agent_demo`、`session_persistence_demo`、`subagent_demo`、`observability_demo`、`skills_demo`、`todowrite_demo`、`devlog_demo`，以及自定义工具中的 `complete_example`、`simple_tool_template`、`weather_tool` 支持 `--live`：

```bash
python -X utf8 -m examples.agents.async_agent_demo --live
```

旅行助手使用 `--mode live`，其余机制实验保持离线，以便控制实验变量。真实模型可能选择不同调用顺序；检查工具回执和 `agent.last_run`，不要只看最终回答。模型服务需支持工具调用；适配器配置见 [LLM 消息指南](../docs/llm-message-guide.md)。

## SSE 网页

```bash
python -m pip install -r requirements/web.txt
python -X utf8 -m examples.web.fastapi_sse_server
```

打开 <http://127.0.0.1:8000>，或另开终端执行 `python -X utf8 -m examples.web.test_sse_client`。每个 HTTP 请求独立创建 Agent。默认使用预设响应；配置模型并设置 `HELLOAGENTS_DEMO_LIVE=1` 后启动服务即可使用真实模型。

## 验证

```bash
python -m pip install -r requirements/test.txt -r requirements/web.txt
python -m pytest tests/test_current_examples.py tests/test_runtime_features_example.py
```

测试在独立目录逐个运行离线案例，并检查 SSE、工具校验和持久化行为。完整本地回归可执行 `python -m pytest`；配置模型后，使用 `python -m pytest --run-live -m live` 显式运行真实服务测试。更多功能说明见 [文档资源](../README.md#-文档资源)。
