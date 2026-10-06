# Agent 组件组合指南

需要替换历史存储、接入已有会话目录，或只禁用某一项默认组件时，使用 `AgentComponents` 明确指定依赖。这样可以单独验证组件行为，不必修改模型与工具的执行循环。

## 📚 目录

- [快速开始](#快速开始)
- [默认装配与显式覆盖](#默认装配与显式覆盖)
- [组件契约](#组件契约)
- [历史、摘要与计数的一致性](#历史摘要与计数的一致性)
- [替换存储与 Skills](#替换存储与-skills)
- [生命周期与支持范围](#生命周期与支持范围)
- [常见问题](#常见问题)
- [从默认 Agent 逐步替换组件](#从默认-agent-逐步替换组件)

## 快速开始

在源码根目录安装框架：

```bash
python -m pip install -r requirements.txt
```

先准备几个可以独立使用的组件，不需要模型密钥：

```python
from hello_agents import AgentComponents, Message
from hello_agents.context import HistoryManager
from hello_agents.core.session_store import SessionStore

history = HistoryManager(min_retain_rounds=4)
history.append(Message("本次旅行预算1500元", "user"))
session = SessionStore(session_dir="workspace/travel-sessions")
components = AgentComponents(
    history_manager=history,
    session_store=session,
    skill_loader=None,
)
```

在源码根目录将它们传给 Agent。这里使用示例中的预设响应替身，不需要模型密钥：

```python
from hello_agents import Config, SimpleAgent
from examples.agents.runtime_features import ScriptedLLM, response

llm = ScriptedLLM([response("离线协议已读取此前预算")])
agent = SimpleAgent(
    "旅行助手", llm,
    config=Config(trace_enabled=False, subagent_enabled=False,
                  todowrite_enabled=False, devlog_enabled=False),
    components=components,
)
assert agent.history_manager is history
assert agent.session_store is session
assert agent.skill_loader is None
agent.run("在此前预算下继续规划行程")
assert any("1500" in m.get("content", "") for m in llm.requests[0]["messages"])
saved_path = agent.save_session("component-example")
print(saved_path)
```

预载历史会参与实际消息构建和本地预算计数，传入的对象不会被复制或重新配置。四种 Agent（Simple、ReAct、Reflection、PlanSolve）均通过 `components` 参数接受组合。

以上断言核对组件身份和实际模型输入，`saved_path` 指向真实会话 JSON。预设回答只用于驱动协议，不能证明模型理解了预算。完整恢复与继续运行见 `python -X utf8 -m examples.agents.runtime_features --workspace workspace/runtime-demo`。接入真实模型时，将替身换成配置好的 `HelloAgentsLLM()`，其余组件组合保持不变。

## 默认装配与显式覆盖

默认关闭 Trace、Session、Skills、Subagent、TodoWrite 与 DevLog；使用相应 `Config(..._enabled=True)` 或显式注入组件开启。普通短输出不会创建截断目录。

不传 `components` 或传 `AgentComponents()`，都按 Config 创建组件。`history_manager`、`token_counter`、`truncator` 是运行所需组件；这三个字段的 `None` 表示创建默认实现，不表示禁用。

`session_store` 与 `skill_loader` 是可选组件，有三种含义：

- `DEFAULT_COMPONENT`（默认值）：使用 `Config.session_enabled` 或 `Config.skills_enabled` 决定是否创建默认实例。
- `None`：显式禁用该组件，即使 Config 中启用了默认能力。
- 组件实例：使用该实例，即使 Config 关闭了默认组件创建。

```python
from hello_agents import AgentComponents, DEFAULT_COMPONENT

use_defaults = AgentComponents(session_store=DEFAULT_COMPONENT)
disable_session = AgentComponents(session_store=None)
custom_session = AgentComponents(session_store=session)
```

显式 Skills 实例是否自动注册 `SkillTool`，仍由 `skills_auto_register` 控制，并要求提供 ToolRegistry。`skills_enabled` 只控制默认加载器创建，不能覆盖显式实例。

默认 Skill、Task、TodoWrite、DevLog 的注册入口现在位于 `core/components.py`，注册条件由 Config 与已注入的组件决定。没有工具注册表时不会自动创建一个（ReAct 在未传入注册表时创建默认注册表）。

## 组件契约

协议位于 `hello_agents.core.components`，按各自职责定义，无需继承共同基类。

- `HistoryProtocol`：正整数 `min_retain_rounds`，以及 `append`、`get_history`、`clear`、`compress`、`estimate_rounds`、`find_round_boundaries`。
- `TokenCounterProtocol`：`count_message`、`count_messages`、`clear_cache`。单条计数与总计数应保持同一估算规则。
- `TruncatorProtocol`：`truncate(tool_name, output)`，返回现有 Truncator 的预览与截断信息约定。
- `SessionStoreProtocol`：`save`、`load`、`list_sessions`，以及配置和工具定义的一致性检查方法；会话数据仍使用现有 SessionStore 格式。
- `SkillLoaderProtocol`：`get_descriptions`、`get_skill`、`list_skills`；`get_skill` 返回现有 Skill 数据结构或具有相同字段的对象。

构造时会检查消费所需的方法是否存在且可调用。无效注入在创建默认存储目录前报错；接口检查不会替自定义实现验证所有返回值或业务语义。

## 历史、摘要与计数的一致性

注入历史管理器的 `min_retain_rounds` 优先于 `Config.min_retain_rounds`。摘要输入的旧历史范围和真正保留的最近轮次均读取这个组件属性，避免 Config 要保留10轮、组件实际只保留2轮时遗漏中间内容。自定义 `compress` 也应遵守这个约定。

构造、历史整体替换、加载会话和临时子任务恢复后，Agent 重新计算自己的 `_history_token_count`。这个过程调用注入计数器的 `count_messages`，不清空其配置或缓存；主动 `clear_history()` 调用 `clear_cache()`。

自动压缩的触发阈值仍由 Config 的 `context_window` 和 `compression_threshold` 决定。组件化不改变简单摘要只统计消息数量的限制，也不保证模型生成的摘要完整。实际行为与边界见[上下文工程指南](context-engineering-guide.md)。

## 替换存储与 Skills

可以注入现有实现，也可以让自定义对象满足相同协议。例如，将 Skills 的来源封装成一个适配器，而不修改 Agent Loop：

```python
from hello_agents import AgentComponents
from hello_agents.skills import SkillLoader

class SkillCatalog:
    def __init__(self, loader):
        self.loader = loader

    def get_descriptions(self):
        return self.loader.get_descriptions()

    def list_skills(self):
        return self.loader.list_skills()

    def get_skill(self, name):
        return self.loader.get_skill(name)

catalog = SkillCatalog(SkillLoader("workspace/travel-skills"))
components = AgentComponents(skill_loader=catalog)
```

该适配器无需继承 SkillLoader。SessionStore 的替换同理，但需要保留会话字段和一致性检查契约。长期 MemoryStore 管的是带范围和修订状态的记录，它不是 SessionStore 的直接替代品，应通过 MemoryTool 或 ContextProvider 组合。

## 生命周期与支持范围

`AgentComponents` 是构造时注入；框架不克隆、不自动关闭宿主传入的资源。`agent.components` 是解析后的只读字段集合，可通过 `history_manager`、`session_store` 等属性访问运行中使用的组件。运行后直接替换属性不是本接口的热切换机制。

可变历史和计数器通常应每个 Agent 单独创建；把同一对象传给多个 Agent 会共享状态，不自动获得线程隔离。SessionStore 可指向独立会话目录，具体并发访问语义由存储实现负责。

TaskTool 的默认子代理工厂仍按 Config 创建子代理，不自动继承父 Agent 的实例，避免意外共享历史。需要指定子代理组件时，使用显式工厂为每个子代理创建自己的组件。

TraceLogger 生命周期与各 Agent 的专有 Planner、Executor 或反思轨迹不通过 AgentComponents 注入。`ContextProvider`/`ContextAssembler` 是 SimpleAgent 的独立构造参数；其他 Agent 当前未公开这些参数，不能直接照搬构造调用。

## 常见问题

**为什么使用 `None` 和默认标记两种值？**

需要区分“沿用原来配置”和“明确不要创建这个可选组件”。只有 `None` 无法同时表达这两种意图。

**传入空存储会被当作未启用吗？**

不会。可选组件使用 `is None` 判断是否启用，合法但布尔值为假的对象仍会参与保存和恢复。

**这是否提供了跨租户安全隔离？**

没有。注入控制组件来源与组合，身份、权限、文件访问和执行隔离仍由具体组件与宿主应用承担。

**怎样验证接口替换？**

```bash
python -m pytest tests/test_agent_components.py tests/test_context_pipeline.py
```

测试覆盖四种 Agent、独立协议实现、默认工具注册、真实会话文件往返、实际 Skill 加载、预载历史与计数、摘要范围以及子任务恢复。模型全部使用明确标注的本地替身，不需要外部 API。

## 从默认 Agent 逐步替换组件

第一次使用时，先创建只带业务工具的 SimpleAgent，检查模型能完成一次工具请求与回执。需要跨进程继续任务时再注入会话存储；需要每轮读取当前偏好时，再增加 Provider 和 ContextBuilder。每增加一个组件，保留原来的任务，观察输入、工具执行和结束状态发生了什么变化。

替换时从契约出发：改变“从哪里取资料”就实现 Provider；改变“资料如何进入消息”就实现 Assembler；改变“工具做什么”就注册 Tool。不要为了替换一个召回器，同时重写模型接口、运行循环和会话格式。

组件可以单独测试。先调用 Provider 检查 ContextPacket 的内容与来源，再调用 Assembler 检查预算和工具关联，最后通过 Agent 的实际请求确认接线。这样遇到问题时能分清是组件输出有误，还是输出没有进入运行路径。
