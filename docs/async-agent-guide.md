# 异步 Agent 指南（Async Agent）

## 📖 概述

**异步 Agent** 是 HelloAgents 框架的异步执行能力，支持 `arun()` 和 `arun_stream()` 方法，实现并行工具调用和流式输出。

### 核心特性

- ✅ **向后兼容**：现有 `run()` 方法完全不变
- ✅ **工具并行**：用户工具并行执行，内置工具串行
- ✅ **生命周期钩子**：on_start、on_step、on_tool_call、on_finish、on_error
- ✅ **流式输出**：实时返回 LLM 输出和工具调用

---

## 🚀 快速开始

### 1. 异步执行

```python
import asyncio
from hello_agents import ReActAgent, HelloAgentsLLM

async def main():
    agent = ReActAgent("assistant", HelloAgentsLLM())
    
    # 异步执行
    result = await agent.arun("分析项目结构")
    print(result)

asyncio.run(main())
```

### 2. 流式输出

```python
import asyncio
from hello_agents import ReActAgent, HelloAgentsLLM

async def main():
    agent = ReActAgent("assistant", HelloAgentsLLM())
    
    # 流式执行
    async for event in agent.arun_stream("分析项目结构"):
        if event.type == "LLM_CHUNK":
            print(event.data["content"], end="", flush=True)
        elif event.type == "TOOL_CALL_START":
            print(f"\n🔧 调用工具: {event.data['tool_name']}")
        elif event.type == "TOOL_CALL_FINISH":
            print(f"✅ 工具完成: {event.data['tool_name']}")

asyncio.run(main())
```

---

## 💡 核心概念

### 1. 异步方法

| 方法            | 同步版本 | 功能                 |
| --------------- | -------- | -------------------- |
| `arun()`        | `run()`  | 异步执行，返回结果   |
| `arun_stream()` | 无       | 流式执行，返回事件流 |

### 2. 生命周期钩子

```python
from hello_agents.core.lifecycle import LifecycleHook, AgentEvent

class MyHook(LifecycleHook):
    async def on_start(self, event: AgentEvent):
        print(f"Agent 开始: {event.data['input']}")
    
    async def on_step(self, event: AgentEvent):
        print(f"步骤 {event.data['step']}")
    
    async def on_tool_call(self, event: AgentEvent):
        print(f"调用工具: {event.data['tool_name']}")
    
    async def on_finish(self, event: AgentEvent):
        print(f"Agent 完成: {event.data['result']}")
    
    async def on_error(self, event: AgentEvent):
        print(f"错误: {event.data['error']}")

# 注册钩子
agent = ReActAgent("assistant", llm)
agent.register_hook(MyHook())
```

### 3. 工具并行执行

**ReActAgent 并行策略：**
- ✅ **用户工具**：并行执行（Read、Write、Search 等）
- ✅ **内置工具**：串行执行（Thought、Finish）

```python
# 示例：并行调用 3 个工具
async def main():
    agent = ReActAgent("assistant", llm, tool_registry=registry)
    
    # Agent 会并行调用 Read、Search、Calculator
    result = await agent.arun("读取 config.py，搜索文档，计算 2+3")
    
    # 执行时间：max(Read, Search, Calculator) 而非 sum

asyncio.run(main())
```

---

## 📝 使用指南

### 1. 基本异步执行

```python
import asyncio
from hello_agents import ReActAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools.builtin import ReadTool, SearchTool

async def main():
    # 创建 Agent
    registry = ToolRegistry()
    registry.register_tool(ReadTool(project_root="./"))
    registry.register_tool(SearchTool())
    
    agent = ReActAgent("assistant", HelloAgentsLLM(), tool_registry=registry)
    
    # 异步执行
    result = await agent.arun("读取 README.md 并搜索相关文档")
    print(result)

asyncio.run(main())
```

### 2. 流式输出

```python
import asyncio
from hello_agents import ReActAgent, HelloAgentsLLM
from hello_agents.core.streaming import StreamEventType

async def main():
    agent = ReActAgent("assistant", HelloAgentsLLM())
    
    # 流式执行
    async for event in agent.arun_stream("分析项目"):
        if event.type == StreamEventType.AGENT_START:
            print("🚀 Agent 开始")
        
        elif event.type == StreamEventType.STEP_START:
            print(f"\n📍 步骤 {event.data['step']}")
        
        elif event.type == StreamEventType.THINKING:
            print(f"💭 思考: {event.data['content']}")
        
        elif event.type == StreamEventType.TOOL_CALL_START:
            print(f"🔧 调用: {event.data['tool_name']}")
        
        elif event.type == StreamEventType.TOOL_CALL_FINISH:
            print(f"✅ 完成: {event.data['tool_name']}")
        
        elif event.type == StreamEventType.LLM_CHUNK:
            print(event.data["content"], end="", flush=True)
        
        elif event.type == StreamEventType.AGENT_FINISH:
            print("\n🎉 Agent 完成")

asyncio.run(main())
```

### 3. 生命周期钩子

```python
import asyncio
from hello_agents import ReActAgent, HelloAgentsLLM
from hello_agents.core.lifecycle import LifecycleHook, AgentEvent

class LoggingHook(LifecycleHook):
    """日志钩子"""
    
    async def on_start(self, event: AgentEvent):
        print(f"[START] 输入: {event.data['input']}")
    
    async def on_tool_call(self, event: AgentEvent):
        print(f"[TOOL] {event.data['tool_name']}: {event.data['parameters']}")
    
    async def on_finish(self, event: AgentEvent):
        print(f"[FINISH] 结果: {event.data['result'][:100]}...")

class MetricsHook(LifecycleHook):
    """指标钩子"""
    
    def __init__(self):
        self.tool_calls = 0
        self.steps = 0
    
    async def on_step(self, event: AgentEvent):
        self.steps += 1
    
    async def on_tool_call(self, event: AgentEvent):
        self.tool_calls += 1
    
    async def on_finish(self, event: AgentEvent):
        print(f"📊 统计: {self.steps} 步, {self.tool_calls} 次工具调用")

async def main():
    agent = ReActAgent("assistant", HelloAgentsLLM())
    
    # 注册多个钩子
    agent.register_hook(LoggingHook())
    agent.register_hook(MetricsHook())
    
    # 执行任务
    result = await agent.arun("分析项目")

asyncio.run(main())
```

---

## 📊 实际案例

### 案例 1：并行工具调用

**场景：** 同时读取多个文件

```python
import asyncio
from hello_agents import ReActAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools.builtin import ReadTool

async def main():
    registry = ToolRegistry()
    registry.register_tool(ReadTool(project_root="./"))
    
    agent = ReActAgent("assistant", HelloAgentsLLM(), tool_registry=registry)
    
    # Agent 会并行读取 3 个文件
    result = await agent.arun("""
    读取以下文件：
    1. config.py
    2. main.py
    3. utils.py
    """)
    
    # 执行时间：max(read1, read2, read3) 而非 sum

asyncio.run(main())
```

**性能提升：**
```
串行执行：3 × 1s = 3s
并行执行：max(1s, 1s, 1s) = 1s
提升：3 倍
```

### 案例 2：实时进度显示

**场景：** 显示 Agent 执行进度

```python
import asyncio
from hello_agents import ReActAgent, HelloAgentsLLM
from hello_agents.core.streaming import StreamEventType

async def main():
    agent = ReActAgent("assistant", HelloAgentsLLM())
    
    print("🚀 开始分析项目...")
    
    async for event in agent.arun_stream("分析项目结构"):
        if event.type == StreamEventType.STEP_START:
            print(f"\n📍 步骤 {event.data['step']}/{event.data['max_steps']}")
        
        elif event.type == StreamEventType.TOOL_CALL_START:
            print(f"  🔧 {event.data['tool_name']}...", end="", flush=True)
        
        elif event.type == StreamEventType.TOOL_CALL_FINISH:
            duration = event.data.get('duration_ms', 0)
            print(f" ✅ ({duration}ms)")
        
        elif event.type == StreamEventType.AGENT_FINISH:
            print("\n🎉 分析完成！")

asyncio.run(main())
```

**输出示例：**
```
🚀 开始分析项目...

📍 步骤 1/10
  🔧 Read... ✅ (245ms)
  🔧 Search... ✅ (1230ms)

📍 步骤 2/10
  🔧 Calculator... ✅ (10ms)

🎉 分析完成！
```

### 案例 3：错误处理

**场景：** 捕获和处理异步错误

```python
import asyncio
from hello_agents import ReActAgent, HelloAgentsLLM
from hello_agents.core.lifecycle import LifecycleHook, AgentEvent

class ErrorHandler(LifecycleHook):
    async def on_error(self, event: AgentEvent):
        error = event.data['error']
        print(f"❌ 错误: {error}")
        
        # 记录错误日志
        with open("errors.log", "a") as f:
            f.write(f"{event.timestamp}: {error}\n")

async def main():
    agent = ReActAgent("assistant", HelloAgentsLLM())
    agent.register_hook(ErrorHandler())
    
    try:
        result = await agent.arun("执行可能失败的任务")
    except Exception as e:
        print(f"任务失败: {e}")

asyncio.run(main())
```

---

## 🎯 最佳实践

### 1. 使用异步上下文管理器

```python
import asyncio
from hello_agents import ReActAgent, HelloAgentsLLM

async def main():
    async with ReActAgent("assistant", HelloAgentsLLM()) as agent:
        result = await agent.arun("任务")
        # Agent 自动清理资源

asyncio.run(main())
```

### 2. 批量任务并行执行

```python
import asyncio
from hello_agents import ReActAgent, HelloAgentsLLM

async def process_task(agent, task):
    return await agent.arun(task)

async def main():
    agent = ReActAgent("assistant", HelloAgentsLLM())
    
    tasks = [
        "分析 module1",
        "分析 module2",
        "分析 module3"
    ]
    
    # 并行执行所有任务
    results = await asyncio.gather(*[
        process_task(agent, task) for task in tasks
    ])
    
    for i, result in enumerate(results):
        print(f"任务 {i+1}: {result}")

asyncio.run(main())
```

### 3. 超时控制

```python
import asyncio
from hello_agents import ReActAgent, HelloAgentsLLM

async def main():
    agent = ReActAgent("assistant", HelloAgentsLLM())
    
    try:
        # 设置 60 秒超时
        result = await asyncio.wait_for(
            agent.arun("长时间任务"),
            timeout=60.0
        )
    except asyncio.TimeoutError:
        print("任务超时")

asyncio.run(main())
```

---

## 🔗 相关文档

- [流式输出](./streaming-sse-guide.md) - SSE 协议和前端集成
- [可观测性](./observability-guide.md) - 追踪异步执行
- [Function Calling](./function-calling-architecture.md) - 异步工具调用

---

## ❓ 常见问题

**Q: 同步和异步方法可以混用吗？**

A: 可以，但不推荐：
```python
# ✅ 好：统一使用异步
async def main():
    result = await agent.arun("任务")

# ❌ 不好：混用同步和异步
def main():
    result = agent.run("任务")  # 同步
    asyncio.run(agent.arun("任务"))  # 异步
```

**Q: 如何禁用工具并行执行？**

A: 目前不支持禁用，但可以通过钩子控制：
```python
class SerialHook(LifecycleHook):
    def __init__(self):
        self.lock = asyncio.Lock()
    
    async def on_tool_call(self, event: AgentEvent):
        async with self.lock:
            # 强制串行执行
            pass
```

**Q: 流式输出的性能开销？**

A: 几乎没有开销：
- 使用原生 AsyncOpenAI 客户端
- 逐个 token 传输，无缓冲
- 内存占用低

---

**最后更新**: 2026-02-21
