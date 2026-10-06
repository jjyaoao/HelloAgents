# 自定义工具：声明、执行与组合

工具把一项可调用操作封装成名称、参数声明和执行结果。定义应描述操作本身；具体读取哪个文件、搜索什么主题，由用户任务或提示词提供。

## 目录

- [一个可运行工具](#一个可运行工具)
- [完整参数 Schema](#完整参数-schema)
- [函数与异步调用](#函数与异步调用)
- [把多个动作展开为工具](#把多个动作展开为工具)
- [注册与组合](#注册与组合)
- [接入 Agent 与验证](#接入-agent-与验证)

## 一个可运行工具

在源码根目录执行 `python -m pip install -r requirements.txt`。下面不需要密钥：

```python
from hello_agents.tools import Tool, ToolParameter, ToolRegistry, ToolResponse
from hello_agents.tools.errors import ToolErrorCode

class WordCountTool(Tool):
    def __init__(self):
        super().__init__("character_count", "统计给定文本中的字符数")

    def get_parameters(self):
        return [ToolParameter(name="text", type="string", description="待统计文本")]

    def run(self, parameters):
        text = parameters.get("text")
        if not isinstance(text, str):
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "text 必须是字符串")
        return ToolResponse.success("字符统计完成", data={"characters": len(text)})

registry = ToolRegistry()
registry.register_tool(WordCountTool())
result = registry.execute_tool("character_count", {"text": "杭州旅行"})
assert result.data["characters"] == 4
print(result.to_dict())
```

`run(dict)` 返回 `ToolResponse`。`text` 说明结果，`data` 保存可检查的载荷；错误说明应帮助调用者判断需要改参数、补资料还是停止操作。通过注册表执行可以应用计时、输入上下文和熔断规则；直接调用工具方法不会经过注册表熔断。

## 完整参数 Schema

`ToolParameter` 使用 `name`、`type`、`description`、`required`、`default` 和可选 `json_schema`。提供 `json_schema` 时，以该片段表达参数结构：

```python
from hello_agents.tools import ToolParameter

routes = ToolParameter(
    name="routes", type="array", description="要检查的路线列表",
    json_schema={
        "type": "array", "minItems": 1,
        "items": {
            "type": "object",
            "properties": {"mode": {"type": "string", "enum": ["walk", "transit"]}},
            "required": ["mode"], "additionalProperties": False,
        },
    },
)
assert routes.json_schema["items"]["required"] == ["mode"]
```

`Tool.to_openai_schema()` 是模型工具声明入口。需要跨字段约束时重写该方法，返回完整函数声明。手工片段中的 `$ref` 以整个 `parameters` 为根；跨参数定义宜集中在完整 Schema 中管理。声明生成错误会在注册时暴露。

Schema 描述允许的结构，不能代替业务检查。例如金额有效还需知道币种、范围、权限和重复执行后果。类型注解也不会自动把字典转成 Pydantic 实例。对象数组应明确声明 `items`，不要让模型猜测字段。

## 函数与异步调用

单输入函数可以直接注册；多参数使用 Tool 或 action。异步函数通过 `aexecute_tool()` 真正等待执行：

```python
import asyncio
from hello_agents.tools import ToolRegistry, ToolResponse

async def lookup(query):
    await asyncio.sleep(0)
    return ToolResponse.success("本地查询完成", data={"query": query})

async def main():
    registry = ToolRegistry()
    registry.register_function(lookup, name="lookup", description="查询指定条件；input 为条件")
    response = await registry.aexecute_tool("lookup", "杭州")
    assert response.data["query"] == "杭州"

asyncio.run(main())
```

函数工具向模型暴露一个 `input` 字符串参数。原生异步函数不能通过同步 `execute_tool()` 调用，该入口返回 `INVALID_PARAM`。异步注册表在线程中运行同步函数；无法强制取消已经进入线程的副作用。

自定义 Tool 重写 `arun()` 可接入异步客户端，`run()` 则提供同步实现或明确返回不支持的错误。两种入口都返回 ToolResponse，不把 coroutine 当作成功结果。调用方式和取消边界见[异步指南](async-agent-guide.md)。

## 把多个动作展开为工具

```python
import asyncio
from hello_agents.tools import Tool, ToolResponse, ToolRegistry, tool_action

class Totals(Tool):
    def __init__(self):
        super().__init__("totals", "数值列表操作", expandable=True)

    def get_parameters(self):
        return []

    def run(self, parameters):
        return ToolResponse.error("INVALID_PARAM", "请使用展开后的 totals_sum")

    @tool_action("totals_sum", "计算整数列表之和")
    async def total(self, values: list[int]):
        if not isinstance(values, list) or any(type(v) is not int for v in values):
            return ToolResponse.error("INVALID_PARAM", "values 必须是整数列表")
        await asyncio.sleep(0)
        return ToolResponse.success("求和完成", data={"sum": sum(values)})

async def main():
    registry = ToolRegistry()
    registry.register_tool(Totals())
    result = await registry.aexecute_tool("totals_sum", {"values": [2, 3]})
    assert result.data["sum"] == 5

asyncio.run(main())
```

默认注册会展开 `@tool_action`，从方法签名和类型注解生成声明，包括嵌套数组及其引用。`auto_expand=False` 注册父工具本身，此时父工具必须实现自己的有效分派逻辑。

## 注册与组合

Tool、函数和展开 action 共用名称空间。重复名称抛出 `ValueError`；确实需要替换时显式传 `replace=True`。展开注册先检查全部名称与声明，失败不留下半组工具。

`registry.fork(["rag_search", "rag_read"])` 创建独立的选定名称映射，函数也适用；省略参数复制全部，空列表得到空表，未知名称报错。名称映射、函数元数据和读取缓存独立，Tool/函数实例及熔断器共享。需要完整状态隔离时应创建独立工具实例和存储。

`unregister(name)` 删除名称。`get_tool(name)` 取得 Tool，`get_function(name)` 取得函数；`list_tools()` 包含两者，`get_all_tools()` 只返回 Tool 实例。不要用后者误判函数是否已注册。

## 接入 Agent 与验证

将注册表通过 `tool_registry=registry` 传给 Agent。任务要求写在 `agent.run(...)` 中；模型依据声明生成参数，运行器执行并回填。[Function Calling](function-calling-architecture.md)展示消息关联，[工具响应协议](tool-response-protocol.md)说明如何保留来源和失败状态。

完整示例：`python -X utf8 -m examples.agents.runtime_features --workspace workspace/runtime-demo`。测试：`python -m pytest tests/test_tool_contract_fixes.py`。应检查 Schema 是否包含真实字段、输入不合法时是否明确拒绝、异步操作是否等待完成，以及有副作用操作失败后的实际状态。
