# TodoWrite：维护当前任务清单

TodoWrite 把多步任务的当前进度保存在一个结构化清单中。模型可以更新清单，应用也可以直接调用；状态由调用方填写，工具不会自动验证任务成果。

## 📚 目录

- [最小示例](#最小示例)
- [更新方式](#更新方式)
- [完整流程：创建、推进与恢复](#完整流程创建推进与恢复)
- [组合与边界](#组合与边界)
- [常见问题](#常见问题)

## 最小示例

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from hello_agents.tools.builtin import TodoWriteTool
from hello_agents.tools.response import ToolStatus

with TemporaryDirectory() as directory:
    tool = TodoWriteTool(project_root=directory)
    reply = tool.run({
        "action": "create", "summary": "核对旅行方案",
        "todos": [
            {"content": "查阅预约说明", "status": "completed"},
            {"content": "核对步行距离", "status": "in_progress"},
        ],
    })
    assert reply.status == ToolStatus.SUCCESS
    assert reply.data["stats"]["completed"] == 1
    saved = next((Path(directory) / "memory/todos").glob("*.json"))
    restored = TodoWriteTool(project_root=directory)
    restored.load_todos(str(saved))
    assert restored.current_todos.get_stats()["total"] == 2
    assert restored.run({"action": "clear"}).data["stats"]["total"] == 0
    print(reply.text)
```

输出展示完成数、当前任务与待处理事项。`data.stats` 可供界面展示，`current_todos` 可由应用读取。

## 更新方式

`create` 和 `update` 都提交完整清单快照。更新某一项时，应同时提交其他仍需保留的任务；省略的任务不会自动合并。每项包含非空字符串 `content`，以及 `pending`、`in_progress`、`completed` 之一的 `status`。最多一项处于 `in_progress`。

`clear` 清空当前清单并保存空快照。文件写入 `persistence_dir`，默认是项目下的 `memory/todos`；文件名含秒级时间，同一秒内更新可能覆盖该快照。初始化不自动选择历史文件，需用 `load_todos(filepath)` 指定恢复对象。

## 完整流程：创建、推进与恢复

长任务通常先创建清单，完成一个步骤后再提交新快照。下面每次都保留两项任务；第二次调用只改变它们的状态。

```python
from tempfile import TemporaryDirectory
from hello_agents.tools.builtin import TodoWriteTool
from hello_agents.tools.response import ToolStatus

with TemporaryDirectory() as directory:
    todo = TodoWriteTool(project_root=directory)
    first = todo.run({"action": "create", "summary": "完成旅行核对", "todos": [
        {"content": "核对预约规则", "status": "in_progress"},
        {"content": "核对步行距离", "status": "pending"},
    ]})
    assert first.status == ToolStatus.SUCCESS
    second = todo.run({"action": "update", "summary": "完成旅行核对", "todos": [
        {"content": "核对预约规则", "status": "completed"},
        {"content": "核对步行距离", "status": "in_progress"},
    ]})
    assert second.data["stats"]["total"] == 2
    assert second.data["stats"]["completed"] == 1
    print(second.text)
```

清单中的“完成”应在资料已经回读或结果已经检查后设置。每次提供完整快照，界面与模型就能看到同一份当前计划。需要保存每一步更详细的决策理由时，可同时使用 [DevLog](devlog-guide.md)。

### 接入模型与界面

将 `TodoWriteTool(project_root=...)` 注册到 ToolRegistry，模型就能通过 `TodoWrite` 请求更新清单。宿主从回执的 `data.stats` 读取数量，从工具保存的当前清单读取事项；不要通过匹配展示文本里的 emoji 来判断状态。

只需要应用自己维护进度时，直接调用 `run()` 即可，不必让模型参与每次更新。多位用户应绑定各自的工作目录，避免把一个实例作为所有会话的全局清单。

## 组合与边界

注册 `TodoWriteTool` 后，模型通过原生工具请求更新进度。Agent 的默认辅助工具由 `Config.todowrite_enabled` 控制；要注入自己的实例，见 [组件组合](component-composition-guide.md)。

清单是计划记录，不是调度器或成果校验器。完成标记不能替代测试、来源核对或人工验收。当前文件持久化不提供多进程任务协调；并行任务应使用独立目录或独立工具实例。

## 常见问题

**能只提交刚完成的那一项吗？**

不能按增量更新理解。`update` 替换整个清单，应保留所有仍需要展示的事项；否则它们会从当前状态中消失。

**重启后为什么没有自动出现原任务？**

初始化不会猜测应恢复哪个文件。由宿主保存快照路径，再显式调用 `load_todos()`。不应随意取目录中第一个文件作为某位用户的当前任务。

**怎样运行多项并行工作？**

当前清单最多有一项 `in_progress`，适合串行推进一个主任务。真正的后台并发用 JobQueue 管理，各子任务可拥有独立清单。
