# 检索组件与 RAG 工具指南

当回答依赖外部资料时，先检索候选，再回读原文核对条件。这里分别处理“找资料”和“让模型回答”，使漏检、版本错误和生成错误可以分开检查。

## 📚 目录

- [快速开始](#快速开始)
- [核心概念](#核心概念)
- [API 参考](#api-参考)
- [Agent 与上下文集成](#agent-与上下文集成)
- [替换召回与重排](#替换召回与重排)
- [有来源的局部关系检索](#有来源的局部关系检索)
- [把自己的资料接入进来](#把自己的资料接入进来)
- [完整示例](#完整示例)
- [常见问题](#常见问题)

## 快速开始

在源码根目录安装框架：

```bash
python -m pip install -r requirements.txt
```

基础检索只使用 SQLite 和框架已有依赖，不下载嵌入模型，不需要 API 密钥。

```python
from hello_agents.retrieval import RAGStore

store = RAGStore("workspace/knowledge.sqlite")
store.add_document(
    "示例博物馆平日无需预约，节假日须提前预约。",  # 教学虚构材料
    source="fixture://museum/notice", version="1", document_id="museum",
)
hits = store.search("博物馆节假日预约", limit=3)
for hit in hits:
    print(hit.content, hit.source, hit.version, hit.chunk_id)
    print(store.read_chunk(hit.chunk_id).content)
```

这里得到的是候选证据，并没有生成回答。检查片段中的适用条件，再将证据交给模型，才构成检索增强生成。

这个例子应检索到包含“节假日须提前预约”的片段，来源为 `fixture://museum/notice`、版本为 `1`，回读正文与命中正文一致。没有命中时先检查导入内容与查询词，不要把空结果解释成“不需要预约”。

## 核心概念

`RAGStore` 保存完整原文与片段。每个片段包含文档标识、来源、版本和 `[start, end)` 字符区间；它满足 `原文[start:end] == 片段正文`。偏移是 Python Unicode 字符索引，不是 UTF-8 字节位置。导入时不归一化空白。

关键词检索使用 BM25。英文和数字按词切分，连续汉字生成单字与相邻双字，因此中文不需要先插入空格。这是可观察的词项匹配，不是语义向量检索：同义词、复杂指代和无字面重叠的问题可能漏检。

片段按字符长度与重叠切分。预约要求与例外可能被切开，因此检索结果保留来源和回读标识。`read_chunk` 回读命中片段；`read_document(hit.document_id, hit.version)` 回读同一版本的完整原文。全文也要经过输入预算检查，大文档可以由宿主提供分节回读器。

### 版本规则

- 同一 `document_id` 导入新 `version` 后，搜索只使用新导入版本；版本字符串不按大小排序。
- 旧片段仍可通过 `chunk_id` 回读，返回值明确标注旧版本，适合核对历史证据。
- 同标识同版本同原文重复导入是幂等的，不重新激活旧版本；同版本改变原文或来源会报错。
- 分块参数只在首次导入该版本时生效。重新切分请提供新版本，不覆盖已有片段标识。

## API 参考

### RAGStore

```python
RAGStore(path)
store.add_document(text, source, version="1", document_id=None,
                   chunk_size=600, overlap=80)  # 返回 document_id
store.search(query, limit=5)                  # list[RetrievalResult]
store.read_chunk(chunk_id)                    # RetrievalResult
store.read_document(document_id, version=None) # DocumentResult
```

`chunk_size` 必须大于零，且 `0 <= overlap < chunk_size`；`limit` 为 1–100。空查询或无效参数抛出 `ValueError`，找不到片段抛出 `KeyError`。默认文档标识来自来源字符串的 SHA-256。每次数据库操作结束时关闭连接，不需要额外调用 `close()`，同一路径可在另一个进程重新打开。

`RetrievalResult` 包含 `chunk_id`、`document_id`、`source`、`version`、`content`、`start`、`end` 和 `score`。BM25 分数仅用于同一查询内排序，不是事实可信度。`to_dict()` 便于保存记录，`to_context_packet()` 用于上下文组合。

`DocumentResult` 包含 `document_id`、`source`、`version`、`content` 和 `active`，同样提供 `to_dict()` 与 `to_context_packet()`。省略版本读取当前原文；指定版本不会自动跳到新版。旧原文保留且 `active=False`，便于解释历史结果，不能当作当前规定使用。

### RAGTool

```python
from hello_agents import ToolRegistry
from hello_agents.tools.builtin import RAGTool

registry = ToolRegistry()
registry.register_tool(RAGTool(store))
response = registry.execute_tool("rag_search", {"query": "节假日预约", "limit": 3})
print(response.to_dict())
```

工具沿用 `Tool.run(dict) -> ToolResponse` 与 `ToolParameter`，默认按 `@tool_action` 展开为 `rag_search(query, limit=5)`、`rag_read(chunk_id)` 和 `rag_read_document(document_id, version)`。`ToolResponse.data` 保存完整来源。Agent 向模型返回结构化数据时序列化响应，而不只取 `text`。全文回读工具要求显式版本，避免检索与回读之间更新后读到不同内容。

也可 `register_tool(RAGTool(store), auto_expand=False)`，此时调用 `rag`，使用 `action="search"`、`"read"` 或 `"read_document"` 及对应参数。文档导入不作为模型工具暴露。

## Agent 与上下文集成

固定检索用 Provider；由模型决定何时检索及是否补查时，将 `RAGTool` 注册进现有 Agent Loop。无需创建第二个循环。

```python
from hello_agents.context import ContextBuilder, RetrievalContextProvider

provider = RetrievalContextProvider(store, limit=3)
builder = ContextBuilder()
result = builder.build_messages(
    [{"role": "user", "content": "节假日参观需要预约吗？"}],
    additional_packets=provider.get_context("节假日预约"),
)
print(result.messages)
print(result.diagnostics)
```

资料进入 `user` 参考消息，来源字段一起进入模型输入。它们不会被提升为系统指令。`SimpleAgent` 的具体注入和每轮刷新方式见[上下文指南](context-engineering-guide.md#组件组合与资料注入)。

真实向量与混合召回可直接使用 [QdrantSearch 与 HybridSearch](qdrant_retrieval.md)，通过独立 EmbeddingProvider 选择向量模型。

## 替换召回与重排

`SearchBackend` 只要求 `search(query, limit) -> list[RetrievalResult]`。`RetrievalContextProvider` 可以直接接收自定义后端；需要把召回与原文存储分开时，将后端注入 `RAGTool`：

```python
from hello_agents.retrieval import RetrievalPipeline
from hello_agents.tools import RAGTool

# 不传 reranker 时保持后端原始次序；这里仍然是 BM25，没有隐含向量模型。
pipeline = RetrievalPipeline(store, candidate_limit=20)
tool = RAGTool(store, search_backend=pipeline)
hits = pipeline.search("博物馆预约", limit=3)
```

`RetrievalPipeline(backend, reranker=None, candidate_limit=20)` 先召回至多 `candidate_limit` 项，再可选调用 `reranker.rerank(query, candidates)`。返回上限 `limit` 不能大于候选上限。重排器必须返回原候选的完整排列，不能增删候选或改写内容、来源和召回分数；管线会验证这一点。独立重排分数由重排器自行保留诊断，不冒充原召回分数。

宿主可接入真实向量索引和交叉编码器，输出同一 `RetrievalResult` 契约。框架没有默认下载这些模型。外部后端返回的 `chunk_id` 应当能由关联原文存储回读；来源授权、索引版本同步和删除传播仍由宿主负责。

## 有来源的局部关系检索

关系把分散的线索连接起来，原始来源仍用于核对适用条件。下面的例子只导入一条经人工整理的关系：

```python
from hello_agents.retrieval import RelationStore
from hello_agents.tools import RelationTool

store.add_document("示例文化馆位于东站。", "fixture://transport", document_id="transport")
evidence = next(hit for hit in store.search("示例文化馆东站")
                if hit.document_id == "transport")
relations = RelationStore(store)
relations.add("示例文化馆", "位于", "东站", evidence.chunk_id, "示例文化馆位于东站。")
for edge in relations.neighbors("示例文化馆", hops=1, direction="out"):
    print(edge.subject, edge.predicate, edge.object, edge.evidence.source)
registry.register_tool(RelationTool(relations))
```

`RelationStore(documents)` 与 `RAGStore` 共用 SQLite 文件，重启后可恢复。`add(subject, predicate, object, chunk_id, quote)` 返回关系标识，重复导入幂等。`quote` 必须是指定片段中的连续原文；这验证出处存在，不证明三元组语义正确，抽取结果仍需校验。

`neighbors(entity, hops=1, limit=20, direction="both")` 使用精确实体标识作有界广度优先遍历。`hops` 范围为 1–3，`limit` 为 1–100，方向为 `out`、`in` 或 `both`。返回 `RelationResult`，含三元组、引用原句、完整 `RetrievalResult` 与发现深度。返回边集不等于一条已证实的因果路径。`to_context_packet()` 保留来源与版本。

关系检索只采用当前原文版本的边。导入新文档版本后，旧边立即退出遍历；系统不会自动猜测新边，需要重新导入。旧片段仍可明确按 ID 回读。`RelationTool` 暴露 `relation_lookup(entity, hops, limit, direction)`，只读，不授予模型写图能力。

这是局部关系证据组件。需要实体关系自动抽取、Leiden 社区检测、分层报告与全局综合时，使用独立的 [GraphRAGIndex](graphrag-guide.md)。关系图本身不包含用户权限系统；多租户资料需要宿主隔离存储或在检索后端落实授权。

## 把自己的资料接入进来

先选择一小份有明确来源、版本和适用范围的资料，例如预约规则。为它分配稳定的 `document_id`；规则更新时继续使用同一标识导入新版本，这样当前检索才能排除旧内容。不同地区或不同场馆的同名文件应使用不同标识。

直接调用 `store.search()` 后，不只看有没有命中，还应回读命中位置附近的完整条件。例如片段写着“可以退款”，相邻段落可能限定“预约前一天”。确认切分与来源回读合理，再接上模型回答。

### 选择固定检索或工具检索

问题都要查询同一资料库时，用 RetrievalContextProvider 在调用前提供候选，路径更容易控制。需要先查预约、再根据结果补查交通时，给模型 RAGTool，让它在循环中决定下一条查询。这两种方式可以组合：固定注入当前任务约束，工具补查外部证据。

第一次接入不必同时开启向量、重排和图检索。先确认资料能稳定入库、搜索并回读，然后针对实际缺口增加能力：同义表达难命中时增加向量召回，候选排序不理想时尝试重排，问题依赖多份材料间的连接时使用关系或图检索。

## 完整示例

```bash
python -X utf8 -m examples.applications.travel_assistant
python -X utf8 -m examples.applications.travel_assistant --mode resume
```

默认流程实际导入 SQLite、切换资料版本、检索并回读、保存和修订偏好、输出上下文预览，再启动新进程读回。材料是虚构教学资料；没有调用模型，也没有伪造模型轨迹。

若要继续观察完整工具请求、上下文、会话恢复与结束状态，运行 `python -X utf8 -m examples.agents.runtime_features --workspace workspace/runtime-demo`。该例用明确的离线响应替身驱动真实 Agent Loop，适合检查接口；真实模型的检索决策应使用下面的 Live 入口单独验证。

配置 `.env` 的 `LLM_MODEL_ID`、`LLM_API_KEY`、`LLM_BASE_URL` 后，可显式运行：

```bash
python -X utf8 -m examples.applications.travel_assistant --mode live
```

选择支持原生工具调用的模型。Live 模式需要真实服务，不保证每次查询顺序相同。离线机制测试不代表真实模型的检索决策或回答质量，需要另行核对来源与任务结果。

## 常见问题

**这是向量 RAG 或完整 GraphRAG 吗？**

默认检索为本地 BM25。向量与混合召回通过 [QdrantSearch](qdrant_retrieval.md) 组合；图构建、社区报告及局部/全局查询使用 [GraphRAGIndex](graphrag-guide.md)。这些可选组件显式启用，不会在失败后悄悄切换算法。神经重排模型仍由调用者通过重排契约提供。

**适合多大的资料库？**

当前每次查询扫描全部有效片段，并在 Python 中计算 BM25，适合小型资料库和机制学习。大规模应用应替换为索引后端并增加权限过滤，不能把此实现当作生产级检索服务。

**来源字段可以证明内容真实吗？**

不能。它提供回读与核对入口，不验证网页可信度或有效日期。导入、访问权限与资料更新由宿主负责。

**怎样运行测试？**

```bash
python -m pytest tests/test_retrieval_memory.py tests/test_retrieval_composition.py tests/test_context_pipeline.py
```

这些测试使用真实 SQLite，模型调用部分使用明确标注的捕获替身，不连接外部服务。
