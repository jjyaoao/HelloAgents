# 可观测性指南（Observability）

## 📖 概述

**TraceLogger** 是 HelloAgents 框架的双格式审计轨迹记录器，提供 JSONL（机器可读）和 HTML（人类可读）两种输出格式。

### 核心特性

- ✅ **双格式输出**：JSONL + HTML
- ✅ **流式追加**：实时写入，无需等待会话结束
- ✅ **自动脱敏**：API Key、路径等敏感信息
- ✅ **内置统计**：Token、工具调用、错误统计
- ✅ **可视化界面**：HTML 带交互式面板

---

## 🚀 快速开始

### 1. 自动集成（零配置）

```python
from hello_agents import ReActAgent, HelloAgentsLLM, Config

# TraceLogger 默认启用
config = Config(
    trace_enabled=True,
    trace_output_dir="memory/traces"
)

agent = ReActAgent("assistant", HelloAgentsLLM(), config=config)

# 运行任务
agent.run("分析项目结构")

# 自动生成 trace 文件
# memory/traces/trace-{session_id}.jsonl
# memory/traces/trace-{session_id}.html
```

### 2. 查看 Trace

**JSONL 格式（机器可读）：**
```bash
# 使用 jq 分析
cat memory/traces/trace-xxx.jsonl | jq '.event'

# 过滤工具调用
cat memory/traces/trace-xxx.jsonl | jq 'select(.event=="tool_call")'

# 统计 Token 使用
cat memory/traces/trace-xxx.jsonl | jq '.payload.usage.total_tokens' | awk '{sum+=$1} END {print sum}'
```

**HTML 格式（人类可读）：**
```bash
# 在浏览器中打开
open memory/traces/trace-xxx.html
```

HTML 界面包含：
- 📊 统计面板（Token、工具调用、错误）
- 📝 事件时间线（可折叠）
- 🔍 搜索和过滤
- 🎨 语法高亮

---

## 💡 核心概念

### 事件类型

TraceLogger 记录以下事件：

| 事件类型          | 描述           | 关键字段                    |
| ----------------- | -------------- | --------------------------- |
| `session_start`   | 会话开始       | agent_name, config          |
| `session_end`     | 会话结束       | duration, total_tokens      |
| `step_start`      | ReAct 步骤开始 | step, max_steps             |
| `step_end`        | ReAct 步骤结束 | step, action                |
| `tool_call`       | 工具调用       | tool_name, parameters       |
| `tool_result`     | 工具结果       | tool_name, status, duration |
| `llm_request`     | LLM 请求       | model, messages             |
| `llm_response`    | LLM 响应       | content, usage              |
| `error`           | 错误事件       | error_type, message         |
| `compression`     | 历史压缩       | before_count, after_count   |
| `session_save`    | 会话保存       | filepath                    |
| `circuit_breaker` | 熔断器触发     | tool_name, state            |

### 事件结构

```json
{
  "ts": "2026-02-21T10:30:45.123Z",
  "session_id": "s-20250220-a3f2d8e1",
  "step": 3,
  "event": "tool_call",
  "payload": {
    "tool_name": "Read",
    "parameters": {"path": "config.py"},
    "metadata": {...}
  }
}
```

---

## 📝 使用指南

### 1. 手动使用 TraceLogger

```python
from hello_agents.observability import TraceLogger

# 创建 logger
logger = TraceLogger(
    output_dir="memory/traces",
    sanitize=True,                      # 自动脱敏
    html_include_raw_response=False     # HTML 不包含原始响应
)

# 记录事件
logger.log_event("session_start", {
    "agent_name": "MyAgent",
    "config": {...}
})

logger.log_event("tool_call", {
    "tool_name": "Calculator",
    "parameters": {"expression": "2+3"}
}, step=1)

logger.log_event("tool_result", {
    "tool_name": "Calculator",
    "status": "success",
    "result": "5",
    "duration_ms": 10
}, step=1)

# 完成会话（生成最终 HTML）
logger.finalize()
```

### 2. 配置选项

```python
from hello_agents import Config

config = Config(
    # 可观测性配置
    trace_enabled=True,                 # 启用 TraceLogger
    trace_output_dir="memory/traces",   # 输出目录
    trace_sanitize=True,                # 自动脱敏
    trace_html_raw_response=False       # HTML 包含原始响应
)
```

### 3. 自动脱敏

TraceLogger 自动脱敏以下信息：

```python
# API Key
"api_key": "sk-1234567890abcdef"
# 脱敏后
"api_key": "sk-***"

# 路径
"path": "/Users/john/projects/myapp/config.py"
# 脱敏后
"path": ".../myapp/config.py"

# Authorization Header
"Authorization": "Bearer token123"
# 脱敏后
"Authorization": "Bearer ***"
```

---

## 📊 实际案例

### 案例 1：问题复盘

**场景：** Agent 执行失败，需要分析原因

```bash
# 1. 查看 HTML trace
open memory/traces/trace-xxx.html

# 2. 定位错误事件
# 在统计面板看到：错误数 = 3

# 3. 查看错误详情
# 点击错误事件，展开详情
# 发现：工具 'MCP' 连续失败 3 次

# 4. 分析根因
# 查看 tool_result 事件
# 错误码：CONNECTION_REFUSED
# 结论：MCP 服务器未启动
```

### 案例 2：性能分析

**场景：** 分析 Token 消耗和工具调用耗时

```bash
# 使用 jq 分析 JSONL
cat memory/traces/trace-xxx.jsonl | jq '
  select(.event=="llm_response") | 
  .payload.usage.total_tokens
' | awk '{sum+=$1} END {print "Total tokens:", sum}'

# 分析工具调用耗时
cat memory/traces/trace-xxx.jsonl | jq '
  select(.event=="tool_result") | 
  {tool: .payload.tool_name, duration: .payload.duration_ms}
'
```

### 案例 3：审计合规

**场景：** 生产环境审计，需要完整轨迹

```python
# 启用完整 trace（包含原始响应）
config = Config(
    trace_enabled=True,
    trace_html_raw_response=True,  # 包含 LLM 原始响应
    trace_sanitize=True            # 仍然脱敏敏感信息
)

agent = ReActAgent("assistant", llm, config=config)
agent.run("处理用户数据")

# 生成的 trace 包含：
# - 所有 LLM 请求和响应
# - 所有工具调用和结果
# - 时间戳和会话 ID
# - 自动脱敏的敏感信息
```

---

## 🎯 最佳实践

### 1. 生产环境启用 Trace

```python
# ✅ 好：生产环境启用，便于问题排查
config = Config(
    trace_enabled=True,
    trace_sanitize=True,           # 必须脱敏
    trace_html_raw_response=False  # 不包含原始响应（节省空间）
)
```

### 2. 定期清理旧 Trace

```bash
# 删除 7 天前的 trace
find memory/traces -name "trace-*.jsonl" -mtime +7 -delete
find memory/traces -name "trace-*.html" -mtime +7 -delete
```

### 3. 使用 JSONL 进行自动化分析

```python
import json

# 读取 JSONL
events = []
with open("memory/traces/trace-xxx.jsonl") as f:
    for line in f:
        events.append(json.loads(line))

# 统计工具调用次数
tool_calls = {}
for event in events:
    if event["event"] == "tool_call":
        tool_name = event["payload"]["tool_name"]
        tool_calls[tool_name] = tool_calls.get(tool_name, 0) + 1

print(tool_calls)
# {'Read': 5, 'Write': 2, 'Calculator': 1}
```

---

## 🔗 相关文档

- [日志系统](./logging-system-guide.md) - 四种日志范式对比
- [开发日志](./devlog-guide.md) - DevLogTool 使用
- [会话持久化](./session-persistence-guide.md) - 保存和恢复会话

---

## ❓ 常见问题

**Q: TraceLogger 会影响性能吗？**

A: 影响很小：
- JSONL 流式写入，无缓冲
- HTML 增量渲染，实时可查看
- 脱敏操作简单（正则替换）
- 性能开销 < 1%

**Q: 如何禁用 TraceLogger？**

A: 设置 `trace_enabled=False`：
```python
config = Config(trace_enabled=False)
```

**Q: JSONL 和 HTML 的区别？**

A:
- **JSONL**: 机器可读，适合自动化分析、日志聚合
- **HTML**: 人类可读，适合问题排查、可视化分析

**Q: 如何在 HTML 中搜索事件？**

A: HTML 内置搜索功能：
1. 打开 HTML 文件
2. 使用浏览器搜索（Ctrl+F / Cmd+F）
3. 搜索事件类型、工具名称、错误信息等

---

**最后更新**: 2026-02-21
