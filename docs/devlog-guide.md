# DevLog：记录决策与阶段结果

DevLog 保存任务中的决策、进展、问题和解决办法。它适合留下简短、可追踪的工作记录；自动运行轨迹请使用 [TraceLogger](observability-guide.md)。

## 📚 目录

- [最小示例](#最小示例)
- [参数](#参数)
- [一次任务中记录什么](#一次任务中记录什么)
- [组合与边界](#组合与边界)
- [常见问题](#常见问题)

## 最小示例

```python
from tempfile import TemporaryDirectory
from hello_agents.tools.builtin import DevLogTool
from hello_agents.tools.response import ToolStatus

with TemporaryDirectory() as directory:
    tool = DevLogTool(session_id="travel-demo", project_root=directory)
    reply = tool.run({
        "action": "append", "category": "decision",
        "content": "第二天优先选择室内景点。",
        "metadata": {"tags": ["weather"], "source": "用户确认"},
    })
    assert reply.status == ToolStatus.SUCCESS
    restored = DevLogTool(session_id="travel-demo", project_root=directory)
    records = restored.run({"action": "read", "filter": {"category": "decision", "limit": 5}})
    assert len(records.data["entries"]) == 1
    print(restored.run({"action": "summary"}).text)
    assert restored.run({"action": "clear"}).data["cleared_count"] == 1
```

同一目录和会话 ID 创建的新实例会读取已保存记录。`append` 返回记录 ID、时间和类别；`read` 返回 `data.entries`；`summary` 整理已有记录，不调用大语言模型。

## 参数

`action` 为 `append`、`read`、`summary`、`clear`。写入时提供 `category`、非空 `content` 及可选 `metadata`。类别包括 `decision`、`progress`、`issue`、`solution`、`refactor`、`test`、`performance`。

读取条件放在 `filter` 对象中，可包含 `category`、`tags` 和 `limit`。`clear` 删除当前会话记录并保存空状态，不是只清空显示。

## 一次任务中记录什么

旅行助手决定把室外行程改为室内时，日志应交代“依据什么作出什么决定”，而不是保存大段模型中间文本。例如，`decision` 记录改线决定，`issue` 记录原场馆已约满，`solution` 记录替代场馆和仍待确认的条件。

保持一条记录描述一个事件。来源标识放进 `metadata`，使后续阅读者能够回到用户确认或工具结果；不要把 API Key、完整认证头等运行配置写入日志。自动模型请求和工具回执交给 TraceLogger，DevLog 用于人工可读的阶段说明。

### 按类别和标签回看

```python
from tempfile import TemporaryDirectory
from hello_agents.tools.builtin import DevLogTool

with TemporaryDirectory() as directory:
    log = DevLogTool(session_id="trip-01", project_root=directory)
    for category, content in [
        ("issue", "原定场馆已约满，需要替代方案。"),
        ("decision", "先核对附近室内场馆的预约规则。"),
    ]:
        log.run({"action": "append", "category": category, "content": content,
                 "metadata": {"tags": ["booking"], "source": "fixture:booking"}})
    issues = log.run({"action": "read", "filter": {"category": "issue", "limit": 10}})
    assert len(issues.data["entries"]) == 1
    print(issues.data["entries"])
```

查询只返回匹配的记录，原来的决策仍保留在文件中。`summary` 是已有日志的整理视图，不会替你核验“场馆已约满”是否属实。

### 接入 Agent

应用自行注册 DevLogTool 时，可明确指定会话 ID 和目录。需要框架自动注册时，使用 `Config(devlog_enabled=True)`；要替换默认实例，参照组件组合指南。确认实际注册的工具名称后，再在任务指导中说明什么阶段需要记录。

## 组合与边界

使用 `registry.register_tool(DevLogTool(...))` 提供给模型；默认辅助工具由 `Config.devlog_enabled` 控制。自定义实例可通过 [AgentComponents](component-composition-guide.md) 注入。

记录保存在项目下的 `memory/devlogs/devlog-{session_id}.json`，可通过 `persistence_dir` 改变目录。会话 ID 应由宿主生成稳定、简单的标识，不把用户提供的路径直接作为 ID。

DevLog 记录调用方提交的文本，不自动判断事实真伪，也不会把所有日志自动加入下一次模型输入。需要检索和跨任务偏好管理时，使用 [记忆组件](memory-guide.md)。同一会话文件不提供跨进程并发事务，应避免多个写者共用。

## 常见问题

**DevLog 和长期记忆有什么不同？**

DevLog 按会话记录过程，适合复盘决定和问题；MemoryStore 管理带来源、可修订和可召回的事实。重要偏好需要后续参与判断时，应通过记忆或画像组件维护。

**记录之后，下一轮模型会自动读到吗？**

写入工具的回执会进入当前循环，但全部历史日志不会自动注入。需要回顾时调用 `read`，或由宿主筛选相关记录后放入上下文。

**清空操作能撤销吗？**

`clear` 会保存空记录。需要保留审阅依据时先另存文件，不能把清空当作暂时隐藏。
