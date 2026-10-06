# 将运行事件接入 Python 日志

应用日志负责把运行状态送入终端或日志平台；轨迹文件负责保存可回看的事件。两者可以同时使用。使用运行回调或流式事件接入应用已有的日志系统。

## 📚 目录

- [最小示例](#最小示例)
- [应用中的做法](#应用中的做法)
- [部署时怎样组织日志](#部署时怎样组织日志)
- [常见问题](#常见问题)

## 最小示例

下面使用离线协议替身，检查开始、结束回调确实进入标准库 `logging`。

```python
import asyncio
import io
import logging
from examples.agents.runtime_features import ScriptedLLM, response
from hello_agents import Config, SimpleAgent

def build_agent(llm):
    return SimpleAgent("文档示例", llm, config=Config(
        trace_enabled=False, session_enabled=False, skills_enabled=False,
        subagent_enabled=False, todowrite_enabled=False, devlog_enabled=False,
    ))

stream = io.StringIO()
logger = logging.getLogger("travel.runtime")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream)
logger.addHandler(handler)
logger.propagate = False

async def main():
    agent = build_agent(ScriptedLLM([response("资料已整理。")]))
    answer = await agent.arun(
        "整理资料",
        on_start=lambda event: logger.info("started: %s", event.data["input_text"]),
        on_finish=lambda event: logger.info("finished: %s", event.data["result"]),
        on_error=lambda event: logger.error("failed: %s", event.data["error"]),
    )
    assert answer == "资料已整理。"

try:
    asyncio.run(main())
    assert "started" in stream.getvalue() and "finished" in stream.getvalue()
    print(stream.getvalue())
finally:
    logger.removeHandler(handler)
    handler.close()
```

回调接收 `AgentEvent`。`on_start` 的 `data.input_text` 是输入，`on_finish` 的 `data.result` 和 `data.status` 是最终文本及状态，`on_error` 的 `data.error` 是错误说明。回调可为同步函数或异步函数。需要逐个文本增量或工具回执时，消费 `arun_stream()` 返回的事件，再把选定字段写入日志。

## 应用中的做法

在应用入口配置 handler，避免每次请求重复注册。把会话 ID、请求 ID、工具名和终止状态作为结构化字段保存；默认不要写入用户原文、密钥或完整工具参数。日志框架的级别设置不会自动关闭代码中所有 `print` 输出。

运行是否完成以 `last_run_result.status` 为准；收到文本不代表运行已经成功结束。若要排查具体工具参数和结果，可开启 `Config(trace_enabled=True, trace_dir="workspace/traces")`，并按数据保留策略管理轨迹文件。

相关指南：[运行轨迹](observability-guide.md)、[流式事件](streaming-sse-guide.md)、[运行状态](runtime-guide.md)。

## 部署时怎样组织日志

推荐在应用启动时配置一个具名 logger，并把请求标识、会话标识、Agent 名称和运行状态作为结构化字段。业务日志记录用户请求的生命周期；工具层记录服务调用是否成功；TraceLogger 保留需要回看的模型和工具事件。三者用相同请求标识关联，避免把所有内容拼成一行文本。

服务中重复创建 handler 会让同一事件输出多次。把日志初始化放在应用入口，清理测试或临时 handler 时调用 `removeHandler()` 和 `close()`；不要在每个工具函数里重复初始化整个日志系统。框架导入不会替应用选择全局日志级别。

## 常见问题

**为什么设置 WARNING 后，终端仍有文字？**

Python logging 只管理 logger 的记录，不能屏蔽普通 `print`。需要统一收集输出时，在宿主层区分标准输出、标准错误与日志，不要把所有终端文字都当成日志级别失效。

**on_finish 和 on_error 应怎样用于告警？**

将回调中的状态和 `last_run_result` 一起判断。超时、取消与预算结束不是相同故障；可以分别记录，避免把用户主动停止也当作服务异常。

**可以在生产日志中直接保存整个 event 吗？**

应先挑选字段。事件可能携带输入文本、工具结果和业务信息；按排查需要保存标识、状态和简短错误，再用受控轨迹定位详情。
