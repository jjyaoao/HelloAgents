# 异步执行与生命周期回调

异步入口让应用在等待模型或工具时处理其他任务。四种 Agent 共用执行循环，`arun()` 返回最终文本，`arun_stream()` 返回事件；工具并发策略由具体 Agent 决定。异步不会自动隔离共享历史、数据库或外部写入。

## 目录

- [先运行一个无需密钥的例子](#先运行一个无需密钥的例子)
- [使用回调观察一次运行](#使用回调观察一次运行)
- [并发任务与工具](#并发任务与工具)
- [超时取消与资源](#超时取消与资源)
- [接入真实模型](#接入真实模型)

## 先运行一个无需密钥的例子

先在源码根目录安装框架并执行：

```bash
python -m pip install -r requirements.txt
python -X utf8 -m examples.agents.runtime_features --workspace workspace/runtime-demo
```

示例使用明确标注的 `ScriptedLLM` 预设模型响应，实际执行异步工具、SQLite 查询和会话保存恢复。观察 `result.json`：首轮 `model_calls=2`、`tool_calls=1`、`status=completed`；恢复后保留工具请求与结果配对。它验证运行协议，不测量真实模型的决策能力。

## 使用回调观察一次运行

以下片段在源码根目录执行，无需密钥；与上述示例使用同一组公共接口。

```python
import asyncio
from tempfile import TemporaryDirectory
from examples.agents.runtime_features import ScriptedLLM, build_agent, response

async def main():
    observed = []

    async def started(event):
        observed.append((event.type.value, event.data["input_text"]))

    async def step_finished(event):
        observed.append((event.type.value, event.data["step"]))

    async def finished(event):
        observed.append((event.type.value, event.data["status"]))

    with TemporaryDirectory() as workspace:
        agent = build_agent(workspace, ScriptedLLM([response("离线协议完成")]))
        answer = await agent.arun(
            "检查回调", on_start=started, on_step=step_finished, on_finish=finished,
        )
        assert answer == "离线协议完成"
        assert observed[-1] == ("agent_finish", "completed")
        print(observed)

asyncio.run(main())
```

回调接收 `AgentEvent`，可为同步或异步函数；通过 `on_start`、`on_step`、`on_tool_call`、`on_finish`、`on_error` 关键字参数传入。Simple、Reflection 和 PlanSolve 的 `on_step` 在模型调用完成后收到 `step`、`usage`、`finish_reason` 和 `tool_count`。ReAct 在回合开始与结束时调用回调，使用事件类型区分 STEP_START 与 STEP_FINISH；它们都不等于一次外部操作。`on_tool_call` 可作为关键字传入，数据包含 `name`、`id`、JSON 字符串 `arguments` 和 `step`，同时提供字段 `tool_name`、`tool_call_id`、解析后的 `args`。`on_error` 收到 `error` 与 `error_type`。事件结构以[流式指南](streaming-sse-guide.md)为准。

回调有 `Config.hook_timeout_seconds` 限制，适合记录进度，不应用它持有锁来包围工具执行。授权和参数检查应在工具调度层完成。

## 并发任务与工具

一个 Agent 一次只能运行一个任务；同一实例并发调用会报错。独立任务创建独立 Agent，并分别管理历史和组件：

```python
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from examples.agents.runtime_features import ScriptedLLM, build_agent, response

async def main():
    with TemporaryDirectory() as workspace:
        agents = [build_agent(Path(workspace) / str(i), ScriptedLLM([response(str(i))]))
                  for i in range(2)]
        results = await asyncio.gather(*(agent.arun("独立任务") for agent in agents))
        assert results == ["0", "1"]

asyncio.run(main())
```

ReAct 对同一模型响应中的普通工具请求采用有界并发，`Config(max_concurrent_tools=1)` 可串行执行。含 `Thought` 或 `Finish` 的批次按顺序处理；其他 Agent 的共同工具循环默认逐项执行。模型不一定在同一响应发出多个请求，因此不能仅凭提示词或异步入口保证并行加速。

共享可变工具仍可能相互影响；尤其多个请求修改同一文件或记录时，应在宿主或工具内部协调。独立 Agent 不等于独立工具状态。

## 超时取消与资源

`llm_async_timeout` 管等待模型，`tool_async_timeout` 管单次工具等待。应用还可用 `asyncio.wait_for(agent.arun(...), timeout=...)` 限制整个任务。运行异常继续抛出，检查 `agent.last_run.status` 区分失败与取消；完整状态见[运行指南](runtime-guide.md)。

ReAct 一项工具超时后会取消并等待同批未完成的异步任务。Python 无法强制终止已在线程中运行的同步函数；取消不撤销已发生的副作用，也不保证线程立即停止。需要工具自己的超时、幂等键或补偿操作。

取消或失败后，历史保留已取得的工具回执，未取得回执的请求标为 `execution_status="unknown"`。关闭流或等待任务退出后再保存会话；恢复时先核实未知操作状态。完整例子的 `interrupted_resume` 演示有写入回执的中断恢复，继续运行没有重放该写操作。

提前结束事件流使用 `contextlib.aclosing`，不要只 `break` 后遗留生成器。Agent 本身没有异步上下文管理器接口，不能写 `async with ReActAgent(...)`。同步 `run()`、`stream_run()` 不能在已运行的事件循环中调用；Notebook 异步单元直接 `await agent.arun(...)`。

## 接入真实模型

将示例的 `ScriptedLLM` 换成 `HelloAgentsLLM()`，先配置 `LLM_MODEL_ID`、`LLM_API_KEY`、`LLM_BASE_URL`。任务需要工具时，选择支持 Function Calling 的模型。真实调用次数、工具顺序和耗时取决于模型及服务，不应沿用离线脚本的固定结果。

测试入口：`python -m pytest tests/test_runtime_contract.py tests/test_runtime_features_example.py`。测试使用离线响应或本地资源；异步文本与工具片段的传输方式见[流式与 SSE](streaming-sse-guide.md)。
