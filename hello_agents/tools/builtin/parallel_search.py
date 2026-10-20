"""Free Parallel Search MCP tools, using the optional official MCP SDK."""

import asyncio
from uuid import UUID, uuid4
from urllib.parse import urlsplit

from ..base import Tool, ToolParameter
from ..errors import ToolErrorCode
from ..response import ToolResponse

SEARCH_MCP_URL = "https://search.parallel.ai/mcp"
USER_AGENT = "HelloAgents/1.0.1 (+https://github.com/jjyaoao/HelloAgents)"


class ParallelWebTool(Tool):
    """One read-only tool; connections are scoped to a call, never a conversation.

    The agent supplies conversation identity separately at dispatch time. Direct
    registry calls are standalone research runs and receive their own UUID.
    """

    def __init__(self, *, fetch=False, timeout=30):
        self.fetch = fetch
        self.timeout = timeout
        super().__init__(
            "WebFetch" if fetch else "WebSearch",
            "Read relevant excerpts from HTTP/HTTPS pages using Parallel."
            if fetch
            else "Search the web using Parallel and return source URLs and excerpts.",
        )

    def get_parameters(self):
        if self.fetch:
            return [
                ToolParameter(
                    name="urls",
                    type="array",
                    description="1–20 HTTP/HTTPS URLs",
                    json_schema={
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 20,
                    },
                ),
                ToolParameter(
                    name="objective",
                    type="string",
                    description="What to extract (up to 200 characters)",
                    required=False,
                ),
            ]
        return [
            ToolParameter(
                name="objective",
                type="string",
                description="Specific information to find",
            ),
            ToolParameter(
                name="search_queries",
                type="array",
                description="Related concise search queries",
                json_schema={
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
            ),
        ]

    def run(self, parameters):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(parameters))
        raise RuntimeError("Use await registry.aexecute_tool inside an event loop")

    async def arun(self, parameters):
        arguments = {
            p.name: parameters[p.name]
            for p in self.get_parameters()
            if p.name in parameters
        }
        if self.fetch:
            urls = arguments.get("urls")
            if not isinstance(urls, list) or not 1 <= len(urls) <= 20:
                return ToolResponse.error(
                    ToolErrorCode.INVALID_PARAM, "Provide 1–20 HTTP/HTTPS URLs"
                )
            try:
                valid = all(
                    isinstance(url, str)
                    and urlsplit(url).scheme in {"http", "https"}
                    and urlsplit(url).hostname
                    for url in urls
                )
            except ValueError:
                valid = False
            if not valid:
                return ToolResponse.error(
                    ToolErrorCode.INVALID_PARAM,
                    "URLs must use HTTP or HTTPS and include a host",
                )
            objective = arguments.get("objective")
            if objective is not None and (
                not isinstance(objective, str) or len(objective) > 200
            ):
                return ToolResponse.error(
                    ToolErrorCode.INVALID_PARAM,
                    "Fetch objective must be at most 200 characters",
                )
        else:
            queries = arguments.get("search_queries")
            if (
                not isinstance(arguments.get("objective"), str)
                or not arguments["objective"].strip()
                or not isinstance(queries, list)
                or not queries
                or any(not isinstance(q, str) or not q.strip() for q in queries)
            ):
                return ToolResponse.error(
                    ToolErrorCode.INVALID_PARAM,
                    "Provide an objective and at least one search query",
                )
        try:
            import httpx2
            from mcp.client.streamable_http import streamable_http_client
            from ..mcp import MCPConnection
            from ..registry import ToolRegistry
        except ImportError as exc:
            raise ImportError(
                "Install hello-agents[mcp] to use Parallel web search"
            ) from exc

        try:
            session_id = str(UUID(parameters.get("_parallel_session_id")))
        except (ValueError, TypeError, AttributeError):
            session_id = str(uuid4())
        arguments["session_id"] = session_id
        remote_name = "web_fetch" if self.fetch else "web_search"
        # No credentials are loaded from the environment, and no provider fallback
        # or automatic retry masks an explicit failure.
        async with httpx2.AsyncClient(
            headers={"User-Agent": USER_AGENT}, timeout=self.timeout
        ) as http:
            transport = streamable_http_client(SEARCH_MCP_URL, http_client=http)
            async with MCPConnection(
                transport, tools=[remote_name], timeout=self.timeout
            ) as connection:
                registry = ToolRegistry()
                connection.register_tools(registry)
                return await registry.aexecute_tool(remote_name, arguments)
