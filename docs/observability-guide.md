# 运行轨迹：定位模型、工具与结束状态

轨迹用于回答三个问题：模型请求了什么，工具实际返回了什么，运行为什么结束。HelloAgents 的 `TraceLogger` 同时写 JSONL 和 HTML；JSONL 适合程序分析，HTML 适合逐项查看。

## 📚 目录

- [写入一条本地轨迹](#写入一条本地轨迹)
- [接入 Agent](#接入-agent)
- [从现象定位到一次调用](#从现象定位到一次调用)
- [解读与保存](#解读与保存)
- [常见问题](#常见问题)

## 写入一条本地轨迹

下面不调用模型。临时目录内的文件会在退出后删除；要保留结果，把目录换成自己的工作目录。

```python
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from hello_agents.observability import TraceLogger

with TemporaryDirectory() as directory:
    trace = TraceLogger(output_dir=directory, sanitize=True)
    trace.log_event("tool_call", {"name": "rag_search", "arguments": {"query": "预约"}}, step=1)
    trace.log_event("tool_result", {"name": "rag_search", "status": "success", "text": "找到预约说明"}, step=1)
    trace.finalize()
    events = [json.loads(line) for line in Path(trace.jsonl_path).read_text(encoding="utf-8").splitlines()]
    assert any(event["event"] == "tool_result" for event in events)
    assert Path(trace.html_path).exists()
    print([event["event"] for event in events])
```

每条记录包含 `ts`、`session_id`、`step`、`event` 和 `payload`。文件名由实例生成，使用 `jsonl_path` 和 `html_path` 获取实际路径。调用 `finalize()` 写入汇总并关闭文件。

## 接入 Agent

通过 `Config(trace_enabled=True, trace_dir="workspace/traces")` 配置自动轨迹。`trace_sanitize` 控制模式匹配脱敏，`trace_html_include_raw_response` 控制 HTML 是否附带原始响应。Agent 在运行结束时整理轨迹，无需在构造参数中传入 `trace_logger`。

自动记录的事件包括会话开始、模型输出、工具请求、工具回执、错误和会话结束。它不承诺保存供应商完整 HTTP 请求或所有内部计算；模型最终状态请同时查看 `agent.last_run`。演示完整流程：

```bash
python -X utf8 -m examples.agents.runtime_features --workspace workspace/runtime-demo
```

## 从现象定位到一次调用

排查“回答采用了旧偏好”时，按事件顺序逐层核对：

1. 找到本轮模型收到的参考资料或相关工具结果，确认五公里的新偏好是否已经进入运行过程。
2. 找到模型的工具请求，核对查询文本和记录标识；若没有发起检索，继续检查工具是否已注册、描述是否足以识别用途。
3. 查看工具回执中的状态和正文，区分“未命中”“索引过期”和正常返回。
4. 最后检查运行终止状态，确认回答是否在预算耗尽或异常之前提前停止。

若回执仍是旧记录，问题在存储、索引同步或上下文选取；若回执已经是新记录而回答错误，应进一步检查模型如何使用资料。轨迹可以缩小定位范围，但不自动给出语义判断。

### 配置最少需要哪些项

```python
from hello_agents import Config

config = Config(
    trace_enabled=True,
    trace_dir="workspace/traces",
    trace_sanitize=True,
    trace_html_include_raw_response=False,
)
```

把 `config` 传给 Agent。日常应用可先关闭 HTML 中的原始响应，保留事件与结构化状态；需要诊断供应商返回时再明确开启。这个开关只控制 HTML 展示，不代替 JSONL 的检查与保留策略。

为不同任务保留会话标识，依据 `jsonl_path` 和 `html_path` 找到文件，而不是自己猜测文件名。应用需建立“业务请求 ID → 会话/轨迹路径”的对应，用户报告问题时才有可定位的运行记录。

## 解读与保存

先核对工具调用 ID 与回执，再核对运行终止原因。工具报错后模型可能修正参数继续执行；单个错误事件不必然意味着整轮失败。`max_iterations`、`output_limit`、`failed` 和 `cancelled` 也不能当作成功回答。

Token 统计依赖模型服务返回的用量字段，缺失值不能解释为没有成本。耗时包含实际调度和工具执行，不宜拿单次本地预设响应推断模型性能。

脱敏仅覆盖已定义的密钥和路径模式，不能保证识别任意个人信息、业务资料或新格式密钥。发布轨迹前仍需检查内容。HTML 输出是一次运行的阅读视图，不是长期监控后台。

相关指南：[日志接入](logging-system-guide.md)、[异步与取消](async-agent-guide.md)、[会话恢复](session-persistence-guide.md)。

## 常见问题

**为什么工具错误后，整轮仍然 completed？**

工具错误可以被模型读取并修正。例如第一次参数不合法，第二次成功，最终循环可以正常结束。应同时看具体回执和整轮状态。

**能只保存终端日志吗？**

可以，但终端文字未必保留工具参数、请求关联和结构化状态。需要复现执行过程时，保存 JSONL；面向人工检查时保留对应 HTML。
