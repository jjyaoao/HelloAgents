# 持久化记忆与 MemoryTool 指南

用户修改偏好后，旧值需要退出当前检索，但仍可追溯；重新启动后，系统还应记得最新状态。MemoryStore 提供这一维护过程，SessionStore 则保存完整会话。两者可以组合，职责不同。

## 📚 目录

- [快速开始](#快速开始)
- [核心概念](#核心概念)
- [在一次任务中完成记忆维护](#在一次任务中完成记忆维护)
- [API 参考](#api-参考)
- [工具与上下文组合](#工具与上下文组合)
- [完整示例](#完整示例)
- [常见问题](#常见问题)

## 快速开始

在源码根目录安装框架，无需额外数据库或模型服务：

```bash
python -m pip install -r requirements.txt
```

```python
from hello_agents.memory import MemoryStore

store = MemoryStore("workspace/memory.sqlite", user_id="alice", task_id="hangzhou")
record = store.add("每天步行不超过八公里", source="user:message-1", kind="preference")
updated = store.revise(record.memory_id, "每天步行不超过五公里", source="user:message-2")

# 可在新进程重新创建这个实例；数据位于 SQLite 文件中。
reopened = MemoryStore("workspace/memory.sqlite", user_id="alice", task_id="hangzhou")
print(reopened.search("步行")[0].content)
print(reopened.get(record.memory_id, include_inactive=True).status)  # superseded
reopened.retract(updated.memory_id)
assert reopened.search("步行") == []
```

修改偏好后，旧值仍可审计，但不会作为有效记忆重新召回。记忆保存的是带来源的陈述，不能仅因入库就当成已经核实的事实。

前例先输出“五公里”和 `superseded`，撤回后查询为空。重点是有效状态变化与重启读回；这里没有模型抽取、语义相似度或答案质量评测。默认文件会保留审计记录，重复运行会新增记录，学习时可选择独立工作目录。

## 核心概念

`MemoryStore` 是持久化组件，`MemoryTool` 是模型调用适配器，`MemoryContextProvider` 是上下文读取适配器。它们各自可用，不要求创建 Agent，也不会自动解析整段会话并写入“事实”。

宿主创建 Store 时绑定 `user_id` 与 `task_id`。读取、修订、撤回都在该范围内执行；工具参数没有身份字段。不同用户或任务即使知道另一个记录的标识，也不能通过这个实例读取或修改它。身份的真实性仍由宿主认证负责，SQLite 文件本身也需要相应文件权限。

`kind` 区分 `preference`（偏好）、`fact`（事实陈述）、`episode`（事件）、`inference`（推断）和 `procedure`（做法）。这些是记录类别，不代表不同的神经记忆机制或存储算法。默认检索使用中英关键词重叠；它不是向量语义检索。

### 修订与撤回

`revise` 在同一事务中把旧记录标为 `superseded`，再写入新记录并用 `supersedes` 指向旧记录。再次修订旧版本会失败，避免并发调用覆盖刚更新的偏好。`retract` 将当前记录标为 `retracted`，重复撤回是幂等的。

已返回的 Python 对象、生成的回答、消息历史和静态 `ContextPacket` 不会自动消失。要让下一次调用使用新状态，采用每次重新查询的 `MemoryContextProvider`。历史对话中引用过的旧内容仍需由应用按保留策略管理；撤回不是从所有日志中彻底删除。

## 在一次任务中完成记忆维护

以步行偏好为例，宿主先把用户明确表达的“每天最多八公里”保存为一条有来源的记录。用户后来更正为五公里，应修订原记录，而不是简单新增第二条互相矛盾的偏好。查询只返回当前有效值，旧值保留在修订链中。

```text
确认信息 → add → 有效记录
用户更正 → revise → 新记录有效，旧记录 superseded
用户撤回 → retract → 当前检索排除
下一次调用 → Provider 重新读取 → 当前资料进入消息
```

### 什么时候写入

区分用户确认和模型推断。用户明确提出的要求可保存为偏好；模型根据活动推测的兴趣应保留 `inference` 类型和来源，不能伪装成用户确认。是否长期保留、是否需要用户确认，应由应用的写入策略决定。

不要把每轮模型输出直接 `add()`。这会重复记录过时结论，并把临时计划混入长期偏好。先选出后续任务确实要复用的信息，再确定记录范围和类型。

### 什么时候读取

小量、每轮都需要的约束，可通过 Provider 放入当前上下文；较大的经历集合，由 MemoryTool 按任务查询。初次接入时先直接调用 `store.search()` 核对内容，再检查 Provider 生成的 ContextPacket，最后观察 Agent 实际收到的消息。

`task_id` 决定记录共享范围。同一个用户换了任务标识，实例就不会自动读出另一个任务的记录。需要稳定跨旅行使用的结构化偏好时，可采用 ProfileStore 的应用 namespace；不要靠省略身份校验实现跨任务共享。

## API 参考

```python
MemoryStore(path, user_id, task_id)
store.add(content, source, kind="preference")        # MemoryRecord
store.search(query="", limit=10)                    # list[MemoryRecord]
store.get(memory_id, include_inactive=False)          # MemoryRecord
store.revise(memory_id, content, source)              # 新 MemoryRecord
store.retract(memory_id)                             # 撤回后的 MemoryRecord
```

空查询读取当前范围最新的有效记录；非空查询按关键词重叠排序。`limit` 为 1–100。无效输入抛 `ValueError`，不存在、越范围或默认读取失效记录抛 `KeyError`。所有 SQLite 连接在操作结束后关闭。

`MemoryRecord` 包括 `memory_id`、`user_id`、`task_id`、`content`、`source`、`kind`、`status`、`created_at`、`updated_at` 和 `supersedes`。`to_dict()` 用于检查记录；有效记录的 `to_context_packet(required=False)` 提供共享上下文契约。撤回或被替代的记录不能直接转成包。

时间字段是写入/更新时间，当前没有单独的业务有效期、TTL 自动清理或历史时点查询。`source` 由调用方声明；框架不会自动验证引用所支持的结论。

## 工具与上下文组合

```python
from hello_agents import ToolRegistry
from hello_agents.tools.builtin import MemoryTool

registry = ToolRegistry()
registry.register_tool(MemoryTool(store))
response = registry.execute_tool("memory_search", {"query": "步行"})
print(response.to_dict())
```

默认展开为 `memory_add`、`memory_search`、`memory_revise`、`memory_retract`。方法参数与 Store 对应，响应统一为 `ToolResponse`；无效参数为 `INVALID_PARAM`，当前范围内找不到记录为 `NOT_FOUND`。不展开时注册 `auto_expand=False`，通过 `memory` 的 `action` 参数选择 `add/search/revise/retract`。

让宿主选择哪些记忆进入输入：

```python
from hello_agents.context import ContextBuilder, MemoryContextProvider

provider = MemoryContextProvider(store, limit=5, required=True)
packets = provider.get_context("规划杭州旅行")
result = ContextBuilder().build_messages(
    [{"role": "user", "content": "规划杭州旅行"}], additional_packets=packets,
)
print(result.messages)
```

`required=True` 适合宿主确认必须保留的约束；全部必需内容超过预算时明确报错。默认 `required=False` 的候选仍接受相关性筛选。默认 Provider 读取最近记录，`use_query=True` 改为用当前任务检索。更细的类型、时效和常驻偏好策略可以由自定义 Provider 实现。

是否允许模型写入、是否需要用户确认，由应用在注册工具和调度前决定。`ToolFilter` 只是可见性筛选，不等同于身份认证、批准流程或执行沙箱。`MemoryTool` 不内置虚假的“自动安全授权”。

## 完整示例

```bash
python -X utf8 -m examples.applications.travel_assistant
python -X utf8 -m examples.applications.travel_assistant --mode resume
```

示例在同一任务中修订步行偏好，并启动新进程验证持久化；另一个用户查询为空。`--workspace` 可指定独立目录。模型集成显式使用 `--mode live`，配置方式见[RAG 指南](rag-guide.md#完整示例)。

`python -X utf8 -m examples.agents.runtime_features --workspace workspace/runtime-demo` 进一步把当前偏好注入 Agent 输入并保存/恢复会话。其 `result.json` 中旧记录为 `superseded`，演示撤回后的当前记录为 `retracted`，另一用户结果数为 `0`。记忆撤回不删除此前会话里已经出现的文字，应用仍需管理历史保留策略。

## 常见问题

**与 SessionStore 有何区别？**

SessionStore 保存会话配置和历史，MemoryStore 保存有范围、类型、来源和生命周期的记录。前者适合恢复对话，后者决定哪些长期信息当前仍可采用。

**是否会自动抽取、去重或总结记忆？**

不会。宿主或模型工具调用明确决定写入。向量与混合召回由可选的 `SemanticMemorySearch` 提供；它不自动去重、验证事实或构造图记忆。两个相似的 `add` 会形成两条记录，应当使用已有标识进行 `revise`。

**为什么使用 SQLite？**

它让作用范围、版本替代和事务边界可检查，且不增加学习者部署负担。多机服务、大规模搜索与复杂访问控制需要独立后端，Store 的公开操作和 Provider/Tool 适配仍可以保留。

**撤回是否等于彻底删除个人信息？**

不是。它是可审计的逻辑失效。真正的数据删除还涉及数据库、备份、历史与日志，应由应用实现完整的保留和删除策略。

存储的导出、删除、版本迁移、备份与派生索引清理见[运行可靠性与验收](reliability-guide.md#数据维护)。
