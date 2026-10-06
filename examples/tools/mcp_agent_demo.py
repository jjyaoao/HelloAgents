"""Native Agent Loop calling an actual MCP subprocess. Add --live for a model service."""

import asyncio
from pathlib import Path
import sys

from hello_agents import SimpleAgent, ToolRegistry
from hello_agents.tools import MCPConnection
from examples._support import demo_llm, tool_response, response


async def main():
    llm = demo_llm(
        [
            tool_response("travel_route_info", {"place": "museum"}),
            response("The museum route takes 25 minutes, with 1 km of walking."),
        ]
    )
    registry = ToolRegistry()
    server = Path(__file__).with_name("mcp_server.py")
    async with MCPConnection.stdio(
        sys.executable,
        ["-X", "utf8", str(server)],
        prefix="travel_",
        tools=["route_info"],
    ) as connection:
        connection.register_tools(registry)
        agent = SimpleAgent("travel", llm, tool_registry=registry)
        print(
            await agent.arun(
                "Use travel_route_info to check the museum route. Report minutes and walking distance."
            )
        )
        receipts = [m for m in agent._history if m.role == "tool"]
        assert receipts and "example-fixture" in receipts[0].content
    assert registry.list_tools() == []
    print("MCP tool receipt verified; connection closed and tools unregistered.")


if __name__ == "__main__":
    asyncio.run(main())
