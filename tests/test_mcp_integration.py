import asyncio
from pathlib import Path
import socket
import subprocess
import sys

import pytest

pytest.importorskip("mcp")
pytest.importorskip("jsonschema")

from hello_agents import ToolRegistry
from hello_agents.tools import MCPConnection, AllowlistPolicy

SERVER = Path(__file__).resolve().parents[1] / "examples" / "tools" / "mcp_server.py"


@pytest.mark.asyncio
async def test_actual_stdio_schema_results_lifecycle_and_policy():
    r = ToolRegistry()
    connection = MCPConnection.stdio(sys.executable, [str(SERVER)], prefix="trip_")
    async with connection:
        assert connection.register_tools(r) == ("trip_route_info",)
        tool = r.get_tool("trip_route_info")
        assert (
            tool.to_openai_schema()["function"]["parameters"]["properties"]["place"][
                "type"
            ]
            == "string"
        )
        good = await r.aexecute_tool("trip_route_info", {"place": "museum"})
        assert good.data["mcp"]["structuredContent"]["minutes"] == 25
        bad = await r.aexecute_tool("trip_route_info", {"place": 5})
        assert bad.error_info["code"] == "INVALID_PARAM"
        remote_error = await r.aexecute_tool("trip_route_info", {"place": "missing"})
        assert remote_error.error_info["code"] == "EXECUTION_ERROR"
        r.policy = AllowlistPolicy([])
        assert (await r.aexecute_tool("trip_route_info", {"place": "lake"})).error_info[
            "code"
        ] == "PERMISSION_DENIED"
    assert r.list_tools() == []
    with pytest.raises(RuntimeError, match="closed"):
        await tool.arun({"place": "museum"})


@pytest.mark.asyncio
async def test_collision_and_host_replacement_survives_cleanup():
    r = ToolRegistry()
    r.register_function(lambda x: x, name="route_info")
    async with MCPConnection.stdio(sys.executable, [str(SERVER)]) as connection:
        with pytest.raises(ValueError, match="collision"):
            connection.register_tools(r)
        r.unregister("route_info")
        connection.register_tools(r)
        r.register_function(lambda x: x, name="route_info", replace=True)
    assert r.list_tools() == ["route_info"]


@pytest.mark.asyncio
async def test_reconnect_does_not_reactivate_old_fork_tools():
    r = ToolRegistry()
    c = MCPConnection.stdio(sys.executable, [str(SERVER)])
    async with c:
        c.register_tools(r)
        child = r.fork()
    c.allowed = frozenset()
    async with c:
        assert c.register_tools(r) == ()
        result = await child.aexecute_tool("route_info", {"place": "museum"})
        assert result.error_info["code"] == "INTERNAL_ERROR"
        assert "closed connection generation" in result.text
        assert not result.data.get("mcp")


@pytest.mark.asyncio
async def test_actual_streamable_http():
    pytest.importorskip("uvicorn")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, str(SERVER), "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(100):
            if process.poll() is not None:
                pytest.fail("MCP HTTP service exited before becoming ready")
            try:
                reader, writer = await asyncio.open_connection("127.0.0.1", port)
                writer.close()
                await writer.wait_closed()
                break
            except OSError:
                await asyncio.sleep(0.05)
        else:
            pytest.fail("MCP HTTP service did not start")
        async with MCPConnection(
            f"http://127.0.0.1:{port}/mcp", tools=["route_info"]
        ) as c:
            r = ToolRegistry()
            c.register_tools(r)
            result = await r.aexecute_tool("route_info", {"place": "lake"})
            assert result.data["mcp"]["structuredContent"]["walking_km"] == 4
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
