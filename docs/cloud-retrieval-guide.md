# 云端检索：注册、配置与运行

推荐初次使用选择 Qdrant Cloud。一个账号负责向量存储和文本嵌入，RAG 与记忆检索共用配置；无需 Docker、下载本地模型或注册另一家 Embeddings 服务。结构化用户画像仍可独立使用 SQLite，无需云服务。

## 📚 目录

- [注册与获取 API Key](#注册与获取-api-key)
- [安装与配置](#安装与配置)
- [在代码中使用](#在代码中使用)
- [模型变更与常见问题](#模型变更与常见问题)
- [第一次运行后检查什么](#第一次运行后检查什么)

## 注册与获取 API Key

1. 打开 [Qdrant Cloud](https://cloud.qdrant.io/)，使用邮箱、GitHub 或 Google 注册。
2. 在控制台创建免费集群（Create Free Cluster），选择名称与区域，等待集群就绪。
3. 复制集群详情里的 Endpoint / URL，以及创建集群时提供的集群 API Key。这里需要的是访问数据的集群密钥，不是管理账号资源的 Cloud Management Key。
4. 查看集群的 Inference 页，确认云端推理已开启，并可使用 `intfloat/multilingual-e5-small`。当前官方列出的该多语言模型为 384 维，免费层也可使用；实际可用模型及价格以控制台为准。

官方入口：[Cloud Quickstart](https://qdrant.tech/documentation/cloud-quickstart/) · [Cloud Inference](https://qdrant.tech/documentation/cloud/inference/)。

## 安装与配置

推荐 Python 3.13，也支持 3.12。在框架源码根目录选择一种安装方式：

```bash
# uv
uv sync --locked --extra qdrant
uv run --locked --extra qdrant python -m examples.retrieval.cloud_retrieval_demo
```

```bash
# 或 pip：先创建并激活虚拟环境
python -m pip install -r requirements/qdrant.txt
python -m examples.retrieval.cloud_retrieval_demo
```

首次运行前，在当前目录的 `.env` 填入两个值。示例会加载此文件，已经设置的系统环境变量优先：

```dotenv
QDRANT_URL=https://从控制台复制的集群地址
QDRANT_API_KEY=从控制台复制的集群密钥
```

案例使用虚构旅行规则和用户偏好，展示文档检索与记忆召回。运行时会将示例文本发送到云端编码，并在当前目录保存 SQLite 原始记录，在云端创建向量集合。它不调用聊天模型，因此不需要 `LLM_API_KEY`。接入 Agent 生成回答时，再按模型指南配置聊天服务。

## 在代码中使用

```python
import os
from dotenv import load_dotenv
from hello_agents.retrieval import RAGStore, QdrantSearch, QdrantCloudInference

load_dotenv()
store = RAGStore("workspace/documents.sqlite")
store.add_document("下雨时优先安排室内展览。", source="example:rain", document_id="rain")
with QdrantSearch(
    store, QdrantCloudInference(),
    url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"],
    collection="hello_agents_cloud",
) as search:
    search.sync()
    for hit in search.search("雨天怎么玩？"):
        print(hit.content, hit.source)
```

记忆检索沿用同样的配置，返回 `MemoryRecord`，保留用户作用域、来源和修订关系：

```python
from hello_agents.memory import MemoryStore, SemanticMemorySearch

memories = MemoryStore("workspace/memory.sqlite", user_id="alice", task_id="travel")
memories.add("每天步行不超过五公里。", source="user:message-1", kind="preference")
with SemanticMemorySearch(
    memories, QdrantCloudInference(),
    url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"],
    collection="hello_agents_cloud",
) as recall:
    recall.sync()
    print(recall.search("徒步有什么限制？"))
```

把仍处于打开状态的 `search` 传给 `RAGTool(store, search_backend=search)` 即可供 Agent 调用；记忆对应 `MemoryTool(memories, search_backend=recall)`。关闭上下文管理器后不再使用检索对象。画像用法见[用户画像指南](profile-memory-guide.md)。

## 模型变更与常见问题

嵌入模型可配置，不必改业务代码。案例读取下面三个可选变量；更换模型时同时核对维度并选择新集合：

```dotenv
QDRANT_EMBEDDING_MODEL=intfloat/multilingual-e5-small
QDRANT_EMBEDDING_DIMENSION=384
QDRANT_COLLECTION=hello_agents_cloud
```

直接调用 API 时使用 `QdrantCloudInference(model="控制台支持的模型", dimension=对应维度)`。它只描述托管推理，不会下载本地模型。原有 `FastEmbedProvider` 和 `OpenAIEmbeddingProvider` 仍可用于自行计算向量，见[向量与混合检索](qdrant_retrieval.md)。

- 无法连接：使用控制台原样提供的 HTTPS 地址，确认集群已就绪以及当前网络可访问；不要把管理控制台网址填成集群地址。
- 401 / 403：确认使用集群密钥并具有所需读写权限。
- 初始化会自动为作用域、代次等过滤字段建立索引，以满足云端的严格模式；密钥需要创建集合和字段索引的权限，已有字段索引会复用。
- 推理或模型不可用：检查 Inference 开关、模型名称和配额；普通自建 Qdrant 服务不自动具备托管推理能力。
- 维度或模型不一致：使用正确的模型/维度创建新集合，并重新 `sync()`。
- 资料或记忆变更后提示索引过期：重新 `sync()` 后再查询；撤回的记忆不会通过旧索引静默返回。

云端推理与存储的具体配额、收费及地区可用性由服务商决定。本组件不自动切换付费模型。

## 第一次运行后检查什么

先确认 SQLite 中有原始记录，再检查同步完成后的查询结果是否包含正文与 source。云端集合中的点是派生索引，完整来源和记忆修订仍由本地 Store 管理。把程序移动到另一台机器时，仅保留 Qdrant 集合不足以恢复原文与有效记录，需要一起迁移应用存储及对应配置。

文档和记忆可以共用连接配置，但由各组件保留自己的作用域和版本。更换用户或任务，应由宿主创建绑定正确范围的 Store，不能让模型通过参数任意选择用户。

运行结束后，关闭客户端不会删除云端集合。再次查询时沿用同一模型、集合和本地 Store；练习结束可在控制台清理自己创建的练习集合。不要删除其他应用共用的集合。
