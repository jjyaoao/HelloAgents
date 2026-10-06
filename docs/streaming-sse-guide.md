# 流式事件与 SSE

流式接口用于显示正在生成的文本和已发生的工具操作。事件流中的中间文本可能是初稿、评审或某个计划步骤，最终答案应读取 `AGENT_FINISH.data["result"]`，不能把所有文本片段拼接后当作所有 Agent 的最终答案。

## 目录

- [先观察真实事件结构](#先观察真实事件结构)
- [字段与完成条件](#字段与完成条件)
- [转换为 SSE](#转换为-sse)
- [最小 Web 接入](#最小-web-接入)
- [关闭与传输边界](#关闭与传输边界)

## 先观察真实事件结构

在源码根目录先运行 `python -m pip install -r requirements.txt`。以下片段无需密钥，使用明确的预设响应替身，流式资源管理和 Agent 循环仍由框架执行。

```python
import asyncio
from contextlib import aclosing
from tempfile import TemporaryDirectory
from examples.agents.runtime_features import ScriptedLLM, build_agent, response
from hello_agents.core.streaming import StreamEventType

async def main():
    with TemporaryDirectory() as workspace:
        agent = build_agent(workspace, ScriptedLLM([response("离线文本片段")]))
        async with aclosing(agent.arun_stream("观察事件")) as stream:
            async for event in stream:
                if event.type == StreamEventType.LLM_CHUNK:
                    print(event.data["chunk"], end="")
                elif event.type == StreamEventType.AGENT_FINISH:
                    assert event.data["result"] == "离线文本片段"
                    assert event.data["status"] == "completed"
        assert agent.last_run.status == "completed"

asyncio.run(main())
```

完整的结构化工具执行与会话恢复例子：`python -X utf8 -m examples.agents.runtime_features --workspace workspace/runtime-demo`。查看 `result.json` 的 `stream_events`，再对照会话文件中原生 `tool_call_id`，检查展示事件与可恢复历史的区别。

## 字段与完成条件

`event.type` 是 `StreamEventType` 枚举；序列化后的 `type` 与 SSE 事件名是小写，例如 `llm_chunk`。当前运行器产生的字段如下：

| 事件 | `data` 中的主要字段 |
| --- | --- |
| `agent_start` | `input_text` |
| `llm_chunk` | `chunk` |
| `tool_call_start` | `name`、`id`、`arguments`、`step` |
| `tool_call_finish` | `name`、`id`、`result`、`step` |
| `step_start` / `step_finish` | 阶段相关字段，如 `phase`、`step`、`plan` 或 `result` |
| `agent_finish` | `result`、`status`、`stop_reason` |
| `error` | `error`、`error_type` |

`arguments` 是原生工具请求的 JSON 字符串，`result` 是模型可读的序列化工具结果。计划/反思产生阶段事件，ReAct 保留工具回合的 `STEP_START` / `STEP_FINISH`。Reflection 的 `THINKING` 表示公开评审文本，带 `phase="reflection"` 与 `iteration`，不输出模型私有推理。ReAct 的回合开始事件带 `max_steps`；该字段不是所有事件都有，也没有统一的 `duration_ms` 或逐 token 序号。完成事件提供 `result`、`total_steps` 和结束状态，具体含义见[运行指南](runtime-guide.md)。

完成事件表示循环结束，`status` 仍可能是 `max_iterations` 或 `output_limit`。工具 `ToolResponse.error` 通常回填给模型继续判断；运行级错误产生 `error` 事件后继续抛出异常，不会跟一个成功完成事件。完整含义见[运行指南](runtime-guide.md)。

## 转换为 SSE

```python
import json
from hello_agents.core.streaming import StreamEvent, StreamEventType

event = StreamEvent.create(StreamEventType.LLM_CHUNK, "demo", chunk="你好")
frame = event.to_sse()
assert frame.startswith("event: llm_chunk\n")
assert frame.endswith("\n\n")
payload = json.loads(frame.split("data: ", 1)[1])
assert payload["data"]["chunk"] == "你好"
print(frame)
```

SSE 的 `data` 是完整事件对象，包含 `type`、`timestamp`、`agent_name` 和嵌套 `data`，浏览器需要读取 `payload.data.chunk`。`timestamp` 为数值时间戳。当前没有事件 ID 或断点续传缓存。

## 最小 Web 接入

安装 Web 示例依赖并启动服务：

```bash
python -m pip install -r requirements/web.txt
python -X utf8 -m examples.web.fastapi_sse_server
```

打开 `http://127.0.0.1:8000` 使用配套页面。默认使用明确的离线预设响应，运行真实 Agent 和 SSE 传输。需要真实模型时，配置 `LLM_MODEL_ID`、`LLM_API_KEY`、`LLM_BASE_URL`，再设置 `HELLOAGENTS_DEMO_LIVE=1` 启动服务。

服务接收 `POST /agent/stream`，JSON 请求体为 `{"input": "你好", "agent_type": "simple"}`；类型也可选 `react`、`reflection`、`plan`。配套客户端使用 `fetch` 读取 POST 响应流，不能直接换成仅支持 GET 的 `EventSource`。

需要接入自己的代理工厂时，保存下面代码为 `server.py`，运行 `python -m uvicorn server:app`：

```python
from fastapi import FastAPI
from examples.web.fastapi_sse_server import create_app, build_agent

# 工厂每次调用返回新 Agent；可替换为自己的组件装配函数。
app: FastAPI = create_app(agent_factory=build_agent)
```

每次请求创建独立 Agent，避免共享历史并发冲突。这个示例不提供用户身份、长期会话或访问授权；需要多轮会话时，由宿主按用户与会话标识选择 SessionStore，并串行处理同一会话。生产部署还需管理反向代理、连接数量、请求超时及日志内容。

## 关闭与传输边界

`aclosing` 保证提前退出时关闭 Agent 事件源。客户端断开时，服务框架取消生成器，`finally`/上下文管理器负责释放连接。`stream_to_sse` 等格式转换辅助函数不会替调用方管理所有权；组合时仍持有并关闭原始 Agent 流。

关闭未完成的流后状态为 `cancelled`。已取得的工具回执进入历史；缺失回执使用 `execution_status="unknown"` 补齐关联，以便保存和恢复，不能据此声称外部操作被撤销。客户端重连后应先读取会话状态，不要自动重放整项任务。

OpenAI 兼容适配器可输出文本增量和工具参数片段；不同服务的分片粒度不同，不等于每个 token 一个事件。其他适配器可回退为完整响应后输出，不保证相同首包延迟。代理缓存、浏览器缓冲和网络也会影响可见延迟，不能承诺“无缓冲、无开销”。

`StreamBuffer` 只是本地保留最近事件的列表，不是运行器内置的可靠队列、重连协议或生产者背压机制。完整性要求应由宿主单独实现。
