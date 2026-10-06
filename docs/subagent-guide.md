# 子代理：把一个明确子任务交给独立运行过程

子代理适合让检索、核对或局部规划使用独立的对话记录，再把结果交回主任务。工具实例可能仍然共享，因此独立上下文并不意味着独立进程或权限沙箱。

## 目录

- [运行一个子任务](#运行一个子任务)
- [作为工具调用](#作为工具调用)
- [工具集合与状态边界](#工具集合与状态边界)

## 运行一个子任务

从源码根目录安装 `python -m pip install -r requirements.txt`。下面使用明确的预设响应替身，不访问模型服务；子任务隔离、工具筛选和结果整理执行真实框架代码。

```python
from hello_agents.tools.tool_filter import ReadOnlyFilter
from examples.agents.runtime_features import ScriptedLLM, response
from hello_agents import Config, SimpleAgent

def build_agent(llm):
    return SimpleAgent("文档示例", llm, config=Config(
        trace_enabled=False, session_enabled=False, skills_enabled=False,
        subagent_enabled=False, todowrite_enabled=False, devlog_enabled=False,
    ))

agent = build_agent(ScriptedLLM([response("博物馆线路需要继续核对开放时间。")]))
before = list(agent.get_history())
result = agent.run_as_subagent(
    task="核对博物馆线路，列出尚缺的信息。",
    tool_filter=ReadOnlyFilter(),
    return_summary=True,
    max_steps_override=2,
)
assert result["success"]
assert "开放时间" in result["summary"]
assert agent.get_history() == before
print(result["metadata"])
```

`success` 表示子任务运行是否完成，`summary` 是返回的结果文本，`metadata` 包含运行状态、步数和耗时。任务完成不等于事实已经核验；业务方仍应检查来源和完成条件。

## 作为工具调用

`TaskTool` 通过工厂取得子代理。以下工厂为了演示固定返回 SimpleAgent；实际应用应按 `agent_type` 选择相应类型。

```python
from hello_agents.tools.builtin import TaskTool
from hello_agents.tools.response import ToolStatus

def make_child(agent_type):
    assert agent_type == "simple"
    return build_agent(ScriptedLLM([response("已核对：还需确认预约条件。")]))

task_tool = TaskTool(agent_factory=make_child)
reply = task_tool.run({
    "task": "核对预约条件", "agent_type": "simple",
    "tool_filter": "readonly", "max_steps": 2,
})
assert reply.status == ToolStatus.SUCCESS
print(reply.text)
```

注册 `task_tool` 到主代理的 `ToolRegistry` 后，模型可通过原生工具调用提出子任务。`agent_type` 可为 `simple`、`react`、`reflection`、`plan`；`max_steps` 必须是正整数。未知类型或过滤器会返回参数错误，不会降级为不受限制的执行。

## 工具集合与状态边界

`readonly` 使用名称白名单，允许文件读取、资料检索、记忆查询等工具；具有写入能力的 `MemoryTool` 不在其中。`full` 排除若干命令执行工具名，`none` 不筛选。自定义工具需要显式加入白名单，或使用 `CustomFilter(allowed=[...])`。

运行时为子任务创建独立的注册表名称映射和读取缓存，未指定过滤器时也会隔离。`registry.fork(names)` 同样可以显式创建子集；工具对象、函数及熔断器仍然共享。默认子代理工厂会重新装配与代理绑定的辅助工具，避免把父代理的 Task、Skill、TodoWrite、DevLog 直接绑定到子代理。

`run_as_subagent()` 只能复用空闲实例，同一个 Agent 不支持并发复用。子任务期间暂停父会话的自动保存，结束时恢复父历史、注册表、步数限制、运行结果及会话统计；执行中断或摘要生成失败时也执行恢复。需要独立保存子任务时，使用单独构造的 Agent 运行并保存其会话。状态恢复不会复制工具对象，也不会撤销工具对外部资源的修改。

名称过滤无法限制工具内部的文件访问、网络请求或写入副作用。需要权限隔离时，应在工具实现和宿主运行环境中约束资源。子任务失败、取消或历史恢复都不会撤销已经发生的外部操作。

进一步阅读：[运行状态](runtime-guide.md)、[组件组合](component-composition-guide.md)、[工具协议](tool-response-protocol.md)。
