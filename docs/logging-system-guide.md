# 日志系统指南（Logging System）

## 📖 概述

HelloAgents 框架提供**四种日志范式**，满足不同场景的日志需求：

1. **TraceLogger** - 执行轨迹审计（JSONL + HTML）
2. **AgentLogger** - Agent 运行日志（结构化）
3. **DevLogTool** - 开发日志工具（Agent 可用）
4. **标准 logging** - Python 标准日志

---

## 🚀 快速开始

### 1. TraceLogger（执行轨迹）

```python
from hello_agents import ReActAgent, HelloAgentsLLM
from hello_agents.core.observability import TraceLogger

# 启用 TraceLogger
logger = TraceLogger(output_dir="logs")
agent = ReActAgent("assistant", HelloAgentsLLM(), trace_logger=logger)

# 执行任务
agent.run("分析项目")

# 查看日志
# - logs/trace.jsonl（机器可读）
# - logs/trace.html（人类可读）
```

### 2. AgentLogger（Agent 日志）

```python
from hello_agents import ReActAgent, HelloAgentsLLM
from hello_agents.core.logging import AgentLogger

# 启用 AgentLogger
logger = AgentLogger(name="assistant", level="INFO")
agent = ReActAgent("assistant", HelloAgentsLLM(), logger=logger)

# 执行任务
agent.run("分析项目")

# 日志输出：
# [2026-02-21 10:30:45] [INFO] [assistant] Agent 开始执行
# [2026-02-21 10:30:46] [INFO] [assistant] 调用工具: Read
# [2026-02-21 10:30:47] [INFO] [assistant] Agent 完成
```

### 3. DevLogTool（开发日志）

```python
from hello_agents import ReActAgent, HelloAgentsLLM, Config

# 启用 DevLogTool
config = Config(devlog_enabled=True)
agent = ReActAgent("assistant", HelloAgentsLLM(), config=config)

# Agent 可以使用 DevLog 工具
agent.run("记录开发决策：使用 Redis 作为缓存")

# 查看日志
# - memory/devlogs/devlog-xxx.json
```

### 4. 标准 logging

```python
import logging
from hello_agents import ReActAgent, HelloAgentsLLM

# 配置标准 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

agent = ReActAgent("assistant", HelloAgentsLLM())
agent.run("分析项目")

# 日志输出：
# 2026-02-21 10:30:45,123 [INFO] Agent 开始执行
```

---

## 💡 四种范式对比

| 范式         | 用途           | 格式         | 可读性 | Agent 可用 | 持久化 |
| ------------ | -------------- | ------------ | ------ | ---------- | ------ |
| TraceLogger  | 执行轨迹审计   | JSONL + HTML | 高     | ❌          | ✅      |
| AgentLogger  | Agent 运行日志 | 结构化文本   | 中     | ❌          | ✅      |
| DevLogTool   | 开发决策记录   | JSON         | 高     | ✅          | ✅      |
| 标准 logging | 通用日志       | 文本         | 低     | ❌          | ✅      |

---

## 📝 使用指南

### 1. TraceLogger 详细说明

**特点：**
- ✅ 记录所有 LLM 请求和工具调用
- ✅ 双格式输出（JSONL + HTML）
- ✅ 支持审计和回放

**配置：**
```python
from hello_agents.core.observability import TraceLogger

logger = TraceLogger(
    output_dir="logs",           # 输出目录
    jsonl_file="trace.jsonl",    # JSONL 文件名
    html_file="trace.html",      # HTML 文件名
    enable_jsonl=True,           # 启用 JSONL
    enable_html=True             # 启用 HTML
)
```

**日志内容：**
```json
{
  "timestamp": "2026-02-21T10:30:45.123Z",
  "event_type": "llm_request",
  "data": {
    "messages": [...],
    "model": "gpt-4",
    "temperature": 0.7
  }
}
{
  "timestamp": "2026-02-21T10:30:46.456Z",
  "event_type": "tool_call",
  "data": {
    "tool_name": "Read",
    "parameters": {"path": "config.py"},
    "result": "..."
  }
}
```

**查看 HTML 报告：**
```bash
# 在浏览器中打开
open logs/trace.html
```

### 2. AgentLogger 详细说明

**特点：**
- ✅ 结构化日志（时间戳、级别、消息）
- ✅ 支持多个 Agent 独立日志
- ✅ 可配置日志级别

**配置：**
```python
from hello_agents.core.logging import AgentLogger

logger = AgentLogger(
    name="assistant",           # Logger 名称
    level="INFO",               # 日志级别（DEBUG/INFO/WARNING/ERROR）
    output_file="agent.log",    # 输出文件
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
)
```

**日志级别：**
```python
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
```

**多 Agent 日志：**
```python
# Agent 1
logger1 = AgentLogger(name="explorer", output_file="explorer.log")
agent1 = ReActAgent("explorer", llm, logger=logger1)

# Agent 2
logger2 = AgentLogger(name="analyzer", output_file="analyzer.log")
agent2 = ReActAgent("analyzer", llm, logger=logger2)
```

### 3. DevLogTool 详细说明

**特点：**
- ✅ Agent 可以主动记录日志
- ✅ 7 种日志类别（decision、progress、issue 等）
- ✅ 结构化存储（JSON）

**使用：**
```python
# 启用 DevLogTool
config = Config(devlog_enabled=True)
agent = ReActAgent("assistant", llm, config=config)

# Agent 使用 DevLog 工具
agent.run("""
记录开发决策：
- category: decision
- content: 使用 Redis 作为缓存
- metadata: {"reason": "高性能"}
""")
```

**详细文档：** 参见 [DevLog 指南](./devlog-guide.md)

### 4. 标准 logging 详细说明

**特点：**
- ✅ Python 标准库，无需额外依赖
- ✅ 灵活配置（Handler、Formatter）
- ✅ 与其他库兼容

**配置：**
```python
import logging

# 基本配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# 使用
logger = logging.getLogger(__name__)
logger.info("Agent 开始执行")
```

---

## 📊 实际案例

### 案例 1：生产环境监控

**场景：** 监控 Agent 运行状态

```python
# 使用 AgentLogger + 标准 logging
import logging
from hello_agents.core.logging import AgentLogger

# 配置标准 logging（应用级别）
logging.basicConfig(level=logging.INFO)

# 配置 AgentLogger（Agent 级别）
agent_logger = AgentLogger(
    name="production_agent",
    level="INFO",
    output_file="logs/agent.log"
)

agent = ReActAgent("assistant", llm, logger=agent_logger)

# 执行任务
try:
    result = agent.run("处理用户请求")
except Exception as e:
    logging.error(f"Agent 执行失败: {e}")
```

### 案例 2：开发调试

**场景：** 调试 Agent 执行过程

```python
# 使用 TraceLogger + AgentLogger
from hello_agents.core.observability import TraceLogger
from hello_agents.core.logging import AgentLogger

# TraceLogger（详细轨迹）
trace_logger = TraceLogger(output_dir="debug_logs")

# AgentLogger（DEBUG 级别）
agent_logger = AgentLogger(name="debug_agent", level="DEBUG")

agent = ReActAgent(
    "assistant",
    llm,
    trace_logger=trace_logger,
    logger=agent_logger
)

# 执行任务
agent.run("分析项目")

# 查看日志
# - debug_logs/trace.html（可视化轨迹）
# - agent.log（详细日志）
```

### 案例 3：项目复盘

**场景：** 记录开发决策和问题

```python
# 使用 DevLogTool
config = Config(devlog_enabled=True)
agent = ReActAgent("assistant", llm, config=config)

# Agent 记录开发日志
agent.run("""
1. 记录决策：使用 PostgreSQL 作为数据库
2. 记录问题：内存泄漏导致服务崩溃
3. 记录解决方案：修复内存泄漏
""")

# 查询日志
agent.run("查询所有问题日志")
```

---

## 🎯 最佳实践

### 1. 根据场景选择日志范式

```python
# ✅ 生产环境：AgentLogger + 标准 logging
agent_logger = AgentLogger(name="prod", level="INFO")
logging.basicConfig(level=logging.WARNING)

# ✅ 开发调试：TraceLogger + AgentLogger（DEBUG）
trace_logger = TraceLogger(output_dir="debug")
agent_logger = AgentLogger(name="dev", level="DEBUG")

# ✅ 项目管理：DevLogTool
config = Config(devlog_enabled=True)
```

### 2. 日志分级

```python
# DEBUG：详细调试信息
logger.debug(f"工具参数: {parameters}")

# INFO：普通信息
logger.info("Agent 开始执行")

# WARNING：警告信息
logger.warning("工具调用超时，重试中...")

# ERROR：错误信息
logger.error(f"Agent 执行失败: {error}")
```

### 3. 日志轮转

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "agent.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5           # 保留 5 个备份
)

logging.basicConfig(handlers=[handler])
```

---

## 🔗 相关文档

- [可观测性](./observability-guide.md) - TraceLogger 详细说明
- [DevLog 指南](./devlog-guide.md) - DevLogTool 详细说明

---

## ❓ 常见问题

**Q: 如何同时使用多种日志范式？**

A: 可以组合使用：
```python
trace_logger = TraceLogger(output_dir="logs")
agent_logger = AgentLogger(name="assistant", level="INFO")
config = Config(devlog_enabled=True)

agent = ReActAgent(
    "assistant",
    llm,
    trace_logger=trace_logger,
    logger=agent_logger,
    config=config
)
```

**Q: 日志文件太大怎么办？**

A: 使用日志轮转：
```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler("agent.log", maxBytes=10*1024*1024, backupCount=5)
```

**Q: 如何禁用所有日志？**

A: 设置日志级别为 CRITICAL：
```python
logging.basicConfig(level=logging.CRITICAL)
```

---

**最后更新**: 2026-02-21
