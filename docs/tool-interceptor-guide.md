# 工具调用拦截器 — Human-in-the-Loop 确认机制

## 概述

工具调用拦截器（`ToolInterceptor`）在工具实际执行之前插入一个可配置的确认节点，允许开发者在运行时决定是否放行某次工具调用。适用于文件写入确认、高危操作审批、付费 API 次数控制等场景。

**核心价值：**

- 默认 `AlwaysAllowInterceptor` 直接放行，完全向后兼容
- 一行代码切换确认策略，无需改动 Agent 或 Tool 代码
- 同步和异步路径全覆盖
- 支持缓存决策，避免重复打扰

## 快速开始

```python
from hello_agents import HelloAgentsLLM, SimpleAgent, ToolRegistry
from hello_agents.tools import (
    ReadTool, WriteTool, CalculatorTool,
    ConsoleConfirmInterceptor,
)

llm = HelloAgentsLLM()
registry = ToolRegistry()
registry.register_tool(ReadTool())
registry.register_tool(WriteTool())
registry.register_tool(CalculatorTool())

agent = ReactAgent("assistant", llm, tool_registry=registry)

# 一行代码启用控制台确认
agent.set_tool_interceptor(
    ConsoleConfirmInterceptor(
        whitelist={"Read", "python_calculator"},  # 这些工具不弹确认
        timeout=60.0,
    )
)

agent.run("读取 README.md，然后把版本号改为 2.0.0")
# ReadTool  → 自动放行（白名单）
# WriteTool → 打印参数并等待控制台输入 y/n
```

## 架构

```
                        ToolInterceptor (ABC)
                        ├── intercept()       同步拦截，所有子类必须实现
                        ├── aintercept()      异步拦截，默认在线程池中运行 intercept()
                        └── reset()           重置内部状态

    ┌──────────────────┼──────────────────┐
    │                  │                  │
AlwaysAllow      ConsoleConfirm     CallbackInterceptor
(默认放行)       (控制台 y/n)       (自定义回调)
                    │
             SessionConfirm
             (缓存决策，同参数只问一次)
```

### 执行链

```
Agent._execute_tool_call()          Agent._aexecute_tool_call()
  → interceptor.intercept()           → interceptor.aintercept()
  → tool.run_with_timing()            → tool.arun_with_timing()

ToolRegistry.execute_tool()          ToolRegistry.aexecute_tool()
  → circuit_breaker.is_open()
  → interceptor.intercept()           → interceptor.aintercept()
  → _execute_tool_internal()          → _execute_tool_internal()
```

## 四种策略详解

### 1. AlwaysAllowInterceptor — 默认放行

不做任何拦截，始终返回 `ALLOW`。框架默认行为，完全向后兼容。

```python
from hello_agents.tools import AlwaysAllowInterceptor

# 以下三种写法都使用AlwaysAllowInterceptor 
agent = ReActAgent("assistant", llm, tool_registry=registry) # 1. 自动使用AlwaysAllowInterceptor 

agent.set_tool_interceptor(AlwaysAllowInterceptor()) # 2. 使用AlwaysAllowInterceptor

registry = ToolRegistry()  # 3. 默认内置 AlwaysAllowInterceptor
```

### 2. ConsoleConfirmInterceptor — 控制台确认

在终端打印工具名称和参数，等待用户输入 `y`/`n`。

```python
from hello_agents.tools import ConsoleConfirmInterceptor

agent.set_tool_interceptor(
    ConsoleConfirmInterceptor(
        whitelist={"Read", "TodoWrite"},  # 白名单工具不弹确认
        timeout=60.0,          # 超时秒数（0=不限时），超时默认拒绝
        show_full_params=True, # 是否显示完整参数
        abort_on_deny=3,       # 连续拒绝 N 次后建议中止（返回拒绝理由中会提示）
    )
)
```

**控制台输出示例：**

```
┌──────────────────────────────────────────────────────────┐
│ 🔧 工具调用确认                                            │
├──────────────────────────────────────────────────────────┤
│  工具名称: WriteTool                                       │
│  Agent: assistant                                        │
│  描述: 写入文件内容                                          │
│──────────────────────────────────────────────────────────│
│  {                                                       │
│    "path": "/tmp/config.json",                           │
│    "content": "{\"version\": \"2.0.0\"}"                  │
│  }                                                       │
│──────────────────────────────────────────────────────────│
是否允许执行？[y/N] (60秒超时) y
✅ 已确认执行
```

### 3. SessionConfirmInterceptor — 会话级缓存

包裹另一个拦截器，对已确认的 `(工具名, 参数哈希)` 组合进行缓存。相同调用不会反复弹确认。

```python
from hello_agents.tools import SessionConfirmInterceptor

agent.set_tool_interceptor(
    SessionConfirmInterceptor(
        whitelist={"Read"},
        cache_denies=True,               # 拒绝决策也缓存
        confirm_each_new_params=True,     # 新参数时重新确认
        max_cache_size=500,              # 最大缓存条目（防内存泄漏）
        delegate=ConsoleConfirmInterceptor(),  # 实际确认逻辑（可替换）
    )
)
```

**行为示例：**

```python
# 第一次调用 WriteTool(path="/tmp/a.txt") → 弹确认 → 用户说 y → 缓存
# 第二次调用 WriteTool(path="/tmp/a.txt") → 命中缓存 → 直接通过
# 第三次调用 WriteTool(path="/tmp/b.txt") → 参数不同 → 弹确认
```

### 4. CallbackInterceptor — 自定义回调

将确认逻辑完全交给开发者。支持同步回调和异步回调。

```python
from hello_agents.tools import CallbackInterceptor, InterceptorResult

# === 同步回调：权限服务查询 ===
def my_permission_check(tool_name, params, context):
    DANGEROUS = {"Write", "Edit"}

    if tool_name in DANGEROUS:
        return InterceptorResult.deny(
            f"安全策略禁止使用 {tool_name}",
            policy="security_block"
        )

    return InterceptorResult.allow("权限检查通过")

agent.set_tool_interceptor(CallbackInterceptor(my_permission_check))
```

```python
# === 异步回调：HTTP 远程审批 ===
import aiohttp

async def remote_approval(tool_name, params, context):
    """向审批服务发送 HTTP 请求，等待审批结果"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://approval.internal/api/check",
            json={"tool": tool_name, "params": params, "agent": context.get("agent_name")}
        ) as resp:
            data = await resp.json()
            if data["approved"]:
                return InterceptorResult.allow(data["reason"])
            return InterceptorResult.deny(data["reason"])

agent.set_tool_interceptor(
    CallbackInterceptor(
        callback=my_permission_check,       # sync fallback
        async_callback=remote_approval,     # async 优先
    )
)

# 异步 Agent 使用
result = await agent.arun("删除过期日志")
```

## 设置方式

### 方式 1：Agent 级别（推荐）

```python
agent.set_tool_interceptor(ConsoleConfirmInterceptor(whitelist={"Read"}))
# 自动同步到 agent.tool_registry.interceptor
```

### 方式 2：Registry 级别

```python
registry = ToolRegistry(
    interceptor=ConsoleConfirmInterceptor(whitelist={"Read"})
)
# 所有使用该 registry 的执行都会被拦截
```

## InterceptorResult API

拦截器返回的决策对象：

```python
from hello_agents.tools import InterceptorResult, InterceptorDecision

# 允许执行
result = InterceptorResult.allow("原因说明", key="value")
result.is_allowed   # True
result.is_denied    # False
result.reason       # "原因说明"
result.metadata     # {"key": "value"}

# 拒绝执行
result = InterceptorResult.deny("拒绝原因", policy="block")
result.is_allowed   # False
result.is_denied    # True
result.reason       # "拒绝原因"
```

## 自定义拦截器

实现 `ToolInterceptor` 基类即可：

```python
from hello_agents.tools import ToolInterceptor, InterceptorResult

class RateLimitInterceptor(ToolInterceptor):
    """按工具限制调用次数"""

    def __init__(self, max_calls_per_tool: int = 10):
        self._max = max_calls_per_tool
        self._counts: dict[str, int] = {}

    def intercept(self, tool_name, parameters, context=None):
        count = self._counts.get(tool_name, 0)
        if count >= self._max:
            return InterceptorResult.deny(
                f"工具 {tool_name} 已达调用上限 {self._max} 次"
            )
        self._counts[tool_name] = count + 1
        return InterceptorResult.allow(f"第 {count + 1} 次调用")

    def reset(self):
        self._counts.clear()

agent.set_tool_interceptor(RateLimitInterceptor(max_calls_per_tool=5))
```

如果需要异步支持，重写 `aintercept()`：

```python
async def aintercept(self, tool_name, parameters, context=None):
    # 你的异步逻辑（如查数据库、发 HTTP 请求）
    approved = await self._check_remote_approval(tool_name, parameters)
    if approved:
        return InterceptorResult.allow()
    return InterceptorResult.deny("远程审批未通过")
```

## 异步支持说明

| Agent | 同步路径 | 异步路径 | 拦截器调用方式 |
|-------|---------|---------|--------------|
| SimpleAgent | `run()` → `_execute_tool_call()` | `arun()` 继承基类 → 线程池跑 `run()` | `intercept()` |
| ReActAgent | `run()` → `_execute_tool_call()` | `arun()` 自实现 → `aintercept()` 在线程池中运行 | `aintercept()` |
| ReflectionAgent | `run()` → `_execute_tool_call()` | `arun()` 继承基类 → 线程池跑 `run()` | `intercept()` |
| PlanSolveAgent | `run()` → `_execute_tool_call()` | `arun()` 继承基类 → 线程池跑 `run()` | `intercept()` |

**关键设计：** `ToolInterceptor.aintercept()` 默认实现在线程池中运行 `intercept()`。这对 `ConsoleConfirmInterceptor`（使用阻塞 `input()`）至关重要——在线程池中运行不会阻塞 asyncio 事件循环。`CallbackInterceptor` 如果提供了 `async_callback` 则走真正的异步路径。

## 测试

```bash
# 运行全部拦截器测试（含异步）
pytest tests/test_tool_interceptor.py -v

# 查看覆盖率
pytest tests/test_tool_interceptor.py -v --cov=hello_agents.tools.interceptor
```

## 参考

- 源码：`hello_agents/tools/interceptor.py`
- 示例：`examples/tool_interceptor_demo.py`（支持 `--interactive` 交互模式）
- 测试：`tests/test_tool_interceptor.py`（28 个用例）
