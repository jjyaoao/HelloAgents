# 用户画像（Profile）使用指南

用户画像（Profile）保存需要反复使用的结构化信息，例如步行上限、饮食偏好和输出语言。`ProfileStore` 跨会话保存同一用户在同一应用中的资料；每次修订校验字段并保留来源与版本。整段旅行经历适合放入 `MemoryStore`，对话恢复使用 `SessionStore`。

## 📚 目录

- [快速开始](#快速开始)
- [接入 Agent](#接入-agent)
- [更新与遗忘](#更新与遗忘)
- [怎样设计画像字段](#怎样设计画像字段)
- [API 参考](#api-参考)
- [选择记忆方式](#选择记忆方式)
- [完整示例与验证](#完整示例与验证)
- [常见问题](#常见问题)

## 快速开始

从源码根目录安装即可使用，不需要 Qdrant 或嵌入模型：

```bash
python -m pip install -r requirements.txt
```

```python
from pydantic import Field
from hello_agents.memory import ProfileModel, ProfileStore

class TravelProfile(ProfileModel):
    walking_km: int = Field(ge=0, le=30)
    interests: list[str] = Field(default_factory=list)

store = ProfileStore(
    "workspace/profile.sqlite", user_id="alice", namespace="travel",
    schema=TravelProfile,
)
snapshot = store.get(include_inactive=True)
profile = store.put(
    {"walking_km": 8, "interests": ["历史文化", "自然风景"]},
    source="user:message-1",
    expected_revision=snapshot.revision if snapshot else 0,
)
corrected = store.patch(
    {"walking_km": 5}, source="user:message-2",
    expected_revision=profile.revision,
)
assert corrected.data["walking_km"] == 5
assert corrected.sources["interests"] == "user:message-1"
```

`ProfileModel` 使用 Pydantic 严格校验：字符串 `"5"` 不会自动变成整数，未知字段被拒绝。`user_id` 与 `namespace` 由宿主根据已认证身份确定，不能让模型参数选择用户。`namespace` 表示应用范围，例如 `travel`，不等同于一次会话的 ID。

## 接入 Agent

```python
from hello_agents import HelloAgentsLLM, SimpleAgent
from hello_agents.context import ContextBuilder
from hello_agents.memory import ProfileContextProvider

agent = SimpleAgent(
    "旅行助手", HelloAgentsLLM(),
    context_builder=ContextBuilder(),
    context_providers=[ProfileContextProvider(store)],
)
answer = agent.run("按我的步行要求安排两日行程")
```

Provider 在每次模型调用前重新读取有效 Profile。默认 `required=True` 将小型资料作为必须保留的上下文；超过组装预算会明确报错。`max_bytes` 默认 16 KiB，包含字段与来源，用来避免把长篇经历不断追加到 Profile 中。

资料进入上下文并不意味着模型一定遵守。影响实际操作的约束仍应由工具在执行前校验。Profile 中的文本是用户资料，不应该被提升为系统指令。

## 更新与遗忘

`put` 替换整个对象；`patch` 只替换传入的顶层字段，嵌套对象整体替换，不执行隐式深层合并。业务模型可以使用可空字段表达“未知”；省略字段或设为空值的含义应由 Schema 明确规定。

每次写入必须传 `expected_revision`。两个会话同时基于版本 1 更新时，只有一个成功，另一个收到 `ProfileConflict`。此时读取最新对象，重新判断如何合并；不要无条件重试旧写入。跨字段关系可以通过 Pydantic 模型校验器检查。

```python
current = store.get()
store.forget(source="user:forget-request", expected_revision=current.revision)
assert store.get() is None
audit = store.history(limit=10)
```

`forget` 让资料退出当前读取，保留审计快照和递增版本，防止旧请求重新覆盖。它不是物理删除：SQLite、备份、消息历史、模型服务日志应按应用的数据保留策略分别处理。重新创建已遗忘资料时，通过 `get(include_inactive=True)` 取得当前版本。

改变 Profile Schema 会触发明确错误，需要迁移数据或使用新的命名空间。框架不擅自把旧资料转换为新字段。

## 怎样设计画像字段

画像适合少量、稳定、会反复参与决策的信息。把步行上限保存为带单位的数值字段，比把一整段聊天塞进 `notes` 更容易校验与使用。日期、目的地等一次性行程要求放在任务状态中；长期饮食偏好和表达语言才适合应用级画像。

字段需要允许“未知”时，在 Pydantic Schema 中明确使用可空类型或默认值，并说明其业务含义。不要用 `0` 同时表示“没有限制”和“不能步行”。范围校验用于拒绝无效输入，不能替代对来源的判断。

### 从用户表达更新画像

应用先把用户表达整理为候选字段，展示或按可信来源确认后，读取当前 revision 并提交 `patch()`。如果另一个会话已经修改画像，收到 ProfileConflict 后应重新读取并合并；不能忽略版本重新执行旧请求。

更新后核对三个对象：存储中的 `data` 是否改变、未修改字段的 `sources` 是否保留、下一次 Provider 输出是否采用新版本。只看到数据库更新，不代表正在使用的静态消息也随之改变。

## API 参考

```python
ProfileStore(path, user_id=..., namespace=..., schema=TravelProfile, max_bytes=16384)
store.get(include_inactive=False)                       # ProfileSnapshot 或 None
store.put(data, source=..., expected_revision=...)       # 完整替换
store.patch(changes, source=..., expected_revision=...)  # 顶层字段修订
store.forget(source=..., expected_revision=...)          # 退出当前读取
store.history(limit=20)                                 # 历史快照，最新在前
ProfileContextProvider(store, required=True)
```

快照包含 `data`、逐字段的 `sources`、`revision`、`status`、`updated_at` 和所属用户及命名空间。首次写入使用 `expected_revision=0`，后续写入使用已读快照的版本。`ProfileConflict` 表示版本冲突，Pydantic 的 `ValidationError` 表示资料不符合业务字段约束。

画像通常通过 `ProfileContextProvider` 提供给模型，写入由宿主调用 Store。当前没有自动从所有聊天中提取画像的默认流程，也没有单独的 Profile 写入工具；需要模型辅助更新时，先生成候选字段，校验来源和版本后再写入。

## 选择记忆方式

- **用户画像**：`ProfileStore` 保存有类型、边界与来源的字段。适合每次都需要的少量偏好。
- **经历与事实集合**：`MemoryStore` 保存有来源的独立记录，可修订、撤回和按关键词查询。`preference/fact/episode/inference/procedure` 是类别，不是五套存储引擎。
- **会话状态**：`HistoryManager` 组织当前历史，`SessionStore` 保存并恢复对话。恢复对话不会自动提炼 Profile。
- **操作指导**：Skills 保存宿主维护的可加载说明。把一条记忆标为 `procedure` 不会自动修改系统提示或运行代码。

目前 Profile 更新由宿主显式执行。需要模型抽取时，可以先让模型输出符合业务 Schema 的候选，再核对用户原话、来源与当前版本后调用 Store。框架没有默认开启后台记忆抽取，也不会把模型推断直接确认为事实。大量资料的语义检索见 [Qdrant 检索](qdrant_retrieval.md)；离散记忆集合可组合 [SemanticMemorySearch](semantic-memory-guide.md)，`MemoryStore.search` 本身仍为关键词查询。

## 完整示例与验证

```bash
python -X utf8 -m examples.memory.profile_memory_demo
# 设置 LLM_MODEL_ID、LLM_API_KEY、LLM_BASE_URL 后：
python -X utf8 -m examples.memory.profile_memory_demo --live
python -m pytest tests/test_profile_memory.py
```

示例先保存 8 公里的上限，再修订为 5 公里，重新创建存储和 Agent，检查最新值能否进入回答，并确认另一用户读不到这份资料。离线模式使用预设模型响应；`--live` 使用实际模型服务。测试另外覆盖并发冲突、字段类型、来源保留、遗忘和 Schema 变化。

设计参考：[Profile 与 Collection](https://docs.langchain.com/oss/python/concepts/memory)、[可挂载记忆块](https://docs.letta.com/tutorials/attaching-detaching-blocks/)、[记忆修订](https://docs.mem0.ai/core-concepts/memory-operations/update)。

存储的导出、删除、版本迁移、备份与派生索引清理见[运行可靠性与验收](reliability-guide.md#数据维护)。

## 常见问题

**put 和 patch 怎样选择？**

首次确认整份画像或整体替换时用 put；只修订某些顶层字段时用 patch。两者都要带已读取的版本。patch 不递归合并嵌套对象，修改嵌套字段时应提交该对象完整的新值。

**结构化画像需要向量数据库吗？**

不需要。ProfileStore 按用户和应用范围直接读取对象。只有从大量离散记录中按含义搜索时，才需要考虑 SemanticMemorySearch。

**画像里有步行上限，路线工具就会自动受限吗？**

不会。Provider 为模型提供依据；路线工具或宿主还需校验实际里程是否满足要求。信息进入上下文与操作通过业务检查是两个环节。
