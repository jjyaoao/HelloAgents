"""Local MCP service for examples/tests; prices are explicit fixture data."""

import argparse
from typing import Any
from mcp.server import MCPServer

server = MCPServer("Travel fixture")


@server.tool(structured_output=True)
def route_info(place: str) -> dict[str, Any]:
    """Return transport information for a destination in the example dataset."""
    routes = {
        "museum": {"minutes": 25, "walking_km": 1},
        "lake": {"minutes": 40, "walking_km": 4},
    }
    if place not in routes:
        raise ValueError("Unknown destination")
    return {"place": place, **routes[place], "source": "example-fixture"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    if args.port:
        server.run("streamable-http", host="127.0.0.1", port=args.port)
    else:
        server.run("stdio")
