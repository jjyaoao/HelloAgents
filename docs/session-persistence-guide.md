# 会话保存与恢复

会话保存让后续调用继续使用已有消息、工具请求和回执。它保存的是运行记录快照，不是 Python 进程、网络连接或工具内部状态；恢复历史不会自动重放工具。

## 目录

- [无需密钥的体验](#无需密钥的体验)
- [最小保存与恢复](#最小保存与恢复)
- [中断以后怎样继续](#中断以后怎样继续)
- [保存内容与环境检查](#保存内容与环境检查)
- [自动保存与文件边界](#自动保存与文件边界)
- [组合与常见问题](#组合与常见问题)

## 无需密钥的体验

在源码根目录安装并运行：

```bash
python -m pip install -r requirements.txt
python -X utf8 -m examples.agents.runtime_features --workspace workspace/runtime-demo
```

例子使用明确的预设响应替身，真实执行工具与文件操作。在 `sessions/travel-protocol.json` 查看工具请求和相同 `tool_call_id` 的回执；`result.json` 的 `resumed_tool_pair=true` 表示它们已经进入恢复后下一次模型接口输入。

另一个 `interrupted-write.json` 保存主动关闭流时的历史：本地记录只写一次，恢复后已有成功回执，模型接口的预设续答不再要求写入。`interrupted_resume` 应为 `cancelled → completed`，本次工具写入次数为 `1`。它验证恢复协议，不证明真实模型永远不会重复请求。

## 最小保存与恢复

下面在源码根目录执行，无需密钥；使用与完整例子相同的构造函数，该函数通过 `AgentComponents` 注入 SessionStore。

```python
from tempfile import TemporaryDirectory
from examples.agents.runtime_features import ScriptedLLM, build_agent, response

with TemporaryDirectory() as workspace:
    first = build_agent(workspace, ScriptedLLM([response("已记录对话")]))
    first.run("记录这一轮")
    path = first.save_session("first-turn")

    llm = ScriptedLLM([response("已接续上一轮")])
    second = build_agent(workspace, llm)
    second.load_session(path)
    second.run("继续")
    assert any(m.get("content") == "记录这一轮" for m in llm.requests[0]["messages"])
    print(second.last_run.status)
```

使用真实服务时替换 `ScriptedLLM` 为配置好的 `HelloAgentsLLM()`。保存路径来自 `save_session()` 的返回值，不要猜测自动生成的会话文件名。启用方式可以是 `Config(session_enabled=True, session_dir="...")`，也可以显式注入 `AgentComponents(session_store=SessionStore(...))`。

## 中断以后怎样继续

取消、模型失败或工具超时后，运行器保留本轮已经取得的工具回执；对已记录请求但没有回执的调用补充 `execution_status="unknown"`。未知表示不能从当前记录确认结果，不是“未执行”，也不是“已回滚”。异步流应先完成关闭，再保存。

应用可以按下列顺序处理：

1. 等待任务退出或用 `aclosing` 关闭事件流。
2. 读取 `agent.last_run.status` 和历史中的工具回执。
3. 调用 `agent.save_session("interrupted-task")`。
4. 恢复后先核对未知操作的外部状态，再决定继续、补查或重试。

同一实例运行时禁止 `load_session()`，避免替换正在使用的历史。对于付款、提交订单、发送消息等操作，仅保存工具调用 ID 不足以防重，需要宿主或工具提供业务幂等键和状态查询。强制杀死进程或掉电时不能保证执行保存逻辑。

## 保存内容与环境检查

快照包含历史消息、Agent 配置摘要、工具 Schema 哈希、读取缓存和统计元数据。原生工具请求与回执保存在消息元数据中，加载后继续按消息协议组装。工具实例、外部数据库和 API 客户端不序列化；应在构造新 Agent 时重新提供。

工具 Schema 哈希覆盖发送给模型的完整定义，包括描述、参数类型、必填项和函数工具，注册顺序不影响哈希。它用于发现会话恢复前后的接口变化；不会验证工具内部实现或外部资源是否变化。

`load_session(path, check_consistency=True)` 默认比较配置与工具声明，发现变化时给出提示，不自动安装依赖或还原工具实现。`check_consistency=False` 仅跳过这些环境差异提示，不跳过快照字段解析。

加载会先解析历史与元数据，并计算历史计数，成功后再替换现有历史。快照没有读取缓存时，会清空实例此前的缓存，避免把旧会话的文件修改时间带入新任务。会话文件仍属于应用数据，不应随意加载不可信来源。

## 自动保存与文件边界

`Config(session_enabled=True, auto_save_enabled=True, auto_save_interval=10)` 按新增消息累计触发检查；统一运行器在完整运行结束时保存，避免在一组工具请求与回执之间截断。异常/取消的历史整理也经过保存逻辑，但仍受配置与间隔控制。因此重要中断场景应显式保存，不能宣称一定自动生成 `session-error.json` 或 `session-interrupted.json`。

`save_session("name")` 的名称是文件名，不是路径；目录通过 SessionStore 配置。`SessionStore` 使用同目录独占临时文件写入后替换目标，失败只清理本次临时文件。同一个 Store 实例的写入通过实例锁串行化；不同实例或进程写同名文件的覆盖顺序仍不受保证，宜使用独立目录或名称。相同名称会替换旧快照，默认自动保存名为 `session-auto`。原子替换不是跨进程事务锁，也不保证机器崩溃后的持久性。

`list_sessions()` 返回已保存会话的摘要；`SessionStore.load(path)` 是底层 JSON 读取，Agent 的 `load_session()` 额外执行历史恢复与一致性检查。应用通常使用 Agent 入口，不需要直接操作内部字典。

## 组合与常见问题

**与 MemoryStore 有什么区别？**

会话历史记录发生过什么；MemoryStore 维护当前有效的偏好、事实陈述及其修订关系。撤回记忆不会抹掉旧会话中的文本，需要[上下文与历史策略](context-engineering-guide.md)共同处理。

**能否直接共享同一个 Agent 给多个请求？**

不能并发运行同一实例。按会话串行执行，或创建独立 Agent 并分开状态。共享目录也不提供用户身份认证或跨租户权限隔离。

**怎样验证？**

```bash
python -m pytest tests/test_runtime_features_example.py
```

离线示例测试会检查真实保存文件、恢复后的实际输入，以及中断前后本地写入次数。真实模型是否正确理解回执需要另行验证。
