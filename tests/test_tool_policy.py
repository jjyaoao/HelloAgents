import asyncio
import pytest

from hello_agents import SimpleAgent, ToolRegistry
from hello_agents.tools import AllowlistPolicy, PermissionDecision, CalculatorTool
from hello_agents.core.llm_response import LLMResponse


class MinimalLLM:
    model = "fixture"
    provider = "fixture"

    def invoke(self, messages, **kwargs):
        return LLMResponse("done", self.model)

    invoke_with_tools = invoke


def test_default_agent_is_a_minimal_loop(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tools = ToolRegistry()
    tools.register_tool(CalculatorTool())
    names = tools.list_tools()
    agent = SimpleAgent("minimal", MinimalLLM(), tool_registry=tools)
    assert agent.run("hello") == "done"
    assert tools.list_tools() == names
    assert agent.session_store is None and agent.skill_loader is None
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("asynchronous", [False, True])
def test_policy_covers_functions_forks_and_no_execution(asynchronous):
    calls = []
    registry = ToolRegistry(policy=AllowlistPolicy(["read"]))
    registry.register_function(lambda x: calls.append(x), name="write")
    child = registry.fork()
    if asynchronous:
        result = asyncio.run(child.aexecute_tool("write", "payload"))
    else:
        result = child.execute_tool("write", "payload")
    assert result.error_info["code"] == "PERMISSION_DENIED"
    assert calls == [] and not registry.circuit_breaker.is_open("write")


def test_policy_failure_is_closed_and_arguments_are_copied():
    def invalid(name, arguments):
        raise RuntimeError("broken")

    r = ToolRegistry(policy=invalid)
    r.register_tool(CalculatorTool())
    assert (
        r.execute_tool("calculator", {"expression": "2+3"}).error_info["code"]
        == "PERMISSION_DENIED"
    )

    def allow(name, arguments):
        arguments.clear()
        return PermissionDecision(True)

    r.policy = allow
    args = {"expression": "2+3"}
    r.execute_tool("calculator", args)
    assert args == {"expression": "2+3"}


@pytest.mark.asyncio
async def test_caller_cannot_change_authorized_payload_during_execution():
    entered, release = asyncio.Event(), asyncio.Event()
    seen = []

    async def remote_action(arguments):
        entered.set()
        await release.wait()
        seen.append(arguments["target"])

    registry = ToolRegistry(
        policy=lambda name, args: PermissionDecision(args["target"] == "safe")
    )
    registry.register_function(remote_action)
    payload = {"target": "safe"}
    task = asyncio.create_task(registry.aexecute_tool("remote_action", payload))
    await entered.wait()
    payload["target"] = "denied"
    release.set()
    await task
    assert seen == ["safe"]
