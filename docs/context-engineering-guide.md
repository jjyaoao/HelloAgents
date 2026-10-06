# 上下文工程指南（Context Engineering）

## 📚 目录

- [组件组合与资料注入](#组件组合与资料注入)
- [历史管理与摘要](#历史管理与摘要)
- [工具输出与本地计数](#工具输出与本地计数)
- [前缀布局与缓存](#前缀布局与缓存)
- [配置与使用边界](#配置与使用边界)
- [常见问题](#常见问题)

上下文工程决定模型本次接收哪些信息。当资料、偏好和历史逐渐增长时，先检查实际消息，再判断遗漏是召回、筛选还是预算造成的。当前框架分别提供候选收集与组装、历史管理、工具输出截断和本地 token 估算。

## 组件组合与资料注入

在源码根目录运行 `python -m pip install -r requirements.txt`。检索和记忆的独立用法见 [RAG 指南](rag-guide.md)与[记忆指南](memory-guide.md)。

### 先检查一次实际输入

```python
from hello_agents.context import ContextBuilder, ContextConfig, ContextPacket

builder = ContextBuilder(ContextConfig(max_tokens=2000))
result = builder.build_messages(
    messages=[
        {"role": "system", "content": "依据可核对的资料回答，不编造缺失信息。"},
        {"role": "user", "content": "安排杭州旅行"},
    ],
    additional_packets=[ContextPacket(
        content="每天步行不超过五公里",
        metadata={"type": "related_memory", "id": "preference-1",
                  "source": "user:message-1", "required": True},
    )],
    tool_schemas=[],
)
print(result.messages)
print(result.diagnostics)
```

资料与记忆进入当前任务之前的 `user` 参考消息，保留来源、版本和标识，不提升为系统指令。基础消息原样保留，因此已有的 `assistant.tool_calls` 和 `tool.tool_call_id` 不被拆开。框架内部的 `summary` 在 SimpleAgent 中转换为注明“历史摘要”的合法 `user` 消息。

中文相关性使用汉字单字与相邻双字匹配，不依赖空格。非必需候选按相关性与可选 MMR 多样性排序；超过预算时整包排除，不截断资料尾部。宿主可以给明确约束设置 `required=True`，使其不受词项相关性过滤。

诊断包含 `selected`、`excluded` 及排除原因、`base_tokens`、`tool_schema_tokens`、`estimated_tokens`、`budget` 和输出余量。计数使用本地编码与消息开销估算，不是模型服务端精确 token 用量；以服务返回的 usage 核对实际消耗。

运行前例后，先在 `result.messages` 找到五公里约束和原来的任务，再看 `selected` 中的来源 `user:message-1`。`estimated_tokens` 应不超过 `budget`；数字变化不等于答案质量变化。完整可执行组装例子为 `python -X utf8 -m examples.agents.runtime_features --workspace workspace/runtime-demo`：工具调用前后都组装输入，恢复会话后再次刷新记忆候选，捕获替身可检查每次实际请求。

若基础消息、工具定义或必需资料超过预算，抛出 `ContextBudgetExceeded`，其 `diagnostics` 保留检查信息。该路径不静默删除任务和系统指令，不自动调用模型摘要。先减少非必要历史或工具集合、执行显式压缩，或增大配置预算后重试。

### 接入 SimpleAgent 的真实消息路径

```python
from hello_agents import SimpleAgent, HelloAgentsLLM, Config, ToolRegistry
from hello_agents.context import ContextBuilder, ContextConfig, MemoryContextProvider
from hello_agents.memory import MemoryStore
from hello_agents.retrieval import RAGStore
from hello_agents.tools.builtin import RAGTool

memory = MemoryStore("workspace/memory.sqlite", user_id="alice", task_id="hangzhou")
rag = RAGStore("workspace/knowledge.sqlite")
registry = ToolRegistry()
registry.register_tool(RAGTool(rag))
agent = SimpleAgent(
    "旅行助手", HelloAgentsLLM(), tool_registry=registry,
    config=Config(skills_enabled=False, subagent_enabled=False,
                  todowrite_enabled=False, devlog_enabled=False),
    context_builder=ContextBuilder(ContextConfig(max_tokens=8000)),
    context_providers=[MemoryContextProvider(memory, required=True)],
)
# 需要真实模型配置；见 README 的 LLM_MODEL_ID / LLM_API_KEY / LLM_BASE_URL。
# print(agent.run("查阅资料，规划杭州两日行程"))
```

`ContextProvider.get_context(query)` 在每次模型调用前执行；工具循环中的第二次调用也重新查询，因而记忆修订和撤回能反映到下一次参考资料中。固定检索可另外注入 `RetrievalContextProvider(rag)`；模型自主补查则使用上例的 RAGTool。

也可以调用 `agent.run(query, context_packets=[...])` 传入一次性快照；生成器会在本次 run 开始时收集一次。快照不会随数据库自动更新。没有配置 `context_builder` 却传入非空包时会报错，不会静默忽略。

### 不继承具体存储，也能替换收集策略

```python
from hello_agents.context import ContextPacket

class TravelConstraints:
    def get_context(self, query):
        return [ContextPacket(
            "本次总预算不超过1500元",
            metadata={"id": "budget", "source": "application:confirmed",
                      "required": True},
        )]

# 作为 context_providers=[TravelConstraints()] 注入即可。
# 不要求继承 MemoryStore、RAGStore 或 ContextBuilder。
```

当前分工是 Store 管持久化与查询、Tool 适配工具协议、Provider 收集当前候选、Assembler 组织模型消息、Agent Loop 调度模型与工具。`ContextAssembler` 只要求 `build_messages(messages, additional_packets, tool_schemas) -> ContextBuildResult`；替换检索后端或选择策略无需重写 Loop。共享数据类型位于 `hello_agents.context.types`。

### 组合方式与支持范围

- `SimpleAgent.run`、`arun`、`stream_run` 和 `arun_stream` 共享运行器和每次模型调用前的消息组装，四种入口均执行 Function Calling 循环。不要对同一 Agent 并发运行任务。
- 流式输出可能包含工具调用前的中间文本，最终结果读取完成事件。提前关闭流使用 `aclosing`，见[运行指南](runtime-guide.md)。
- 未配置 Builder/Provider 时使用对话历史与当前任务直接构建输入。`last_context_diagnostics` 表示最近一次成功组装。
- 其他 Agent 可复用 RAGTool、MemoryTool 和统一的同步/异步 ToolRegistry。显式 Provider/Assembler 注入目前仅接入 SimpleAgent，不能将这些参数直接用于其他 Agent。
- 使用 `ContextBuilder.build_messages()` 保持消息角色，并检查返回的预算诊断。历史压缩由 HistoryManager 负责；消息组装不会自动生成摘要。
- 使用 `AgentComponents` 替换历史、计数、截断、会话和 Skills，详见[组件组合指南](component-composition-guide.md)。TraceLogger 及各 Agent 专有组件仍保留原生命周期。
- Prompt 资料分区不是执行沙箱，也不能保证模型绝不受资料中的恶意指令影响；授权与外部执行隔离是不同层的职责。

---

## 历史管理与摘要

`HistoryManager` 管理追加、轮次边界、摘要替换和序列化。追加消息通常不改动此前内容，但 `compress` 会把较早历史替换成摘要，不能把整个生命周期描述成只追加。

### 独立使用

```python
from hello_agents import Message
from hello_agents.context import HistoryManager

manager = HistoryManager(min_retain_rounds=1)
manager.append(Message("预算1500元", "user"))
manager.append(Message("已记录预算", "assistant"))
manager.append(Message("每天步行不超过五公里", "user"))
manager.append(Message("优先安排短线", "assistant"))

# 摘要由调用方提供；此例不调用模型。
manager.compress("已确认总预算1500元；还需核对预约条件。")
for message in manager.get_history():
    print(message.role, message.content)

saved = manager.to_dict()
restored = HistoryManager(min_retain_rounds=1)
restored.load_from_dict(saved)
```

只有历史轮数超过 `min_retain_rounds` 才执行替换。`HistoryManager` 本身不会根据 token 阈值自动压缩，也没有 `should_compress` 或 `get_messages` 方法。自动触发由 Agent 基类在添加消息后检查本地估计值负责。

### Agent 自动压缩

```python
from hello_agents import Config

config = Config(
    context_window=8000,
    compression_threshold=0.8,
    min_retain_rounds=4,
    enable_smart_compression=False,
)
```

窗口大小应按所选模型实际能力配置。这份 Config 管 Agent 历史，和 `ContextConfig` 的本次消息预算是两个不同控制入口，设置时应协调。

默认简单摘要只统计轮数和消息数量，不会保留任务目标、约束、决策或证据；它减少输入，但可能破坏长任务的可继续性。需要保留的状态应显式写入记忆或生成经过检查的摘要，不能把统计摘要当作高质量记忆。

启用 `enable_smart_compression=True` 会额外调用摘要模型；默认沿用主模型，也可通过 `AgentComponents(summary_llm=...)` 注入完整模型实例；`summary_max_tokens` 和 `summary_temperature` 控制摘要调用。当前实现将较早消息文本截到每条前500个字符后请求摘要，失败时退回统计摘要。摘要可能遗漏或改变关键条件，应核对实际结果；不保证压缩后仍保留全部任务信息。

## 工具输出与本地计数

### ObservationTruncator

```python
from hello_agents.context import ObservationTruncator

truncator = ObservationTruncator(
    max_lines=20, max_bytes=4096,
    truncate_direction="head", output_dir="workspace/tool-output",
)
result = truncator.truncate("sample_log", "\n".join(f"line {i}" for i in range(100)))
print(result["preview"])
if result["truncated"]:
    print(result["full_output_path"])
    print(result["stats"])
```

`head`、`tail`、`head_tail` 分别保留开头、结尾或两端。截断保留的是位置，不保证保留关键证据；需要检查完整输出时使用返回的保存路径。返回预览的结构化 JSON 也可能不再完整，不能继续当作原始 JSON 直接解析。

四类 Agent 的共同工具执行路径都会应用注入的截断器。结果过长时，以 `partial` 回执返回预览和完整输出路径，模型可据此决定是否继续回读。ContextBuilder 还会检查组装后的基础消息预算；单个工具已截断并不保证整个会话一定未超预算。

### TokenCounter

```python
from hello_agents import Message
from hello_agents.context import TokenCounter

counter = TokenCounter(model="gpt-4")  # 用于选择本地编码；不创建模型客户端
messages = [Message("杭州旅行预算1500元", "user")]
print(counter.count_messages(messages))
print(counter.get_cache_stats())
```

本地编码、消息包装开销和降级字符估算可能与服务端不同。该计数适合预算预警；实际消耗、缓存命中和费用以服务返回的 usage 与计费规则为准。新增 ContextBuilder 还估算工具 schema 与参考资料的序列化开销，不用正文字符数冒充完整输入量。

## 前缀布局与缓存

将稳定指令和稳定工具定义放在输入前部，动态任务和结果放在后面，有利于满足某些服务的相同前缀复用条件。是否命中仍受模型、接口、前缀长度、序列化方式和服务缓存策略影响；只追加消息不保证缓存命中。

历史压缩或参考资料更新可能改变前缀。应比较同一任务下的实际输入、服务返回的缓存 token、延迟与回答质量。框架没有实现推理引擎的 KV 缓存，也不承诺固定比例的提速或费用下降。

## 配置与使用边界

```python
from hello_agents import Config

config = Config(
    context_window=8000,
    compression_threshold=0.8,
    min_retain_rounds=4,
    enable_smart_compression=False,
    tool_output_max_lines=2000,
    tool_output_max_bytes=51200,
    tool_output_dir="workspace/tool-output",
    tool_output_truncate_direction="head",
)
```

保留多少轮、何时压缩和工具输出保留哪一部分，需要根据任务证据分布调整。较多历史不一定更相关，较短摘要也不一定更可靠。先通过 `ContextBuildResult.diagnostics` 和实际模型消息检查发生了什么，再调参数。

## 常见问题

**设置 `compression_threshold=1.0` 会禁用自动压缩吗？**

不会。它表示本地历史估算超过配置窗口的100%时才触发检查，可能已经太晚。当前 Config 没有独立的禁用自动压缩开关；不要将扩大阈值宣传为无限上下文方案。

**为什么短对话没有产生摘要？**

自动压缩同时受 token 阈值和保留轮数条件影响。增加20条很短的消息通常不会接近默认窗口；只有改变轮数并不能保证触发。

**记忆撤回后，历史里还可能出现旧内容吗？**

可能。Provider 的下一次读取排除失效记录，但旧回答、工具结果或静态包不会自动擦除。应用需要区分当前有效记忆与历史陈述，涉及删除请求时还要处理日志和备份。

**如何验证模型实际看到了哪些资料？**

本地可直接检查 `ContextBuildResult.messages`，集成测试可捕获 LLM 接口输入。本仓库 `tests/test_context_pipeline.py` 使用明确标注的模型替身核对同步、异步和流式路径、来源、工具关联及预算；这些检查不等于远程模型回答质量评估。

## 🔗 相关文档

- [RAG 检索组件](rag-guide.md)
- [持久化记忆](memory-guide.md)
- [会话持久化](session-persistence-guide.md)
- [工具响应协议](tool-response-protocol.md)
- [可观测性](observability-guide.md)
