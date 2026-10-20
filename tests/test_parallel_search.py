"""Scripted models exercise the real resolver, MCP SDK and result consumer."""

import asyncio
from copy import deepcopy
import json
from uuid import UUID

import pytest

httpx2 = pytest.importorskip("httpx2")
pytest.importorskip("mcp")

from hello_agents import ReActAgent, SimpleAgent, ToolRegistry
from hello_agents.core.config import Config
from hello_agents.core.llm_response import LLMToolResponse, ToolCall
from hello_agents.tools import AllowlistPolicy
from hello_agents.tools.builtin import parallel_search


class ScriptedModel:
    model = "offline"

    def __init__(self, calls):
        self.calls = iter(calls)
        self.messages = []
        self.schemas = []

    async def ainvoke_with_tools(self, messages, tools, **kwargs):
        self.messages.append(deepcopy(messages))
        self.schemas.append(deepcopy(tools))
        call = next(self.calls)
        return LLMToolResponse(
            "" if call else "Found https://example.org/source",
            [call] if call else [],
            self.model,
        )


def search(call_id="search"):
    return ToolCall(
        call_id,
        "WebSearch",
        json.dumps(
            {"objective": "Find a source", "search_queries": ["example source"]}
        ),
    )


def fetch():
    return ToolCall("fetch", "WebFetch", '{"urls":["https://example.org/source"]}')


@pytest.fixture
def mcp_http(monkeypatch):
    requests = []
    state = {"error": False, "delay": 0, "started": asyncio.Event(), "cancelled": False}
    original = httpx2.AsyncClient

    async def handler(request):
        assert str(request.url) == parallel_search.SEARCH_MCP_URL
        assert request.headers["user-agent"] == parallel_search.USER_AGENT
        assert "authorization" not in request.headers
        if request.method != "POST":
            return httpx2.Response(404)
        packet = json.loads(request.content)
        requests.append(packet)
        method = packet.get("method")
        if "id" not in packet:
            return httpx2.Response(202)
        if method == "initialize":
            result = {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fixture", "version": "1"},
            }
        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "web_search",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "objective": {"type": "string"},
                                "search_queries": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "session_id": {"type": "string"},
                            },
                            "required": ["objective", "search_queries"],
                        },
                    },
                    {
                        "name": "web_fetch",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "urls": {"type": "array", "items": {"type": "string"}},
                                "session_id": {"type": "string"},
                            },
                            "required": ["urls"],
                        },
                    },
                ]
            }
        elif method == "tools/call":
            state["started"].set()
            try:
                await asyncio.sleep(state["delay"])
            except asyncio.CancelledError:
                state["cancelled"] = True
                raise
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": "quota exceeded"
                        if state["error"]
                        else "Evidence at https://example.org/source",
                    }
                ],
                "isError": state["error"],
            }
        else:
            return httpx2.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": packet["id"],
                    "error": {"code": -32601, "message": "Method not found"},
                },
            )
        return httpx2.Response(
            200, json={"jsonrpc": "2.0", "id": packet["id"], "result": result}
        )

    def client(*args, **kwargs):
        return original(*args, transport=httpx2.MockTransport(handler), **kwargs)

    monkeypatch.setattr(httpx2, "AsyncClient", client)
    for key in ("PARALLEL_API_KEY", "TAVILY_API_KEY", "SERPAPI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    return requests, state


def outgoing(requests):
    return [p["params"] for p in requests if p.get("method") == "tools/call"]


@pytest.mark.asyncio
async def test_default_react_search_fetch_followup_and_reset(mcp_http):
    requests, _ = mcp_http
    model = ScriptedModel(
        [search(), fetch(), None, search("followup"), None, search("new"), None]
    )
    agent = ReActAgent("research", model)
    assert set(agent.tool_registry.list_tools()) == {"WebSearch", "WebFetch"}
    await agent.arun("Research")
    await agent.arun("Follow up")
    calls = outgoing(requests)
    assert [c["name"] for c in calls] == ["web_search", "web_fetch", "web_search"]
    ids = {c["arguments"]["session_id"] for c in calls}
    assert len(ids) == 1
    UUID(next(iter(ids)))
    assert "https://example.org/source" in model.messages[1][-1]["content"]
    assert "session_id" not in json.dumps(model.schemas)
    agent.clear_history()
    await agent.arun("New chat")
    assert outgoing(requests)[-1]["arguments"]["session_id"] not in ids


@pytest.mark.asyncio
async def test_shared_registry_concurrent_agents_keep_conversation_identity(mcp_http):
    requests, _ = mcp_http
    first = ReActAgent("first", ScriptedModel([search(), fetch(), None]))
    second = ReActAgent(
        "second",
        ScriptedModel([search(), fetch(), None]),
        tool_registry=first.tool_registry,
    )
    await asyncio.gather(first.arun("one"), second.arun("two"))
    calls = outgoing(requests)
    by_name = {
        name: {c["arguments"]["session_id"] for c in calls if c["name"] == name}
        for name in ("web_search", "web_fetch")
    }
    assert len(by_name["web_search"]) == 2
    assert by_name["web_search"] == by_name["web_fetch"]


@pytest.mark.asyncio
async def test_explicit_registry_disabled_and_permission(mcp_http):
    requests, _ = mcp_http
    explicit = ToolRegistry()
    explicit.register_function(lambda value: value, name="chosen_search")
    assert ReActAgent(
        "custom", ScriptedModel([]), tool_registry=explicit
    ).tool_registry.list_tools() == ["chosen_search"]
    empty = ToolRegistry()
    assert (
        ReActAgent(
            "empty", ScriptedModel([]), tool_registry=empty
        ).tool_registry.list_tools()
        == []
    )
    assert (
        ReActAgent(
            "off", ScriptedModel([]), config=Config(web_search_enabled=False)
        ).tool_registry.list_tools()
        == []
    )
    assert SimpleAgent("chat", ScriptedModel([])).tool_registry is None
    agent = ReActAgent("denied", ScriptedModel([search(), None]))
    agent.tool_registry.policy = AllowlistPolicy([])
    await agent.arun("Search")
    assert "PERMISSION_DENIED" in agent.llm.messages[-1][-1]["content"]
    assert not requests


@pytest.mark.asyncio
async def test_remote_error_retry_and_bad_urls(mcp_http):
    requests, state = mcp_http
    agent = ReActAgent("error", ScriptedModel([search(), None, search("retry"), None]))
    state["error"] = True
    await agent.arun("search")
    assert "quota exceeded" in agent.llm.messages[-1][-1]["content"]
    state["error"] = False
    await agent.arun("retry")
    calls = outgoing(requests)
    assert len(calls) == 2
    assert calls[0]["arguments"]["session_id"] == calls[1]["arguments"]["session_id"]
    for urls in (
        ["file:///etc/passwd"],
        ["https:///missing"],
        [],
        ["https://[invalid"],
    ):
        agent.tool_registry.circuit_breaker.close("WebFetch")
        result = await agent.tool_registry.aexecute_tool("WebFetch", {"urls": urls})
        assert result.error_info["code"] == "INVALID_PARAM"
    assert len(outgoing(requests)) == 2


@pytest.mark.asyncio
async def test_timeout_and_cancellation_close_actual_transport(mcp_http):
    requests, state = mcp_http
    state["delay"] = 30
    agent = ReActAgent(
        "timeout",
        ScriptedModel([search(), None]),
        config=Config(tool_async_timeout=2),
    )
    with pytest.raises(TimeoutError):
        await agent.arun("Search")
    assert state["cancelled"]
    state["started"].clear()
    state["cancelled"] = False
    agent.config.tool_async_timeout = 60
    agent.llm = ScriptedModel([search(), None])
    task = asyncio.create_task(agent.arun("Again"))
    await asyncio.wait_for(state["started"].wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert state["cancelled"]
    assert len(outgoing(requests)) == 2


@pytest.mark.asyncio
async def test_saved_conversation_identity_survives_reload(mcp_http, tmp_path):
    requests, _ = mcp_http
    cfg = Config(session_enabled=True, session_dir=str(tmp_path))
    agent = ReActAgent("saved", ScriptedModel([search(), None]), config=cfg)
    await agent.arun("First")
    snapshot = agent.save_session("research")
    restored = ReActAgent("saved", ScriptedModel([fetch(), None]), config=cfg)
    restored.load_session(snapshot)
    await restored.arun("Continue")
    calls = outgoing(requests)
    assert calls[0]["arguments"]["session_id"] == calls[1]["arguments"]["session_id"]


@pytest.mark.asyncio
async def test_model_cannot_choose_conversation_identity(mcp_http):
    requests, _ = mcp_http
    call = search()
    args = json.loads(call.arguments)
    args["_parallel_session_id"] = "user@example.org"
    call = ToolCall(call.id, call.name, json.dumps(args))
    agent = ReActAgent("identity", ScriptedModel([call, None]))
    await agent.arun("Search")
    identity = outgoing(requests)[0]["arguments"]["session_id"]
    assert identity == agent._session_metadata["parallel_search_session_id"]
    UUID(identity)


@pytest.mark.asyncio
async def test_isolated_subagent_runs_restore_parent_search_identity(mcp_http):
    requests, _ = mcp_http
    model = ScriptedModel(
        [
            search(),
            None,
            search("child1"),
            fetch(),
            None,
            search("child2"),
            None,
            search("parent-followup"),
            None,
        ]
    )
    agent = ReActAgent("parent", model)
    await agent.arun("Parent research")
    first = await asyncio.to_thread(
        agent.run_as_subagent, "Child one", return_summary=False
    )
    second = await asyncio.to_thread(
        agent.run_as_subagent, "Child two", return_summary=False
    )
    assert first["success"] and second["success"]
    await agent.arun("Parent follow-up")
    identities = [c["arguments"]["session_id"] for c in outgoing(requests)]
    assert identities[0] == identities[4]
    assert identities[1] == identities[2]
    assert len({identities[0], identities[1], identities[3]}) == 3


def test_direct_sync_registry_call_is_standalone_research(mcp_http):
    requests, _ = mcp_http
    registry = ToolRegistry()
    registry.register_tool(parallel_search.ParallelWebTool())
    args = {"objective": "Find a source", "search_queries": ["example source"]}
    assert registry.execute_tool("WebSearch", args).status.value == "success"
    assert registry.execute_tool("WebSearch", args).status.value == "success"
    calls = outgoing(requests)
    assert calls[0]["arguments"]["session_id"] != calls[1]["arguments"]["session_id"]


@pytest.mark.asyncio
async def test_invalid_search_and_fetch_objective_never_send_requests(mcp_http):
    requests, _ = mcp_http
    search_tool = parallel_search.ParallelWebTool()
    fetch_tool = parallel_search.ParallelWebTool(fetch=True)
    bad_search = await search_tool.arun(
        {"objective": "Find a source", "search_queries": []}
    )
    bad_fetch = await fetch_tool.arun(
        {"urls": ["https://example.org"], "objective": "x" * 201}
    )
    assert (
        bad_search.error_info["code"] == bad_fetch.error_info["code"] == "INVALID_PARAM"
    )
    assert not requests


@pytest.mark.asyncio
async def test_missing_optional_sdk_reports_documented_installation_hint(monkeypatch):
    import sys

    monkeypatch.setitem(sys.modules, "mcp.client.streamable_http", None)
    agent = ReActAgent("minimal", ScriptedModel([search(), None]))
    await agent.arun("Search")
    assert "Install hello-agents[mcp]" in agent.llm.messages[-1][-1]["content"]
