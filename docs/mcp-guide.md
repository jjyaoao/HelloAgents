# MCP 工具接入指南

`MCPConnection` 使用官方 Python SDK 连接 MCP 服务，将发现的工具注册进 `ToolRegistry`。模型仍通过原生 Function Calling 发出请求；运行程序把请求交给 MCP 服务，并把回执放回 Agent Loop。

## 📚 目录

- [快速开始](#快速开始)
- [先独立调用，再接入模型](#先独立调用再接入模型)
- [HTTP 与认证](#http-与认证)
- [生命周期与错误](#生命周期与错误)
- [完整示例与验证](#完整示例与验证)
- [常见问题](#常见问题)

## 快速开始

在源码根目录安装可选依赖：

```bash
python -m pip install -r requirements/mcp.txt
python -X utf8 -m examples.tools.mcp_agent_demo
```

下面接入真实模型；先配置应用 `.env` 中的三个 `LLM_*` 字段。无需模型的独立工具调用见下一节。

```python
import asyncio
import sys
from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM, SimpleAgent, ToolRegistry
from hello_agents.tools import MCPConnection

async def main():
    load_dotenv()
    registry = ToolRegistry()
    async with MCPConnection.stdio(
        sys.executable, ["-m", "examples.tools.mcp_server"],
        prefix="travel_", tools=["route_info"], timeout=30,
    ) as connection:
        connection.register_tools(registry)
        async with HelloAgentsLLM() as llm:
            agent = SimpleAgent("旅行助手", llm, tool_registry=registry)
            print(await agent.arun("调用 travel_route_info 查询 museum 的交通时间和步行距离"))

asyncio.run(main())
```

`tools` 是允许暴露的远程工具名；不传时暴露服务目录中的全部工具。`prefix` 区分不同服务的同名工具。未知允许项、重复目录项和注册表名称冲突会明确失败。连接关闭后，只注销它注册且尚未被宿主替换的工具。

## 先独立调用，再接入模型

排查 MCP 接入时，先确认服务器启动、工具发现和实际调用都正常，再让模型决定调用哪一个工具。下面是完整的本地调用，不需要模型密钥。从仓库根目录执行，使子进程能找到 `examples.tools.mcp_server`。

```python
import asyncio
import sys
from hello_agents import ToolRegistry
from hello_agents.tools import MCPConnection
from hello_agents.tools.response import ToolStatus

async def main():
    registry = ToolRegistry()
    async with MCPConnection.stdio(
        sys.executable, ["-m", "examples.tools.mcp_server"],
        prefix="travel_", tools=["route_info"], timeout=30,
    ) as connection:
        connection.register_tools(registry)
        assert "travel_route_info" in registry.list_tools()
        result = await registry.aexecute_tool(
            "travel_route_info", {"place": "museum"},
        )
        assert result.status == ToolStatus.SUCCESS
        print(result.to_dict())
    assert "travel_route_info" not in registry.list_tools()

asyncio.run(main())
```

结果中的 `data.mcp` 保留服务器回执。这个例子实际启动子进程并通过 MCP 交换消息，路线数据由示例服务器提供。退出 `async with` 后，连接关闭，其工具也从注册表移除。

接入 Agent 时，仍使用同一个注册表，在连接内部调用 `await agent.arun(...)`。真实模型先读取带 `travel_` 前缀的工具定义，再返回参数；注册表负责校验和转发。初始化模型前使用 `load_dotenv()` 读取应用配置，退出时调用 `await llm.aclose()`，或用 `async with HelloAgentsLLM() as llm` 管理模型客户端。

### 连接参数怎样选

| 参数 | 用途 | 示例 |
| --- | --- | --- |
| `command` / `args` | 启动本地服务进程 | `sys.executable` 与 Python 模块参数 |
| `tools` | 选择需要暴露的原始工具名 | `["route_info"]` |
| `prefix` | 为注册名称增加前缀 | `travel_route_info` |
| `timeout` | 配置 MCP 读取等待时间 | `30` 秒 |

远程服务自身的名称不因 `prefix` 改变；调用注册表时使用带前缀的名称。为不同服务分配不同前缀，能避免重名，也方便制定权限策略。

## HTTP 与认证

```python
async with MCPConnection("http://127.0.0.1:8000/mcp", prefix="travel_") as connection:
    connection.register_tools(registry)
    # 在这个 async with 内 await agent.arun(...)
```

地址使用 Streamable HTTP。需要请求头、OAuth 或其他连接配置时，先按[官方 SDK](https://github.com/modelcontextprotocol/python-sdk)创建 Transport，再作为 `MCPConnection(transport)` 的参数传入。密钥应来自环境或宿主认证配置，不能写入工具描述。

## 生命周期与错误

连接与调用必须在同一事件循环内；采用 `await agent.arun()`，不要在连接内部调用同步 `agent.run()`。应用管理连接生命周期，不要把短暂 `async with` 里取得的工具带到外面使用。取消或异常会退出连接；服务器已执行的副作用不能仅凭本地取消撤销。

工具定义保留完整嵌套 JSON Schema，在本地检查输入。外部 `$ref` 不会被自动下载；使用本地引用。回执中的文本、`structuredContent` 和其他内容块原样保存在 `ToolResponse.data["mcp"]`。当前模型消息链路以文本和 JSON 传递这些内容，不承诺把图像块自动转换成多模态模型输入。

服务返回 `isError` 时映射为 `EXECUTION_ERROR`；本地参数不符为 `INVALID_PARAM`。连接异常交由注册表转成错误回执，超时和取消由运行器处理。适配器不自动重试远程操作：回复丢失时，服务端可能已经完成修改。

桥接层目前导出 MCP 工具。资源和提示模板可通过 `connection.client` 的官方 API 使用，尚未自动注入 Agent。工具注解如 `readOnlyHint` 是服务声明，不是权限保证；需要执行约束时使用[宿主工具权限策略](tool-policy-guide.md)。

## 完整示例与验证

```bash
python -X utf8 -m examples.tools.mcp_agent_demo --live
python -m pip install -r requirements/mcp.txt -r requirements/test.txt -r requirements/web.txt
python -m pytest tests/test_mcp_integration.py
```

示例使用真实 stdio 子进程与工具回执；旅行交通数据明确为示例数据。`--live` 将预设模型换成环境配置的真实服务。测试还会启动本地 Streamable HTTP 服务，核对 Schema、结构化结果、远程错误、权限拒绝与连接清理。

## 常见问题

**为什么能看到工具，但调用失败？**

先在连接尚未关闭时直接执行上面的 `aexecute_tool`。若直接调用失败，检查服务器日志、参数 Schema 和回执；若直接调用成功而 Agent 失败，再检查模型返回的工具名和参数。两条路径使用同一个注册表，可据此定位问题发生在哪一层。

**可以把服务器改成 HTTP，而不改 Agent 吗？**

可以。替换连接创建方式，重新注册工具；Agent 仍然使用 ToolRegistry。服务端的工具名称、参数和返回约定也需要一致，仅替换地址不保证业务接口相同。

**连接中断后怎样重连？**

由宿主退出旧连接，再创建新连接并重新发现工具。不要保留已经关闭的工具对象。只读查询通常可以重新发起；修改操作应先确认结果或使用服务端幂等机制。
