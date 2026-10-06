from copy import deepcopy
from types import SimpleNamespace

import pytest

from hello_agents import Config
from hello_agents.core.agent import Agent
from hello_agents.core.budget import BudgetExceeded
from hello_agents.core.message import Message
from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.registry import ToolRegistry


class ProbeAgent(Agent):
    def run(self, input_text, **kwargs):
        self.add_message(Message(input_text, "user"))
        self._session_metadata["total_steps"] = 99
        self.last_run = SimpleNamespace(status="completed")
        self._messages_since_save = 19
        self._auto_save()
        return "child answer"


def agent():
    value = ProbeAgent("test", SimpleNamespace(model="test"), config=Config(
        trace_enabled=False, subagent_enabled=False, session_enabled=False,
        skills_enabled=False,
    ), tool_registry=ToolRegistry())
    value.add_message(Message("parent", "user"))
    value.max_steps = 8
    value.max_tool_iterations = 7
    value.last_run = SimpleNamespace(status="completed", answer="parent answer")
    value._messages_since_save = 3
    return value


@pytest.mark.parametrize("phase", ["summary", "metadata"])
def test_subagent_restores_parent_if_postprocessing_raises(phase):
    value = agent()
    original = (value.tool_registry, value.last_run, value._session_metadata)
    def fail(*args):
        raise RuntimeError("postprocessing failed")
    setattr(value, "_generate_subagent_summary" if phase == "summary" else "_get_subagent_metadata", fail)
    with pytest.raises(RuntimeError, match="postprocessing failed"):
        value.run_as_subagent("child", max_steps_override=2)
    assert [m.content for m in value.get_history()] == ["parent"]
    assert value.tool_registry is original[0] and value.last_run is original[1]
    assert value._session_metadata is original[2]
    assert value._session_metadata["total_steps"] == 0
    assert value._messages_since_save == 3
    assert (value.max_steps, value.max_tool_iterations) == (8, 7)


def test_subagent_does_not_overwrite_parent_autosave_or_tool_cache():
    value = agent()
    saved = []
    store = SimpleNamespace(save=lambda **kwargs: saved.append(deepcopy(kwargs)))
    value.session_store = store
    value.tool_registry.read_metadata_cache = {"parent": {"version": 1}}
    original_registry = value.tool_registry
    original_run = value.last_run
    def summary(*args):
        value.tool_registry.read_metadata_cache.clear()
        return "done"
    value._generate_subagent_summary = summary
    assert value.run_as_subagent("child")["success"]
    assert saved == []
    assert value.session_store is store and value.last_run is original_run
    assert value.tool_registry is original_registry
    assert value.tool_registry.read_metadata_cache == {"parent": {"version": 1}}


def test_subagent_restores_parent_on_keyboard_interrupt():
    value = agent()
    registry, last_run = value.tool_registry, value.last_run

    def cancel(*args, **kwargs):
        value.add_message(Message("unfinished child", "user"))
        raise KeyboardInterrupt()

    value.run = cancel
    with pytest.raises(KeyboardInterrupt):
        value.run_as_subagent("child", max_steps_override=1)
    assert [m.content for m in value.get_history()] == ["parent"]
    assert value.tool_registry is registry and value.last_run is last_run
    assert (value.max_steps, value.max_tool_iterations) == (8, 7)


@pytest.mark.parametrize("limit", [0, -1, True, "2"])
def test_subagent_rejects_invalid_budget_before_changing_state(limit):
    value = agent()
    with pytest.raises(ValueError, match="max_steps_override"):
        value.run_as_subagent("child", max_steps_override=limit)
    assert [m.content for m in value.get_history()] == ["parent"]


class ParameterTool(Tool):
    def __init__(self, parameter_type="string", required=True):
        super().__init__("query", "description " * 20)
        self.parameter_type = parameter_type
        self.required = required

    def get_parameters(self):
        return [ToolParameter(name="value", type=self.parameter_type,
                              description="query value", required=self.required)]

    def run(self, parameters):
        return parameters


def test_session_hash_covers_complete_tool_contract_and_functions():
    value = agent()
    tool = ParameterTool()
    value.tool_registry.register_tool(tool)
    baseline = value._compute_tool_schema_hash()
    tool.parameter_type = "integer"
    assert value._compute_tool_schema_hash() != baseline
    tool.parameter_type = "string"
    tool.required = False
    assert value._compute_tool_schema_hash() != baseline
    tool.required = True
    tool.description += " changed beyond character 100"
    assert value._compute_tool_schema_hash() != baseline
    before_function = value._compute_tool_schema_hash()
    value.tool_registry.register_function(lambda x: x, name="echo")
    assert value._compute_tool_schema_hash() != before_function


def test_session_hash_ignores_tool_registration_order():
    first, second = agent(), agent()
    for value, names in ((first, ("alpha", "beta")), (second, ("beta", "alpha"))):
        for name in names:
            tool = ParameterTool()
            tool.name = name
            value.tool_registry.register_tool(tool)
    assert first._compute_tool_schema_hash() == second._compute_tool_schema_hash()


def test_budget_exhaustion_is_not_downgraded_to_statistical_summary():
    value = agent()
    for _ in range(10):
        value.add_message(Message("next", "user"))
    def exhausted(*args, **kwargs):
        raise BudgetExceeded("task exhausted")
    value._get_summary_llm = lambda: SimpleNamespace(invoke=exhausted)
    with pytest.raises(BudgetExceeded):
        value._generate_smart_summary(value.get_history())
