"""可选的官方 MCP SDK 桥接层，连接生命周期由调用方的异步作用域管理。"""

import asyncio
from copy import deepcopy
import re
from typing import Optional, Sequence

from .base import Tool
from .response import ToolResponse
from .errors import ToolErrorCode


class MCPTool(Tool):
    def __init__(self, connection, definition, name):
        self.connection = connection
        self.generation = connection._generation
        self.remote_name = definition["name"]
        self.input_schema = deepcopy(definition["inputSchema"])
        from jsonschema import Draft202012Validator

        def check_refs(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in {"$ref", "$dynamicRef"} and not str(item).startswith("#"):
                        raise ValueError("MCP tool schemas must use local references")
                    check_refs(item)
            elif isinstance(value, list):
                for item in value:
                    check_refs(item)

        check_refs(self.input_schema)
        Draft202012Validator.check_schema(self.input_schema)
        self.validator = Draft202012Validator(self.input_schema)
        super().__init__(name, definition.get("description") or self.remote_name)

    def get_parameters(self):
        return []  # 保留协商得到的嵌套 JSON Schema，不将其展开为扁平结构。

    def to_openai_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": deepcopy(self.input_schema),
            },
        }

    def run(self, parameters):
        raise RuntimeError(
            "MCP tools require await agent.arun / registry.aexecute_tool within async with"
        )

    async def arun(self, parameters):
        self.connection._check_open()
        if self.generation is not self.connection._generation:
            raise RuntimeError("MCP tool belongs to a closed connection generation")
        if not isinstance(parameters, dict) or not self.validator.is_valid(parameters):
            return ToolResponse.error(
                ToolErrorCode.INVALID_PARAM,
                "Arguments do not match the MCP tool schema",
            )
        # 不自动重试远端写入操作：操作可能已提交，只是响应超时。
        result = await self.connection.client.call_tool(self.remote_name, parameters)
        raw = result.model_dump(mode="json", by_alias=True, exclude_none=True)
        text = "\n".join(
            block["text"]
            for block in raw.get("content", [])
            if block.get("type") == "text"
        )
        if raw.get("isError"):
            response = ToolResponse.error(
                ToolErrorCode.EXECUTION_ERROR, text or "MCP tool failed"
            )
            response.data = {"mcp": raw}
            return response
        return ToolResponse.success(
            text or "MCP tool returned content", data={"mcp": raw}
        )


class MCPConnection:
    """在与 Agent 相同的事件循环中使用 ``async with``。

    ``server`` 接受 SDK 传输对象、StdioServerParameters 或 Streamable HTTP
    URL。SDK 传输对象允许显式配置身份认证。本桥接层
    只导出工具；资源与提示词仍可通过 ``client`` 访问。
    """

    def __init__(
        self,
        server,
        *,
        prefix: str = "",
        timeout: float = 30,
        tools: Optional[Sequence[str]] = None,
    ):
        if not isinstance(prefix, str) or (
            prefix and not re.fullmatch(r"[A-Za-z0-9_-]+", prefix)
        ):
            raise ValueError(
                "prefix must contain letters, digits, underscores or hyphens"
            )
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not 0 < timeout < float("inf")
        ):
            raise ValueError("timeout must be positive and finite")
        if tools is not None and (
            isinstance(tools, str)
            or any(not isinstance(t, str) or not t for t in tools)
        ):
            raise ValueError("tools must be a sequence of remote tool names")
        self.server, self.prefix, self.timeout = server, prefix, timeout
        self.allowed = frozenset(tools) if tools is not None else None
        self.client = None
        self._generation = None
        self._loop = None
        self._catalog = []
        self._registrations = []

    @classmethod
    def stdio(
        cls, command: str, args: Sequence[str] = (), *, env=None, cwd=None, **kwargs
    ):
        try:
            from mcp import StdioServerParameters
        except ImportError as exc:
            raise ImportError("Install hello-agents[mcp] to use MCP") from exc
        return cls(
            StdioServerParameters(command=command, args=list(args), env=env, cwd=cwd),
            **kwargs,
        )

    def _check_open(self):
        if self.client is None or self._loop is not asyncio.get_running_loop():
            raise RuntimeError(
                "MCP connection is closed or belongs to another event loop"
            )

    async def __aenter__(self):
        if self.client is not None:
            raise RuntimeError("MCP connection is already open")
        try:
            from mcp import Client
            import jsonschema  # 在建立远端连接前完成校验，无效时立即报错。
        except ImportError as exc:
            raise ImportError("Install hello-agents[mcp] to use MCP") from exc
        client = Client(self.server, read_timeout_seconds=self.timeout)
        await client.__aenter__()
        self.client, self._loop = client, asyncio.get_running_loop()
        self._generation = object()
        try:
            cursor, seen = None, set()
            definitions = []
            while True:
                result = await client.list_tools(cursor=cursor)
                page = result.model_dump(mode="json", by_alias=True)
                definitions.extend(page["tools"])
                cursor = page.get("nextCursor")
                if not cursor:
                    break
                if cursor in seen:
                    raise ValueError("MCP server repeated its pagination cursor")
                seen.add(cursor)
            names = [d["name"] for d in definitions]
            if len(set(names)) != len(names):
                raise ValueError("MCP server advertised duplicate tools")
            if self.allowed is not None and not self.allowed.issubset(names):
                raise ValueError(
                    "Requested MCP tools are missing from the server catalog"
                )
            self._catalog = []
            for definition in definitions:
                if self.allowed is not None and definition["name"] not in self.allowed:
                    continue
                name = self.prefix + definition["name"]
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name):
                    raise ValueError(
                        "Exported MCP tool name must match [A-Za-z0-9_-]{1,64}"
                    )
                self._catalog.append(MCPTool(self, definition, name))
            return self
        except BaseException:
            await self.__aexit__(None, None, None)
            raise

    def register_tools(self, registry):
        self._check_open()
        if set(registry.list_tools()) & {t.name for t in self._catalog}:
            raise ValueError("MCP tool name collision; use a distinct prefix")
        for tool in self._catalog:
            registry.register_tool(tool)
            self._registrations.append((registry, tool))
        return tuple(t.name for t in self._catalog)

    async def __aexit__(self, exc_type, exc, tb):
        self._check_open()
        for registry, tool in self._registrations:
            # 连接清理时，必须保留宿主后来替换注册的工具。
            if registry.get_tool(tool.name) is tool:
                registry.unregister(tool.name)
        self._registrations.clear()
        client, self.client = self.client, None
        self._loop, self._catalog = None, []
        self._generation = None
        return await client.__aexit__(exc_type, exc, tb)
