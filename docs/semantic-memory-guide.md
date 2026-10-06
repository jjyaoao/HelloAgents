# 记忆语义检索指南

希望省去本地模型安装，可先按[云端检索入门](cloud-retrieval-guide.md)配置一个账号，并向 `SemanticMemorySearch` 传入 `QdrantCloudInference()`；下面介绍完整的同步、修订和召回机制。

用户说“膝盖恢复期间每天最多走五公里”，后续却问“安排活动时，徒步强度需要注意什么”。`SemanticMemorySearch` 使用嵌入模型召回含义相关的记录，可与关键词结果融合；记忆本身仍由 `MemoryStore` 保存，修订与撤回的语义保持一致。

## 📚 目录

- [快速开始](#快速开始)
- [使用云端嵌入服务](#使用云端嵌入服务)
- [修订与同步](#修订与同步)
- [接入工具与上下文](#接入工具与上下文)
- [真实模型实验](#真实模型实验)
- [一次更新需要检查两份状态](#一次更新需要检查两份状态)
- [API 与边界](#api-与边界)

## 快速开始

本地模型使用可选的 FastEmbed 与 Qdrant；也可以传入 [OpenAIEmbeddingProvider](qdrant_retrieval.md) 调用兼容的 Embeddings 服务。

```bash
python -m pip install -r requirements/fastembed.txt
```

```python
import os
from dotenv import load_dotenv
from hello_agents.memory import MemoryStore, SemanticMemorySearch
from hello_agents.retrieval import FastEmbedProvider

load_dotenv(override=False)
store = MemoryStore("workspace/memory.sqlite", user_id="alice", task_id="travel")
record = store.add("每天步行最多五公里。", source="user:preference")
embedding = FastEmbedProvider(os.environ["EMBEDDING_MODEL"],
                              int(os.environ["EMBEDDING_DIMENSION"]))
with SemanticMemorySearch(store, embedding, path="workspace/vectors") as recall:
    recall.sync()
    print([item.content for item in recall.search("徒步强度怎么安排？", limit=3)])
```

首次运行 FastEmbed 可能下载权重；模型名称及维度应从所选模型的说明确认。模型、维度或预处理变化时换用新的向量集合。对话模型与嵌入模型独立配置，不要求由同一家服务提供。

默认 `hybrid=True`，将关键词与向量召回用 RRF 融合。`hybrid=False` 只用向量召回。两种模式都返回原始 `MemoryRecord`，保留类型、来源、用户任务范围以及修订关系。

## 使用云端嵌入服务

不下载本地模型时，有两种选择：使用 [Qdrant 云端嵌入](cloud-retrieval-guide.md)，或使用独立的 OpenAI 兼容嵌入 API。后者安装 `requirements/qdrant.txt`（uv 使用 `--extra qdrant`），按[嵌入 API 配置步骤](qdrant_retrieval.md#使用云端-embedding-api)填写 `.env` 的四个 `EMBEDDING_*` 变量，然后运行下面的完整代码：

```python
import os
from dotenv import load_dotenv
from openai import OpenAI
from hello_agents.memory import MemoryStore, SemanticMemorySearch
from hello_agents.retrieval import OpenAIEmbeddingProvider

load_dotenv(override=False)
store = MemoryStore("workspace/api-memory.sqlite", user_id="alice", task_id="travel")
store.add("每天步行最多五公里。", source="user:preference", kind="preference")
with OpenAI(
    api_key=os.environ["EMBEDDING_API_KEY"],
    base_url=os.environ["EMBEDDING_BASE_URL"],
) as client:
    embedding = OpenAIEmbeddingProvider(
        client, model=os.environ["EMBEDDING_MODEL"],
        dimension=int(os.environ["EMBEDDING_DIMENSION"]),
    )
    with SemanticMemorySearch(store, embedding, path="workspace/api-memory-vectors") as recall:
        recall.sync()
        print([record.content for record in recall.search("徒步强度怎么安排？", limit=3)])
```

这里的向量计算使用云端 API，向量索引与原始记忆保存在本地，不需要 Qdrant 云端密钥或聊天模型配置。仅创建 `OpenAIEmbeddingProvider` 不会自动加载 `.env`，所以自行编写程序时需要保留 `load_dotenv()`。

下文的 `semantic_memory_demo` 命令演示 FastEmbed 本地模型；若选择云端路线，使用本节代码或 `examples.retrieval.cloud_retrieval_demo`。

## 修订与同步

每个用户与任务范围拥有独立 namespace 和修订号。`add`、`revise`、`retract` 改变当前有效记录后，已有索引立即变为过期状态；语义查询抛 `IndexStaleError`，直到宿主重新 `sync()`。不会静默退回旧偏好。其他用户或任务的修改不会使当前索引失效。

```python
from hello_agents.retrieval import IndexStaleError

# recall 在 with 块内保持打开
updated = store.revise(record.memory_id, "每天步行最多三公里。", "user:correction")
try:
    recall.search("徒步强度")
except IndexStaleError:
    recall.sync()
results = recall.search("徒步强度")
assert all(item.memory_id != record.memory_id for item in results)
```

同步先写入新向量代次，再发布清单。无变化时返回 `0`，不重新编码；记忆变化时重新编码该范围的有效记录。中途失败不会发布半成品。返回结果前再次读取规范存储并检查修订号，避免已撤回内容被向量命中重新带回。

空查询采用当前最新记录，不经过向量索引。它适合已知要读取最近记忆的场景；不是相似度查询。撤回保留审计历史，不能代替物理删除、备份清理和日志管理。

## 接入工具与上下文

同一个后端可用于模型自行查询，也可由宿主在每次调用前取回：

```python
from hello_agents import ToolRegistry
from hello_agents.tools.builtin import MemoryTool
from hello_agents.context import MemoryContextProvider

registry = ToolRegistry()
registry.register_tool(MemoryTool(store, search_backend=recall))
provider = MemoryContextProvider(store, search_backend=recall,
                                 use_query=True, limit=5)
```

模型的 `memory_search` 参数不包含用户身份，身份由宿主创建 Store 时绑定。写入后应由宿主同步索引或安排后台任务；模型不能通过变更工具参数跨范围查询。提供给调用者的自定义 `search_backend` 也必须绑定相同范围。

结构化资料使用 [ProfileStore](profile-memory-guide.md)，可用字段校验、来源和并发修订；离散事件、偏好与做法使用 MemoryStore。语义检索解决“找回哪些记录”，并不自动验证事实、合并冲突或把推断提升为确认信息。

## 真实模型实验

```bash
python -X utf8 -m examples.memory.semantic_memory_demo --model EMBEDDING_MODEL --dimension DIMENSION --workspace workspace/memory-demo
```

将命令中的 `EMBEDDING_MODEL` 和 `DIMENSION` 替换为选定模型及其维度。可添加 `--cache-dir` 和 `--local-files-only` 复用本地权重。这个案例没有预设向量：使用真实嵌入，依次验证语义召回、八公里修订为五公里、拒绝过期索引、后台重新同步、另一用户隔离和撤回后排除。

配置 `LLM_MODEL_ID`、`LLM_API_KEY`、`LLM_BASE_URL` 后添加 `--live`，会让真实 Agent Loop 使用 Function Calling 查询记忆，并检查回答中的当前步行上限。宿主策略只允许 `memory_search`，不允许模型改写实验记录。

结果保存在 `semantic-memory-report.json`。该案例是小型机制诊断，固定问题的成功不等于通用检索质量；实际业务应加入未命中问题、相近但冲突的偏好和较长的事件集合再评估。

## 一次更新需要检查两份状态

MemoryStore 是有效记忆的依据，向量索引用于加速召回。可以先保存修订，再安排后台同步；在两者版本尚未一致时，明确返回索引过期，让宿主选择等待同步或主动使用关键词检索。后者需要宿主显式选择，不能让语义接口悄悄返回另一算法的结果。

常见流程为：保存用户修订 → 提交同步任务 → 等待任务成功 → 再次召回。JobQueue 的成功只表示处理函数完成，应让处理函数返回实际同步结果；查询仍需经过 SemanticMemorySearch 的版本检查。

### 排查“找不到记忆”

先用同一用户、同一 task_id 的 MemoryStore 读取当前有效记录。如果这里没有结果，检查身份范围、撤回和修订；如果记录存在，再检查 sync 是否完成、嵌入模型是否一致以及查询是否足够明确。关键词和向量命中都正确后，再检查 Provider 是否因为预算排除了候选。

### 调整召回量

`candidate_limit` 控制用于融合的候选数量，`limit` 控制最终返回的记录数。召回更多记录会增加模型输入和无关内容，不能只为避免漏检无限放大。先用业务任务检查是否漏掉关键偏好，再逐步调整并回看实际消息。

## API 与边界

```python
SemanticMemorySearch(store, embedding, hybrid=True, candidate_limit=20,
                     path=None, url=None, client=None, collection="hello_agents")
recall.sync(batch_size=64, checkpoint=None)  # 返回实际编码数
recall.search(query="", limit=10)           # 当前有效 MemoryRecord
recall.close()
```

`path/url/client` 必须三选一；额外 Qdrant 选项见 [向量指南](qdrant_retrieval.md)。注入 client 的生命周期由宿主管理，否则 `close()` 或 `with` 关闭内部 client。查询 limit 不得大于 `candidate_limit`。同步可传 [JobContext.checkpoint](background-jobs-guide.md)，用于阶段间检测取消和执行权。

同一索引应由一个写入者同步。Qdrant 本地路径不能跨进程同时打开；需要远程检索时配置 Qdrant 服务。当前没有自动记忆抽取、语义去重、重要度衰减、TTL 或图记忆；这些策略可以围绕 Store 与检索接口独立实现，不能由向量相似度代替事实判断。

存储的导出、删除、版本迁移、备份与派生索引清理见[运行可靠性与验收](reliability-guide.md#数据维护)。
