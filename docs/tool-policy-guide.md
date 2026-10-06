# 工具权限策略指南

工具能被模型看到，不等于允许执行。`ToolRegistry(policy=...)` 在同步、异步和子注册表调用的共同入口检查宿主策略；拒绝或策略故障时不执行工具，也不计入工具服务的熔断失败。

## 📚 目录

- [快速开始](#快速开始)
- [完整示例：按请求参数决定是否放行](#完整示例按请求参数决定是否放行)
- [检查具体参数](#检查具体参数)
- [与其他控制的关系](#与其他控制的关系)
- [常见问题](#常见问题)

## 快速开始

```python
from hello_agents import ToolRegistry
from hello_agents.tools import AllowlistPolicy, ReadTool

registry = ToolRegistry(policy=AllowlistPolicy(["Read"]))
registry.register_tool(ReadTool())
```

未传策略时执行宿主注册的工具。`AllowlistPolicy` 默认拒绝名单以外的工具，包括后来注册的工具。名称区分大小写，应与工具 Schema 一致。子表 `registry.fork()` 保留同一宿主策略。

## 完整示例：按请求参数决定是否放行

旅行助手可以读取资料，但只有宿主确认过的预约才允许修改。下面用内存字典模拟预约，观察策略拒绝后业务函数是否真的没有执行；无需模型或数据库。

```python
from hello_agents import ToolRegistry
from hello_agents.tools import PermissionDecision, ToolResponse
from hello_agents.tools.response import ToolStatus

bookings = {"museum": 60}
approved = {"museum": 90}  # 仅由宿主维护，示例中已确认的目标值
executed = []

def policy(name, arguments):
    allowed = (
        name == "booking_update" and isinstance(arguments, dict)
        and arguments.get("minutes") == approved.get(arguments.get("booking_id"))
        and arguments.get("booking_id") in approved
    )
    return PermissionDecision(allowed, "请求必须与宿主确认的预约及目标时长一致")

def update_booking(arguments):
    executed.append(arguments.copy())
    bookings[arguments["booking_id"]] = arguments["minutes"]
    return ToolResponse.success(text="预约已更新", data=dict(bookings))

registry = ToolRegistry(policy=policy)
registry.register_function(update_booking, name="booking_update", description="更新预约时长")
denied = registry.execute_tool("booking_update", {"booking_id": "museum", "minutes": 120})
assert denied.status == ToolStatus.ERROR
assert bookings["museum"] == 60 and not executed
allowed = registry.execute_tool("booking_update", {"booking_id": "museum", "minutes": 90})
assert allowed.status == ToolStatus.SUCCESS
assert bookings["museum"] == 90 and len(executed) == 1
print(denied.to_dict())
print(allowed.to_dict())
```

两次请求都指向已注册工具，但只有 90 分钟的请求进入业务函数。这里展示的是参数级放行；实际预约工具仍要独立校验字段类型、业务规则和版本。`approved` 是本地演示数据，真实应用应将审批绑定到可信身份、准确参数和有效期限。

### 接到 Agent Loop

把上述 `registry` 传给 `SimpleAgent(..., tool_registry=registry)` 即可。模型提出工具请求后，注册表在执行前调用策略；拒绝结果作为错误回执进入后续上下文，模型可以解释限制或提出其他方案。无需把权限判断放在模型提示词中执行。

## 检查具体参数

```python
from hello_agents.tools import PermissionDecision

def policy(name, arguments):
    if name == "booking_update":
        return PermissionDecision(False, "需要宿主确认后执行预约修改")
    return PermissionDecision(name in {"booking_read", "rag_search"})

registry = ToolRegistry(policy=policy)
```

对 `Tool` 对象，策略看到解析后的参数对象；对函数式工具，看到函数即将接收的输入。传入策略的是副本，策略不能靠修改参数隐式重写工具请求。策略必须同步返回 `PermissionDecision`；抛异常、返回错误类型或协程都按拒绝处理。

需要人工确认时，在宿主 UI 核对工具名、具体参数、用户身份和当前状态，再为相应请求授予有限权限；不要让模型发一句“已获批准”就放行。这个组件不实现持久化审批队列或后台等待。通用名称白名单也不能替代资源级权限检查。

## 与其他控制的关系

生命周期 Hooks 观察步骤和事件；权限策略决定请求能否进入执行。文件根目录限制、操作系统沙箱和数据库权限约束执行后的资源访问。修改型工具仍需验证业务版本、幂等键和参数，避免重试造成重复副作用。一个工具内部再次执行其他操作时，不会自动获得新的沙箱边界。

```bash
python -m pytest tests/test_tool_policy.py
```

测试覆盖同步与异步拒绝、子表继承、策略故障、参数副本，以及最小 Agent 默认不注册额外工具、不创建存储目录。

## 常见问题

**模型还能看到被拒绝的工具，是否说明权限无效？**

工具可见性和执行权限分别处理。缩小工具集合有助于模型选择，策略则保证进入注册表的请求必须通过宿主检查。即使提示词诱导模型调用其他工具，未获允许的请求也不会通过这个入口执行。

**怎样在用户批准后继续？**

宿主记录具体批准内容，更新受控的审批状态后重新发起对应操作。不要笼统地把整个工具永久加入白名单。修改参数、换用户或业务版本变化后，应重新判断是否仍属于已批准请求。

**直接调用 `tool.run()` 也会检查策略吗？**

不会。策略属于 ToolRegistry。需要统一控制的调用应经过注册表；工具内部的资源权限和业务校验仍应保留。
