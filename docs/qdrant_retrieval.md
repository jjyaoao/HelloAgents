# 向量与混合检索

初次使用推荐[云端检索入门](cloud-retrieval-guide.md)：注册 Qdrant Cloud 后配置集群地址与 API Key，使用托管多语言嵌入模型，无需下载权重。下面介绍自行选择嵌入模型、本地索引和混合召回的完整接口。

`RAGStore` 保存文档原文和不可变版本，`QdrantSearch` 提供真实向量召回，`HybridSearch` 融合关键词与向量排名。三者都实现 `search(query, limit)`，可以接入同一个 `RAGTool`，并继续按 `chunk_id` 回读原文。

## 📚 目录

- [安装与选择模型](#安装与选择模型)
- [使用云端 Embedding API](#使用云端-embedding-api)
- [最小用法](#最小用法)
- [本地模型与远程 Qdrant](#本地模型与远程-qdrant)
- [更新、撤下与来源一致性](#更新撤下与来源一致性)
- [排名融合与重排](#排名融合与重排)
- [运行可核对的实验](#运行可核对的实验)

## 安装与选择模型

```bash
python -m pip install -r requirements/qdrant.txt
# 使用本地 ONNX 嵌入模型时额外安装：
python -m pip install -r requirements/fastembed.txt
```

嵌入模型独立于对话模型。对话服务支持 Function Calling，并不意味着它也提供 Embeddings 接口。可以选择 OpenAI 兼容嵌入服务，或通过 FastEmbed 在本地编码；框架不自动选择模型，也不在导入包时下载权重。

## 使用云端 Embedding API

这种方式由独立服务计算向量，示例将向量保存在 Qdrant 本地目录；无需部署 Qdrant 服务，也无需填写 `QDRANT_URL` 或 `QDRANT_API_KEY`。`--provider openai` 指 OpenAI 兼容接口协议，不限于 OpenAI 官方服务。

在所选嵌入服务商的控制台注册、开通 Embeddings 服务并获取 API 密钥，再从其 API 文档确认接口地址、模型名称和输出维度。聊天模型的名称或密钥不能保证适用于嵌入服务。

将仓库根目录的 `.env.example` 复制为 `.env`，取消下面四项前面的 `#`，并填写实际值：

```dotenv
EMBEDDING_API_KEY=你的嵌入服务密钥
EMBEDDING_BASE_URL=服务商提供的兼容接口根地址
EMBEDDING_MODEL=服务商提供的嵌入模型名称
EMBEDDING_DIMENSION=服务商文档标明的向量维度
```

`EMBEDDING_DIMENSION` 必须替换为整数。`EMBEDDING_BASE_URL` 填 SDK 使用的接口根地址，不填写控制台网址，也不要自行追加 `/embeddings`。

从仓库根目录选择一种方式运行：

```bash
# uv
uv sync --locked --extra qdrant
uv run --locked --extra qdrant python -m examples.retrieval.qdrant_retrieval_demo --provider openai --workspace workspace/api-rag
```

```bash
# 或 pip：使用已激活的虚拟环境
python -m pip install -r requirements/qdrant.txt
python -m examples.retrieval.qdrant_retrieval_demo --provider openai --workspace workspace/api-rag
```

示例读取当前目录的 `.env`；系统环境变量优先，`--model` 和 `--dimension` 可覆盖对应环境变量。运行会将示例文本发送给嵌入服务，结果写入 `workspace/api-rag/retrieval-report.json`；无需配置聊天模型。此路线不安装或下载 FastEmbed 模型。若希望向量存储和嵌入都在云端完成，使用[云端检索入门](cloud-retrieval-guide.md)的另一组配置与示例。

## 最小用法

```python
import os
from dotenv import load_dotenv
from openai import OpenAI
from hello_agents.retrieval import (
    RAGStore, OpenAIEmbeddingProvider, QdrantSearch, HybridSearch,
)
from hello_agents.tools.builtin import RAGTool

load_dotenv(override=False)
store = RAGStore("data/documents.db")
store.add_document(
    "供应商取消活动时全额退款；游客自行取消需遵守退改期限。",
    source="policy://travel/refunds", document_id="refunds", version="1",
)

with OpenAI(
    api_key=os.environ["EMBEDDING_API_KEY"],
    base_url=os.environ["EMBEDDING_BASE_URL"],
) as client:
    embedding = OpenAIEmbeddingProvider(
        client, model=os.environ["EMBEDDING_MODEL"],
        dimension=int(os.environ["EMBEDDING_DIMENSION"]),
    )
    with QdrantSearch(store, embedding, path="data/vectors") as dense:
        dense.sync()
        hybrid = HybridSearch([store, dense], candidate_limit=20)
        for result in hybrid.search("商家不办活动了，我能拿回全部钱吗？", 3):
            print(result.content, result.source, result.version)
        tool = RAGTool(store, search_backend=hybrid)
        # 在这个 with 块内将 tool 注册给 Agent 并执行任务。
```

`dimension` 用于验证服务返回的向量维度。部分服务支持缩减维度；只有显式设置 `request_dimensions=True` 时，适配器才发送 `dimensions` 参数。返回条目会按输入索引恢复次序，数量、维度、非有限数值和零向量都会被检查。

## 本地模型与远程 Qdrant

本地模型使用相同接口：

```python
from hello_agents.retrieval import FastEmbedProvider

embedding = FastEmbedProvider(
    model_name=os.environ["EMBEDDING_MODEL"],
    dimension=int(os.environ["EMBEDDING_DIMENSION"]),
    cache_dir="data/model-cache",
)
```

第一次编码可能下载模型。已部署模型的离线环境可设置 `local_files_only=True`。文档和查询分别经过 FastEmbed 的 `passage_embed` 与 `query_embed`，以保留模型需要的前缀处理。

将 `path` 换成 `url` 即可连接 Qdrant 服务：

```python
with QdrantSearch(
    store, embedding, url=os.environ["QDRANT_URL"],
    api_key=os.getenv("QDRANT_API_KEY"), collection="travel_knowledge",
) as dense:
    dense.sync()
    results = dense.search("雨天有什么室内备选？")
```

也可以注入已配置的 `qdrant_client.QdrantClient`：`QdrantSearch(store, embedding, client=client)`。注入的客户端由宿主关闭；通过 `path` 或 `url` 创建的客户端由 `QdrantSearch` 关闭。`path=":memory:"` 使用真实 Qdrant 本地内存模式，适合测试。

## 更新、撤下与来源一致性

原文新增版本或撤下后，需要重新 `sync()`。未同步时抛出 `IndexStaleError`，不会悄悄返回过期片段。

```python
store.add_document(
    "新的退改规则……", "policy://travel/refunds",
    document_id="refunds", version="2",
)
dense.sync()
store.deactivate_document("refunds")
dense.sync()
```

同步先把当前资料写入新的向量代次，再切换清单，最后回收上一代。向量上传中途失败时，新代次不会参与检索。搜索返回前会回读 SQLite 原文、核对当前版本；向量 payload 不作为事实来源。历史片段仍可通过 `read_chunk` 审计回读，撤下操作不等于物理删除。

每份 SQLite 资料库有持久化 namespace，同一 Qdrant 集合中的不同资料库相互隔离。namespace 是索引隔离机制，不能替代应用的身份认证与授权。更换嵌入模型、维度或预处理规则时，应创建新集合；模型身份不一致会被拒绝。自定义适配器必须为不同配置提供不同 `model_id`。

`sync()` 是显式的全量代次构建，资料未变化时直接跳过。它按批编码，但会读取全部当前片段；适合中小型知识库。大规模增量索引、分布式写入协调、服务端租户授权和访问审计由部署系统负责。同一资料库应由一个同步任务写入。传输中断可能留下未发布代次，需要运维回收；这些代次不会被查询。

## 排名融合与重排

BM25 分数与余弦相似度不在同一尺度，不能直接相加。`HybridSearch` 使用 RRF：一路内排名从 1 开始，每条候选的得分为各路 `1 / (rrf_k + rank)` 之和，`rrf_k` 默认 60。这个参数属于本组件，与 Qdrant 服务端的默认值不同。

`candidate_limit` 决定每路召回多少条。没有被任何一路召回的片段，融合无法找回。要增加交叉编码器等重排器，可将混合后端交给现有 `RetrievalPipeline`；重排器必须保留候选的内容、来源与标识。此实现的关键词一路来自 SQLite BM25，向量一路来自 Qdrant，并非 Qdrant 原生 sparse/dense 服务端融合。

Agentic RAG 可以直接把 `RAGTool(store, search_backend=hybrid)` 注册给 Agent，让模型决定何时搜索、如何改写问题和回读原文。固定检索、Agentic RAG 和关系图遍历是不同组织方式；向量数据库本身不会自动完成这些决策，也不等同于完整 GraphRAG。

## 运行可核对的实验

```bash
python -m examples.retrieval.qdrant_retrieval_demo --model YOUR_EMBEDDING_MODEL --dimension MODEL_DIMENSION --workspace output/travel-rag
```

选择兼容 API 服务时加 `--provider openai`，并配置前述 `EMBEDDING_*` 环境变量；默认使用 FastEmbed。先根据 [FastEmbed 模型列表](https://qdrant.github.io/fastembed/examples/Supported_Models/) 选择支持中文的模型及对应维度。

实验使用八条明确标注为虚构的旅行服务规则，以及六个改写后的问题，比较 BM25、向量、混合三种召回的 Recall@1 与 MRR@3。报告保留每个问题的期望文档及实际排序，并验证规则变更后旧索引被拒绝、新版本能够回读。这是可运行的小型诊断实验，不能据此声称在所有业务数据上某种方案更好。上线前应替换为真实业务的标注问题，并检查拒答、版本变化、无答案问题和来源覆盖率。

协议测试使用真实 Qdrant 本地引擎与确定性向量替身，验证隔离、重启、维度、失败发布及版本一致性；这些测试不衡量嵌入模型的语义质量：

```bash
python -m pytest tests/test_qdrant_retrieval.py -q
```

## 参考资料

- [Qdrant Python Client：本地模式与远程接口](https://github.com/qdrant/qdrant-client)
- [Qdrant：混合检索与 RRF](https://qdrant.tech/documentation/search/hybrid-queries/)
- [FastEmbed 与 Qdrant](https://qdrant.tech/documentation/fastembed/fastembed-semantic-search/)
