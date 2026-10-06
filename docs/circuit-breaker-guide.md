# 工具熔断：暂时停止重复失败的调用

熔断器按工具名称统计连续失败。达到阈值后，注册表在一段时间内拒绝执行该工具，让模型看到明确错误，避免继续重复同一个失败操作。

## 📚 目录

- [最小示例](#最小示例)
- [怎样理解一次熔断](#怎样理解一次熔断)
- [参数与状态查询](#参数与状态查询)
- [状态与组合](#状态与组合)
- [常见问题](#常见问题)

## 最小示例

```python
from hello_agents import ToolRegistry
from hello_agents.tools import ToolResponse
from hello_agents.tools.circuit_breaker import CircuitBreaker
from hello_agents.tools.response import ToolStatus

breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60)
registry = ToolRegistry(circuit_breaker=breaker)
calls = []

def unavailable(value):
    calls.append(value)
    return ToolResponse.error("UNAVAILABLE", "教学服务暂不可用")

registry.register_function(unavailable, name="lookup", description="查询教学服务")
for _ in range(3):
    result = registry.execute_tool("lookup", "杭州")
assert result.status == ToolStatus.ERROR
assert len(calls) == 2
assert breaker.is_open("lookup")
breaker.close("lookup")
assert not breaker.is_open("lookup")
print(result.to_dict())
```

第三次请求在执行前被拦截，因此函数实际只调用两次。`close(name)` 手动恢复；冷却期结束后，后续 `is_open` 检查也会使工具重新可执行。

## 怎样理解一次熔断

假设检索服务连续返回错误。第一次和第二次调用确实进入服务，注册表记录失败；达到阈值后，第三次请求直接得到熔断回执。这样下一轮模型能够获知服务暂不可用，而不是继续支付同一失败调用的时间。

```text
调用服务 → 错误 → 累积失败
调用服务 → 错误 → 达到阈值，开放熔断
再次请求 → 注册表直接拒绝
冷却结束 → 下次检查关闭熔断 → 可以重新调用
```

这里“开放”表示阻断调用，“关闭”表示可以调用。恢复后仍可能失败；熔断器不会修复网络、补充额度或修改错误参数。

## 参数与状态查询

| 参数 | 默认值 | 调整依据 |
| --- | --- | --- |
| `failure_threshold` | `3` | 连续失败多少次后暂时阻断 |
| `recovery_timeout` | `300` | 冷却秒数，按外部服务恢复速度选择 |
| `enabled` | `True` | 是否记录失败并执行阻断 |

不要把所有业务上的“未找到”都包装为错误。例如正常检索返回空集合，可以是成功回执；服务异常才适合错误回执。熔断按返回状态统计，无法自行区分业务原因。

```python
# 接续前例：读取各工具状态，供宿主展示或排查。
print(breaker.get_all_status())
# 恢复服务后可定向关闭某个工具的熔断，不影响其他名称。
breaker.close("lookup")
```

接入 Agent 时，把带熔断器的 `registry` 传入 `SimpleAgent`。模型收到错误后如何解释或改用其他工具，取决于任务与模型；宿主可继续使用最大轮数和调用预算限制整次运行。

## 状态与组合

当前实现只有开放与关闭两种状态，没有半开探测。`ERROR` 增加失败次数，`SUCCESS` 和 `PARTIAL` 都会清零连续失败数。`get_status(name)`、`get_all_status()` 可读取状态；直接读取状态不会触发冷却检查。

通过 `ToolRegistry(circuit_breaker=breaker)` 注入。同步、异步注册表入口都经过熔断；直接调用 `tool.run()` 不经过注册表。`registry.fork()` 与父注册表共享熔断器，同名工具的失败记录也会共享。

熔断状态保存在进程内，不是持久化任务状态。它不替代超时、重试策略、运行步数预算或授权检查，也不能撤回已经发生的工具副作用。

相关指南：[工具返回协议](tool-response-protocol.md)、[自定义工具](custom_tools_guide.md)。

## 常见问题

**为什么不同请求会影响同一个工具？**

计数键是工具名称。共用注册表或通过 `fork()` 创建的子表会共享同名工具状态。不同外部服务需要独立计数时，应注册成不同名称，或使用独立注册表和熔断器。

**等待后状态查询仍显示 open，为什么？**

状态读取不会触发恢复。下一次调用经过 `is_open()` 时才检查冷却是否结束；也可由宿主显式检查。不要把展示中的状态快照当作新一次调用的最终判断。

**是否会自动重试已经失败的请求？**

不会。重新请求由模型或宿主决定。尤其是写操作，错误可能发生在服务已经完成修改之后，需要先查明结果再重试。
