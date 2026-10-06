# 运行循环与结束状态

SimpleAgent、ReActAgent、ReflectionAgent 和 PlanSolveAgent 使用同一套工具运行循环。Agent 决定提示词和阶段安排，`core/runtime.py` 负责模型请求、工具执行、结果回填与终止判断。

## 目录

- [无需密钥的完整体验](#无需密钥的完整体验)
- [选择调用入口](#选择调用入口)
- [一个实际工具调用](#一个实际工具调用)
- [判断运行结果](#判断运行结果)
- [正确关闭流](#正确关闭流)
- [并发、超时与会话](#并发超时与会话)
- [运行测试](#运行测试)

## 无需密钥的完整体验

当一个 Agent 返回文字时，需要区分工具是否执行、循环是否正常结束、历史能否恢复。先在当前源码根目录安装并运行：

```bash
python -m pip install -r requirements.txt
python -X utf8 -m examples.agents.runtime_features --workspace workspace/runtime-demo
```

示例中的 `ScriptedLLM` 明确使用预设响应；SQLite、异步工具、消息组装、SessionStore 和流式事件实际运行。它验证机制，不检验模型质量，不访问外部 API。

打开 `workspace/runtime-demo/result.json`：首轮 `completed`，两次模型接口调用、一次工具执行；`resumed_tool_pair=true` 表示恢复后的实际输入保留工具关联；偏好从 `superseded` 到新记录的 `retracted`，另一用户无法查询。三个额外场景分别返回 `max_iterations`、`output_limit` 和 `failed`。`usage` 为空，因为离线替身没有服务端计量，不能用它计算费用。

`tool_result` 展示真实工具返回的三公里和七公里。`interrupted_resume` 则演示本地写入取得回执后主动关闭流：本轮状态为 `cancelled`，保存并恢复后仍有回执，继续调用不重复写入，`writes_this_run=1`、`resume_tool_calls=0`。这是预设响应控制下的协议演示；真实应用仍需幂等操作与结果核对。

工具的对象数组 Schema、`RouteTool.arun()` 和 `build_agent()` 都在这个例子中。可以分别替换 LLM、工具或 Provider，保留其余运行流程。检索与长期记忆的完整接口见 [RAG](rag-guide.md)、[Memory](memory-guide.md)；历史和会话的注入见[组件组合](component-composition-guide.md)。

## 选择调用入口

- `run(text)`：同步执行，返回最终文本。
- `arun(text)`：异步执行，返回最终文本。
- `stream_run(text)`：同步迭代公开文本片段。
- `arun_stream(text)`：异步迭代模型文本、工具与阶段事件。

四个入口均会执行工具。流式入口不会绕过工具循环。ReflectionAgent 保留“初始回答 → 评审 → 按需改进”，PlanSolveAgent 保留“生成计划 → 逐步执行”。流中的片段可能来自不同阶段；最终结果以 `AGENT_FINISH.data["result"]` 为准。

## 一个实际工具调用

配置 `LLM_MODEL_ID`、`LLM_API_KEY` 和 `LLM_BASE_URL`，选择支持 Function Calling 的模型。以下例子执行一个本地函数，模型需要根据实际返回值回答。

```python
import asyncio
from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.core.config import Config

registry = ToolRegistry()

async def lookup_ticket(query: str) -> str:
    return "杭州成人票内部编号：HZ-Q7N42"

registry.register_function(lookup_ticket, name="lookup_ticket",
                           description="查询票务内部编号，input 为查询条件")
agent = SimpleAgent(
    "旅行助手", HelloAgentsLLM(), tool_registry=registry,
    config=Config(skills_enabled=False, subagent_enabled=False,
                  todowrite_enabled=False, devlog_enabled=False,
                  session_enabled=False, trace_enabled=False),
)

async def main():
    answer = await agent.arun("请查询杭州成人票的内部编号")
    print(answer)
    print(agent.last_run.status, agent.last_run.model_calls)

asyncio.run(main())
```

`register_function` 保留单个 `input` 字符串参数的简便接口。需要多字段、对象数组或枚举时，使用 `Tool` 与 `ToolParameter.json_schema`，见[自定义工具指南](custom_tools_guide.md)。工具的完整 Schema 会直接发给模型，Agent 直接使用工具提供的完整声明。

可用模型支持的 `tool_choice` 关键字指定选择策略；它会透传到带工具的模型请求，最终无工具总结请求会去掉该参数。空或重复的工具调用 ID 在执行前拒绝，避免无法对应回执。模型原生异步接口可用时优先使用；只有同步接口的实现才在线程中等待。

## 判断运行结果

`agent.last_run` 包含 `answer`、`status`、`stop_reason`、`model_calls`、`tool_calls` 和 `usage`。

- `completed`：模型给出回答，或 ReAct 的 Finish 工具结束循环；不代表外部任务已经独立验收。
- `max_iterations`：达到工具迭代上限，完成最后一次无工具总结请求。单次工具循环最多产生“工具迭代上限 + 1”次模型请求；反思和计划可能包含多个循环以及额外的规划请求，不能把它当作整项任务的统一调用上限。
- `output_limit`：模型输出被截断。即使响应中含有工具片段，也不会执行不完整请求。
- `failed`：模型、运行程序或超时错误；异常继续抛给调用方。
- `cancelled`：调用被取消或流在运行中关闭。

模型未返回回答或工具请求时会抛出 `EmptyModelResponse`，不会作为空字符串成功结束。工具自身的可处理错误仍通过 ToolResponse 回填，模型可以据此修正下一次请求。

## 正确关闭流

提前退出迭代时使用 `aclosing`，确保模型连接和运行状态立即释放。

```python
from contextlib import aclosing
from hello_agents.core.streaming import StreamEventType

async def consume(agent, task):
    async with aclosing(agent.arun_stream(task)) as events:
        async for event in events:
            if event.type == StreamEventType.LLM_CHUNK:
                print(event.data["chunk"], end="", flush=True)
            elif event.type == StreamEventType.AGENT_FINISH:
                return event.data["result"]
```

OpenAI 兼容适配器支持原生文本与工具片段流。其他适配器当前可回退到完整响应后执行工具，不承诺逐 token 到达。不要在运行中的事件循环内调用同步入口；使用 `await arun()` 或异步事件流。

## 并发、超时与会话

一个 Agent 实例一次处理一个任务。独立并发任务使用独立 Agent；如果共享同一个可变 Tool 实例，工具自身仍需处理并发访问。

ReAct 对同一响应中的普通工具请求保留有界并发，数量由 `max_concurrent_tools` 控制；含 Thought 或 Finish 的批次按顺序处理。会修改同一资源的工具应设置 `max_concurrent_tools=1`。任一任务超时后会取消同批未完成的异步任务，尚未启动的任务不会继续派发。

`llm_async_timeout` 限制等待模型的时间，不计入下游消费者暂停读取的时间；`tool_async_timeout` 限制单次工具等待时间。Python 无法强制终止已经进入线程的同步函数，取消不等于撤销已发生的外部写入；需要工具自身提供幂等、超时或补偿机制。

会话保留原生工具请求与对应结果，本轮历史在完成事件发出前提交；启用自动保存且满足间隔时，也在该事件前写盘。恢复后继续调用时仍能带上配对的工具轨迹。自动保存按 `auto_save_interval` 累计新增消息，在完整运行结束时检查，避免保存半个工具回合。

取消或失败也保留本轮已取得的回执；对已记录请求但缺少回执的调用，补入 `execution_status="unknown"`。它表示运行器无法确认结果，不代表没有执行或已经回滚。关闭流或捕获异常后可以 `save_session()`；恢复先核对外部状态和回执，不应盲目重试有副作用的操作。进程被强制终止时不能保证完成保存。

`load_session()` 禁止在同一实例运行中调用。加载先解析和检查快照，再替换历史与缓存；没有读取缓存的会话也会清除原实例遗留的缓存。`save_session("名称")` 的名称不接受路径，目录由 SessionStore 配置；文件使用唯一临时文件替换，失败时清理本次临时文件。进一步边界见[会话指南](session-persistence-guide.md)。

子代理使用独立的注册表名称映射，工具过滤同时适用于 Tool 与函数。默认工厂不继承父代理绑定的 Task/Skill/TodoWrite/DevLog，而根据子配置重新装配；默认禁用递归 Task。`fork()` 共享业务工具实例和熔断器，不等同于进程或工具内部状态隔离。

## 运行测试

模型失败会抛出异常。重复工具名在注册时拒绝，宿主要替换实现应显式使用 `replace=True`。模型请求直接使用工具提供的完整 Schema，声明构建错误在注册时暴露。

在源码根目录安装测试依赖，再检查四种入口、异步工具、取消与恢复、超时、Schema、文件写入、过滤规则和文档例子：

```bash
python -m pip install -r requirements/test.txt
python -m pytest tests/test_runtime_contract.py tests/test_tool_contract_fixes.py tests/test_recovery_edges.py tests/test_runtime_features_example.py
```

上述测试使用离线替身；真实服务验收需另行配置密钥。

历史压缩使用 token 预算和完整轮次；异步与流式能力由调用入口选择。
