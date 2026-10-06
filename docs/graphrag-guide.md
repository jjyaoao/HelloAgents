# GraphRAG：从供应依赖到全局答案

某家旅行服务商的接驳和早餐同时受阻。停电公告、承运合同、供餐协议和备用方案分散在不同文档里。单次检索可能找到一个公告，却遗漏它影响的服务以及备用方案的限制。GraphRAG 先抽取有来源的实体与关系，用社区组织相关资料，再分别支持局部追查和全局综合。

## 📚 目录

- [安装与快速开始](#安装与快速开始)
- [索引怎样建立](#索引怎样建立)
- [局部检索与全局查询](#局部检索与全局查询)
- [版本、缓存与后台构建](#版本缓存与后台构建)
- [模型、预算与引用](#模型预算与引用)
- [运行供应链实验](#运行供应链实验)
- [如何读懂构图结果](#如何读懂构图结果)
- [常见问题](#常见问题)
- [API 与边界](#api-与边界)
- [参考资料](#参考资料)

## 安装与快速开始

在包含本组件的框架源码目录安装：

```bash
python -m pip install -r requirements/graphrag.txt
# 或使用 uv
uv sync --locked --extra graphrag
```

图结构使用 `igraph`，社区发现使用 `leidenalg`。实体、关系、来源和社区报告保存在 SQLite；抽取与答案生成沿用 HelloAgents 的模型接口，无需部署图数据库或安装其他 GraphRAG 框架。基础包导入不加载这两个可选依赖；没有安装时会给出明确提示。

当前实现不连接 Neo4j，无需配置 `NEO4J_*`。默认示例也不需要嵌入模型：局部查询先用实体名称、别名和词项匹配定位图节点，再扩展邻域。需要增强语义匹配时，可向 `GraphRAGIndex(..., embedding=embedding)` 注入 [OpenAIEmbeddingProvider 或 FastEmbedProvider](qdrant_retrieval.md)，并安装 `qdrant` 扩展；使用 FastEmbed 时安装 `fastembed` 扩展。

默认案例无需密钥。使用真实模型时，在仓库根目录的 `.env` 填写 `LLM_MODEL_ID`、`LLM_API_KEY` 和 `LLM_BASE_URL`，再运行：

```bash
python -m examples.retrieval.graphrag_demo --live
# uv 对应入口
uv run --locked --extra graphrag python -m examples.retrieval.graphrag_demo --live
```

示例会加载当前目录的 `.env`，已有系统环境变量优先。直接使用下面的 API 示例时，也应显式加载配置：

```python
from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM
from hello_agents.retrieval import (
    RAGStore, GraphRAGIndex, GraphConfig, HelloAgentsGraphModel,
)

load_dotenv(override=False)
store = RAGStore("data/documents.sqlite")
store.add_document(
    "运达客运为湖畔营地提供接驳；车辆依赖滨江充电站。",
    source="fixture://transport-contract", document_id="contract", version="1",
)
store.add_document(
    "滨江充电站停电，运达客运暂停湖畔营地接驳。",
    source="fixture://power-notice", document_id="notice", version="1",
)
model = HelloAgentsGraphModel(HelloAgentsLLM())
index = GraphRAGIndex(
    store, "data/graph.sqlite", model,
    config=GraphConfig(levels=2, max_input_tokens=12000, max_output_tokens=3000),
)
build = index.build()
print(build.to_dict())
for hit in index.local_search("滨江充电站停电会影响哪些服务？"):
    print(hit.content, hit.source, hit.version)
answer = index.global_search("资料中有哪些服务中断与依赖风险？")
print(answer.answer)
print(answer.coverage)
```

模型配置沿用 `LLM_MODEL_ID`、`LLM_API_KEY` 和 `LLM_BASE_URL`。上面的组织与事件都是演练材料。

## 索引怎样建立

`build()` 依次完成四步：

1. 模型从每个当前文档片段中抽取实体和有方向的关系。每条抽取结果必须带有该片段内逐字连续的引用；不存在的引用、未声明的关系端点会被拒绝。
2. 实体按规范化后的 `(kind, name, scope)` 合并。`kind` 使用人员、组织、地点、设施、服务、事件、物品与其他八种固定类别，避免把 `hotel` 与 `organization` 等不同粒度标签误当成不同实体。规范化只处理 Unicode 兼容形式、大小写和连续空白。别名用于查找，不直接触发实体合并；同一别名指向多个实体时保留全部候选，并记录 `ambiguous_aliases`。同名实体应提供不同 `scope`。
3. Leiden 对加权无向投影进行社区发现；原始关系仍保留方向。`levels` 控制层数，下一层在父社区内部重新划分，因此层级具有明确的父子关系。固定随机种子有利于同环境复现。
4. 模型为社区生成带证据引用的报告。社区过大时按预算拆成多个报告部分，全部保留。没有抽取到实体的片段进入单独的 `unassigned` 报告，避免被无声排除。

这些步骤实现了抽取、聚类、社区报告与查询的完整流程。它不同于只把人工三元组存进数据库的局部关系查询。`inspect()` 返回独立的可序列化索引快照，包括实体、关系、逐字证据、社区、报告和构建统计。

## 局部检索与全局查询

`local_context(query)` 先定位实体，再通过 `igraph` 展开邻域，返回实体、关系、相关社区报告与原文片段。准确命中实体别名时优先使用这些实体；否则使用词项匹配作为基础方案。`local_search()` 仅返回其中的 `RetrievalResult`，可直接作为 `RAGTool` 或 `RetrievalPipeline` 的 `SearchBackend`。

```python
from hello_agents.tools.builtin import RAGTool
tool = RAGTool(store, search_backend=index)
```

需要语义实体定位时，可以注入已有 `EmbeddingProvider`；框架复用 Qdrant 为实体建立向量索引：

```python
# 另安装 .[qdrant]；使用 FastEmbed 时安装 .[fastembed]。
index = GraphRAGIndex(store, "data/semantic-graph.sqlite", model, embedding=embedding)
index.build()
```

`global_search(query, level=0)` 则逐一读取指定层级的全部报告部分。Map 阶段产生带原始证据 ID 的局部答案；Reduce 阶段在预算内分批合并，直到得到最终答案。每次模型调用只能引用它实际收到的证据 ID，最终引用还会回到原文核对。这里不会用一个固定 top-k 报告集冒充全局覆盖。

返回的 `GraphAnswer` 包括：

- `answer`、`claims` 与 `citations`：正文、逐条论点、可回读的原文引用。
- `status`：`answered`、`answered_partial` 或 `no_answer`。
- `coverage`：报告总数、实际处理数、被报告引用的源片段数，以及没有进入报告引用的片段 ID。
- `diagnostics`：图代次、资料修订号、Map/Reduce 次数和归并轮数。

`coverage.complete` 只说明处理范围与来源覆盖完整，不证明模型读懂了所有条件或论点必然正确。报告未引用某些源片段时，返回明确的缺口；没有支持信息时返回 `no_answer`。

将两类查询直接暴露给 Agent：

```python
from hello_agents.tools.builtin.graphrag_tool import GraphRAGTool
registry.register_tool(GraphRAGTool(index))
# 注册 graphrag_local 与 graphrag_global；索引更新仍由宿主执行。
```

## 版本、缓存与后台构建

原文新增版本或撤下后，旧图立即被标记为不匹配；查询抛出 `IndexStaleError`，直到重新 `build()`。抽取缓存按模型配置及不可变源片段复用，社区报告按输入内容复用。失败或进程重启后，已经校验成功的阶段可以继续使用，不必重新支付全部模型调用费用。

新图在完整构建后通过 SQLite 事务发布。发布同时比较此前的活动代次，迟到的构建任务不能覆盖另一任务刚发布的图；冲突抛出 `GraphBuildConflict`。构建期间资料改变则拒绝发布，已完成缓存仍保留。

```python
def build_graph(payload, job_context):
    # checkpoint 检查取消请求和当前任务租约。
    result = index.build(checkpoint=job_context.checkpoint)
    return result.to_dict()
```

检查点位于模型调用前后、聚类与向量阶段边界及发布前。它支持协作式取消，不能中断已经进入同步 HTTP 请求的瞬间；网络超时仍由 LLM 配置控制。存储保留旧代次和引用记录用于审阅，未发布向量目录及历史代次的磁盘回收需由宿主管理。

## 模型、预算与引用

`HelloAgentsGraphModel` 使用已有的 `HelloAgentsLLM.invoke()`，不额外捆绑模型 SDK。默认最多尝试两次 JSON 生成，只重试 JSON/Schema 错误；截断、预算溢出与无效来源引用会明确失败。自定义模型适配器实现 `GraphModel.generate(stage, payload, max_input_tokens=..., max_output_tokens=...)`，并提供稳定的 `model_id`。修改模型、提示词或预处理方式时，应更新这个标识。

`max_input_tokens` 使用框架的本地 token 估算，并预留提示词与 Schema 空间；它不是服务商实际计费 tokenizer 的承诺。`max_output_tokens` 同时控制请求和本地输出检查。部分推理模型会共享推理与正文的输出预算，应增加预算，或通过 `HelloAgentsGraphModel(..., call_kwargs=...)` 显式配置服务支持的生成参数。

单条输入放不进预算、报告数量超过 `max_reports`、归并超过 `max_reduce_rounds` 时，组件都会报错，不裁掉一部分后继续宣称完成。可减小源片段、调整社区粒度或增加经过评估的预算。索引构建与全局查询均可能产生多次模型调用。

引用验证保证引用来自本次输入、指向正确版本、能逐字回读。它不等于自动证明“这段引用在语义上支持这个结论”。模型错误合并、遗漏或误解条件仍需业务评测与人工抽查；尤其不能把图中的关联自动解释为因果关系。

## 运行供应链实验

```bash
python -X utf8 -m examples.retrieval.graphrag_demo --workspace output/graph-fixture
python -X utf8 -m examples.retrieval.graphrag_demo --live --workspace output/graph-live
```

默认模式明确使用预设模型响应，实际运行 SQLite、Leiden、缓存、检索与引用校验。`--live` 使用配置的真实模型完成抽取、报告与 Map/Reduce。可通过 `--max-output-tokens` 调整输出预算，或用 `GRAPH_LLM_KWARGS` JSON 环境变量提供服务专用参数。

八份演练资料包含两条供应链：充电站—客运—营地，以及冷链仓库—餐饮—酒店。备用接驳有预约及人数限制，备用早餐无法保证无过敏原交叉接触。实验要求局部查询沿依赖找到影响，全局查询同时覆盖两条链及其限制。

输出保存在 `graphrag-report.json`：包含实际抽取规模、社区数、缓存复用、局部命中、全局答案、引用及覆盖诊断。还比较一次 BM25 top-3 与全局答案对六份标注资料的引用覆盖；两条路径的成本不同，这个小型实验不构成通用性能排名。替换成真实业务数据后，应标注需要的证据、依赖方向、例外条件及无答案问题，再评估召回、引用支持度、费用和延迟。

## 如何读懂构图结果

先运行预设响应案例，确认图索引、社区检测、查询和引用回读的接口能够工作，再切换真实模型。检查顺序应沿着数据处理过程：

1. **原始片段**：切分是否把条件与例外拆开；相同名称是否属于不同对象。
2. **实体和关系**：是否抽取了问题需要的依赖方向；引用原句是否确实支持关系。
3. **社区报告**：报告是否覆盖了本社区的重要限制，是否把不确定信息改成肯定结论。
4. **查询结果**：局部问题是否取得相邻证据，全局问题是否实际覆盖相关社区。

例如“充电站停运影响哪些设施”需要沿依赖查询；“两条供应链都有哪些风险”则需要综合不同社区。全局综合并不替代对某一条原始预约规则的精确回读。

## 常见问题

**什么时候不必使用 GraphRAG？**

单篇规则就能回答的问题，普通检索和来源回读通常更直接。图索引的价值在于组织跨资料关系和聚合主题，同时会增加抽取、构建及维护成本。

**正文已经更新，为什么查询仍然报索引过期？**

保存新原文不会自动重建派生图。重新 build 后，完整代次才会发布；构建中途失败仍应保留错误并恢复，不能绕过版本检查查询旧图。

**有引用，为什么答案仍可能错误？**

逐字引用校验验证“这句话来自这里”，但模型可能误解条件或关系方向。回读引文并核对结论仍是必要步骤。

## API 与边界

常用入口为 `build(checkpoint=None)`、`local_context(query, limit=5)`、`local_search(query, limit=5)`、`global_search(query, level=0, checkpoint=None)` 与 `inspect()`。`BuildReport` 和 `GraphAnswer` 均提供 `to_dict()`，可用于日志或后台任务结果。

当前实现面向中小型资料库，构建时把图快照读入内存；社区发现、模型抽取与报告生成也是有成本的离线工作。语义实体索引复用 Qdrant 本地模式，适合单进程宿主；大规模远程向量服务、多机索引调度及历史代次回收需要部署层进一步组织。这里没有声称实现 DRIFT、动态社区选择、全套知识本体推理或所有 GraphRAG 变体。

测试命令：

```bash
python -m pytest tests/test_graphrag.py -q
```

## 参考资料

- [Microsoft GraphRAG：索引工作流](https://microsoft.github.io/graphrag/index/overview/)
- [Microsoft GraphRAG：Local Search](https://microsoft.github.io/graphrag/query/local_search/)
- [Microsoft GraphRAG：Global Search](https://microsoft.github.io/graphrag/query/global_search/)
- [leidenalg：真实 Leiden 实现及参数](https://leidenalg.readthedocs.io/en/stable/reference.html)

存储的导出、删除、版本迁移、备份与派生索引清理见[运行可靠性与验收](reliability-guide.md#数据维护)。
