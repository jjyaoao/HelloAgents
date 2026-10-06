# 工具响应协议

`ToolResponse` 将执行状态、可读说明和结构化数据一起返回。这样模型和应用可以区分完整结果、部分可用结果与错误，不必从一句字符串猜测执行是否成功。

## 目录

- [最小例子](#最小例子)
- [状态怎样选择](#状态怎样选择)
- [字段与序列化](#字段与序列化)
- [在工具与 Agent 中使用](#在工具与-agent-中使用)
- [错误码与边界](#错误码与边界)

## 最小例子

在源码根目录安装 `python -m pip install -r requirements.txt` 后执行，无需密钥：

```python
from hello_agents.tools import ToolResponse
from hello_agents.tools.response import ToolStatus
from hello_agents.tools.errors import ToolErrorCode

found = ToolResponse.success("取得两条资料", data={"sources": ["doc:a", "doc:b"]})
partial = ToolResponse.partial("一条来源不可用", data={"sources": ["doc:a"], "missing": ["doc:b"]})
failed = ToolResponse.error(ToolErrorCode.NOT_FOUND, "没有找到请求的资料")
assert found.status == ToolStatus.SUCCESS
assert partial.to_dict()["status"] == "partial"
assert failed.error_info["code"] == "NOT_FOUND"
assert ToolResponse.from_json(found.to_json()).data == found.data
print(found.to_model_text())
```

输出保留资料标识；部分结果说明缺失项。应用可以继续处理已有资料，也可以要求补查，不能将部分结果当成完整覆盖。

## 状态怎样选择

- `success`：本次工具操作按约定成功。查询返回零条也可成功，前提是查询本身完成。
- `partial`：有可用结果，但存在截断、部分失败或其他限制，应说明限制。
- `error`：没有符合约定的有效结果，通过错误码和说明给出后续判断依据。

这些状态描述一次工具操作，不表示整个任务成功；Agent 的结束状态见[运行指南](runtime-guide.md)。

## 字段与序列化

`status` 是 ToolStatus 枚举；`text` 是给模型和用户阅读的说明；`data` 是结构化载荷。`stats` 可记录耗时等统计，`context` 可记录必要的输入和环境信息，`error_info` 保存错误码与消息。

`to_dict()` 和 `to_json()` 输出可序列化字段，其中错误字段名为 `error`。`from_dict()`、`from_json()` 恢复响应对象。`to_model_text()` 在有 `data` 时保留完整 JSON；没有结构化载荷时，错误和部分结果带状态说明，普通成功返回文本。

资料工具应在 `data` 保留来源、版本与原文标识，不能只写“搜索成功”。输入和统计也可能进入模型或日志，不应放入密钥及无关个人信息。

## 在工具与 Agent 中使用

`Tool.run(parameters)` 返回 ToolResponse；`run_with_timing()` 补充耗时、输入参数和工具名称。异步实现对应 `arun()` 与 `arun_with_timing()`。通过 `ToolRegistry.execute_tool()` 或 `aexecute_tool()` 执行会进一步应用熔断规则。

```python
from hello_agents.tools import ToolRegistry, ToolResponse

registry = ToolRegistry()
def read_fixture(query):
    return ToolResponse.partial("教学资料只覆盖一个区域", data={"query": query, "source": "fixture://region"})
registry.register_function(read_fixture)
result = registry.execute_tool("read_fixture", "交通")
assert result.to_dict()["status"] == "partial"
assert result.data["source"] == "fixture://region"
```

注册表保留函数返回的 ToolResponse，不将错误或部分结果重包装为成功。Agent 使用模型可读表示回填，并按输出预算截断过长结果；完整输出位置由截断器提供。

## 错误码与边界

常用错误码为 `INVALID_PARAM`、`INVALID_FORMAT`、`NOT_FOUND`、`ACCESS_DENIED`、`PERMISSION_DENIED`、`CONFLICT`、`EXECUTION_ERROR`、`TIMEOUT`、`INTERNAL_ERROR`、`CIRCUIT_OPEN`、`NETWORK_ERROR`、`API_ERROR` 和 `RATE_LIMIT`。可通过 `ToolErrorCode.get_all_codes()` 查看定义。

`ToolResponse.error(code, message, stats=None, context=None)` 不接收 `data`；需要返回部分有效数据时应选择 `partial`，并明确哪些部分可信。错误码是操作语义，不证明外部副作用已撤销。中断而未取得回执的请求由运行器标为未知，不能据此自动重复写入。

更多示例见[自定义工具](custom_tools_guide.md)、[熔断器](circuit-breaker-guide.md)和[文件操作](file_tools.md)。
