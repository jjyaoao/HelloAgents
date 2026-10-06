"""Stateful failures that a successful single-turn test cannot expose."""

import asyncio
import json
from copy import deepcopy
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from hello_agents import SimpleAgent, ReActAgent, ReflectionAgent, PlanSolveAgent
from hello_agents.core.config import Config
from hello_agents.core.components import AgentComponents
from hello_agents.core.session_store import SessionStore
from hello_agents.core.message import Message
from hello_agents.core.llm_response import LLMToolResponse, ToolCall
from hello_agents.core.streaming import StreamEventType
from hello_agents.core.runtime import deadline
from hello_agents.tools import ToolRegistry


def config(**kwargs):
    return Config(
        **dict(
            trace_enabled=False,
            session_enabled=False,
            skills_enabled=False,
            subagent_enabled=False,
            todowrite_enabled=False,
            devlog_enabled=False,
            **kwargs,
        )
    )


class ScriptedLLM:
    model = "offline"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.messages = []

    def invoke(self, messages, **kwargs):
        self.messages.append(deepcopy(messages))
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return result

    def invoke_with_tools(self, messages, tools, **kwargs):
        return self.invoke(messages, **kwargs)

    async def astream_invoke_with_tools(self, messages, tools, **kwargs):
        result = self.invoke(messages, **kwargs)
        if result.content:
            yield result.content
        yield result


def response(text="", calls=(), reason="stop"):
    return LLMToolResponse(text, list(calls), "offline", finish_reason=reason)


def save(store, name="session", history=(), metadata=None):
    return store.save({}, list(history), "hash", {}, metadata or {}, name)


def test_session_save_preserves_unrelated_temp_file(tmp_path):
    store = SessionStore(str(tmp_path))
    other = tmp_path / "session.json.tmp"
    other.write_text("user data", encoding="utf8")
    save(store)
    assert other.read_text(encoding="utf8") == "user data"


def test_failed_session_serialization_leaves_no_partial_file(tmp_path):
    store = SessionStore(str(tmp_path))
    target = Path(save(store))
    original = target.read_bytes()
    with pytest.raises(TypeError):
        save(store, metadata={"bad": object()})
    assert target.read_bytes() == original
    assert list(tmp_path.glob("*.tmp")) == []


@pytest.mark.parametrize("name", ["../elsewhere", "nested/file", r"nested\file"])
def test_session_name_is_a_name_not_a_path(tmp_path, name):
    with pytest.raises(ValueError):
        save(SessionStore(str(tmp_path)), name)


def test_bad_restored_message_preserves_current_history(tmp_path):
    store = SessionStore(str(tmp_path))
    agent = SimpleAgent(
        "test",
        ScriptedLLM([]),
        config=config(),
        components=AgentComponents(session_store=store),
    )
    agent.add_message(Message("original", "user"))
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(
            {
                "history": [
                    {"role": "user", "content": "new"},
                    {"role": "invalid", "content": "broken"},
                ]
            }
        ),
        encoding="utf8",
    )
    with pytest.raises(ValueError):
        agent.load_session(str(path), check_consistency=False)
    assert [m.content for m in agent.get_history()] == ["original"]


def test_restore_empty_cache_removes_previous_session_cache(tmp_path):
    store = SessionStore(str(tmp_path))
    registry = ToolRegistry()
    registry.cache_read_metadata("old", {"version": 1})
    agent = SimpleAgent(
        "test",
        ScriptedLLM([]),
        config=config(),
        tool_registry=registry,
        components=AgentComponents(session_store=store),
    )
    agent.load_session(save(store), check_consistency=False)
    assert registry.read_metadata_cache == {}


def test_parallel_malformed_arguments_are_observations_not_crashes():
    registry = ToolRegistry()
    registry.register_function(lambda x: x, name="echo")
    llm = ScriptedLLM(
        [
            response(
                calls=[
                    ToolCall("a", "echo", "[]"),
                    ToolCall("b", "echo", '{"input":"ok"}'),
                ]
            ),
            response("corrected"),
        ]
    )
    agent = ReActAgent("test", llm, config=config(), tool_registry=registry)
    assert agent.run("task") == "corrected"
    assert "error" in llm.messages[-1][-2]["content"]


def test_duplicate_tool_ids_fail_before_any_execution():
    writes = []
    registry = ToolRegistry()
    registry.register_function(lambda x: writes.append(x), name="write")
    llm = ScriptedLLM(
        [
            response(
                calls=[
                    ToolCall("same", "write", '{"input":"a"}'),
                    ToolCall("same", "write", '{"input":"b"}'),
                ]
            ),
            response("done"),
        ]
    )
    agent = SimpleAgent("test", llm, config=config(), tool_registry=registry)
    with pytest.raises(ValueError, match="ID"):
        agent.run("task")
    assert writes == []


def test_tool_choice_reaches_model_and_is_removed_for_summary():
    seen = []

    class Model(ScriptedLLM):
        def invoke_with_tools(self, messages, tools, **kwargs):
            seen.append(kwargs["tool_choice"])
            return self.invoke(messages, **kwargs)

        def invoke(self, messages, **kwargs):
            if len(self.messages) > 0:
                assert "tool_choice" not in kwargs
            return super().invoke(messages, **kwargs)

    registry = ToolRegistry()
    registry.register_function(lambda x: x, name="echo")
    llm = Model(
        [response(calls=[ToolCall("a", "echo", '{"input":"ok"}')]), response("summary")]
    )
    agent = SimpleAgent(
        "test", llm, config=config(), tool_registry=registry, max_tool_iterations=1
    )
    assert agent.run("task", tool_choice="required") == "summary" and seen == [
        "required"
    ]


def test_nonstream_async_model_override_is_used():
    class Model(ScriptedLLM):
        def invoke(self, *args, **kwargs):
            raise AssertionError("sync entry used")

        async def ainvoke(self, messages, **kwargs):
            return response("async")

    agent = SimpleAgent("test", Model([]), config=config())
    assert asyncio.run(agent.arun("task")) == "async"


def test_cancellation_keeps_completed_tool_receipt(tmp_path):
    writes = []
    registry = ToolRegistry()
    registry.register_function(lambda x: writes.append(x) or "receipt-1", name="write")
    llm = ScriptedLLM([response(calls=[ToolCall("a", "write", '{"input":"once"}')])])
    agent = SimpleAgent("test", llm, config=config(), tool_registry=registry)

    async def main():
        stream = agent.arun_stream("task")
        try:
            async for event in stream:
                if event.type == StreamEventType.TOOL_CALL_FINISH:
                    break
        finally:
            await stream.aclose()

    asyncio.run(main())
    assert writes == ["once"]
    assert any("receipt-1" in m.content for m in agent.get_history())
    assert agent.last_run.status == "cancelled"


def test_auto_save_contains_current_run_statistics(tmp_path):
    store = SessionStore(str(tmp_path))
    cfg = config()
    cfg.auto_save_enabled = True
    cfg.auto_save_interval = 1
    agent = SimpleAgent(
        "test",
        ScriptedLLM([response("done")]),
        config=cfg,
        components=AgentComponents(session_store=store),
    )
    agent.run("task")
    saved = store.load(str(tmp_path / "session-auto.json"))
    assert saved["metadata"]["total_steps"] == 1


def assert_closed(history):
    pending = set()
    for item in history:
        native = item.metadata["model_message"]
        if native["role"] == "tool":
            assert native["tool_call_id"] in pending
            pending.remove(native["tool_call_id"])
        else:
            assert not pending
            pending = {c["id"] for c in native.get("tool_calls", [])}
    assert not pending


@pytest.mark.parametrize(
    "cls", [SimpleAgent, ReActAgent, ReflectionAgent, PlanSolveAgent]
)
def test_interrupted_batch_can_save_restore_and_continue_without_repeating_write(
    tmp_path, cls
):
    writes = []
    registry = ToolRegistry()
    registry.register_function(lambda x: writes.append(x) or "receipt-42", name="write")
    calls = [
        response(
            calls=[
                ToolCall("w", "write", '{"input":"one"}'),
                ToolCall("v", "write", '{"input":"two"}'),
            ]
        )
    ]
    if cls is PlanSolveAgent:
        calls.insert(
            0, response(calls=[ToolCall("p", "generate_plan", '{"steps":["write"]}')])
        )
    store = SessionStore(str(tmp_path))
    agent = cls(
        "test",
        ScriptedLLM(calls),
        config=config(),
        tool_registry=registry,
        components=AgentComponents(session_store=store),
    )

    async def interrupt():
        source = agent.arun_stream("write once")
        try:
            async for event in source:
                if event.type == StreamEventType.TOOL_CALL_FINISH:
                    break
        finally:
            await source.aclose()

    asyncio.run(interrupt())
    # ReAct executes the batch in parallel; others stop before the second write.
    assert writes == (["one", "two"] if cls is ReActAgent else ["one"])
    assert_closed(agent.get_history())
    path = agent.save_session("interrupted")
    restored = SimpleAgent(
        "restored",
        ScriptedLLM([response("received")]),
        config=config(),
        tool_registry=registry,
        components=AgentComponents(session_store=store),
    )
    restored.load_session(path, check_consistency=False)
    before = list(writes)
    assert restored.run("report existing receipts only") == "received"
    assert writes == before
    assert "receipt-42" in json.dumps(restored.llm.messages, ensure_ascii=False)
    assert_closed(restored.get_history())


def test_parallel_timeout_retains_successful_sibling_and_closes_unknown_result():
    registry = ToolRegistry()

    async def operation(value):
        if value == "slow":
            await asyncio.sleep(10)
        return "receipt-fast"

    registry.register_function(operation, name="operation")
    agent = ReActAgent(
        "test",
        ScriptedLLM(
            [
                response(
                    calls=[
                        ToolCall("a", "operation", '{"input":"fast"}'),
                        ToolCall("b", "operation", '{"input":"slow"}'),
                    ]
                )
            ]
        ),
        config=config(tool_async_timeout=0.02),
        tool_registry=registry,
    )
    with pytest.raises(TimeoutError):
        agent.run("task")
    assert agent.last_run.status == "failed"
    assert agent.last_run.tool_calls == 1
    assert_closed(agent.get_history())
    receipts = {
        m.metadata["model_message"]["tool_call_id"]: m.content
        for m in agent.get_history()
        if m.role == "tool"
    }
    assert "receipt-fast" in receipts["a"]
    assert json.loads(receipts["b"])["execution_status"] == "unknown"


def test_active_stream_rejects_session_restore(tmp_path):
    store = SessionStore(str(tmp_path))
    agent = SimpleAgent(
        "test",
        ScriptedLLM([response("done")]),
        config=config(),
        components=AgentComponents(session_store=store),
    )
    path = save(store)

    async def main():
        source = agent.arun_stream("task")
        await anext(source)
        try:
            with pytest.raises(RuntimeError, match="运行中"):
                agent.load_session(path)
        finally:
            await source.aclose()

    asyncio.run(main())
    assert not agent._run_active


def test_native_async_tool_model_override():
    class Model(ScriptedLLM):
        def invoke_with_tools(self, *args, **kwargs):
            raise AssertionError("sync entry used")

        async def ainvoke_with_tools(self, messages, tools, **kwargs):
            return response("native")

    registry = ToolRegistry()
    registry.register_function(lambda x: x, name="echo")
    agent = SimpleAgent("test", Model([]), config=config(), tool_registry=registry)
    assert asyncio.run(agent.arun("task")) == "native"


@pytest.mark.parametrize(
    "name", ["../other", r"nested\file", "/absolute", "", "C:other"]
)
def test_session_delete_rejects_paths(tmp_path, name):
    with pytest.raises(ValueError):
        SessionStore(str(tmp_path)).delete(name)


def test_plan_agent_forced_business_tool_does_not_override_planning_tool():
    seen = []

    class Model(ScriptedLLM):
        def invoke_with_tools(self, messages, tools, **kwargs):
            seen.append(kwargs["tool_choice"])
            return super().invoke_with_tools(messages, tools, **kwargs)

    registry = ToolRegistry()
    registry.register_function(lambda x: x, name="echo")
    llm = Model(
        [
            response(calls=[ToolCall("p", "generate_plan", '{"steps":["do"]}')]),
            response(calls=[ToolCall("e", "echo", '{"input":"ok"}')]),
            response("done"),
        ]
    )
    agent = PlanSolveAgent(
        "test", llm, config=config(), tool_registry=registry, max_tool_iterations=1
    )
    assert agent.run("task", tool_choice="required") == "done"
    assert seen == [
        "auto",
        "required",
    ]


def test_concurrent_session_saves_never_share_a_temporary_file(tmp_path):
    store = SessionStore(str(tmp_path))

    def write(index):
        return save(store, metadata={"index": index, "payload": str(index) * 10000})

    with ThreadPoolExecutor(max_workers=4) as pool:
        paths = list(pool.map(write, range(16)))
    assert len(set(paths)) == 1
    final = store.load(paths[0])["metadata"]
    assert final["payload"] == str(final["index"]) * 10000
    assert not list(tmp_path.glob("*.tmp"))


def test_deadline_clears_only_its_own_cancellation_request():
    async def main():
        task = asyncio.current_task()
        before = task.cancelling() if hasattr(task, "cancelling") else None
        with pytest.raises(TimeoutError):
            async with deadline(0.001):
                await asyncio.sleep(10)
        if before is not None:
            assert task.cancelling() == before
        assert not task.cancelled()
        await asyncio.sleep(0)

    asyncio.run(main())


def test_cancel_between_plan_steps_is_not_reported_as_completed():
    model = ScriptedLLM(
        [
            response(calls=[ToolCall("p", "generate_plan", '{"steps":["one","two"]}')]),
            response("first"),
        ]
    )
    agent = PlanSolveAgent("test", model, config=config())

    async def main():
        source = agent.arun_stream("task")
        try:
            async for event in source:
                if (
                    event.type == StreamEventType.STEP_FINISH
                    and event.data.get("phase") == "execution"
                ):
                    break
        finally:
            await source.aclose()

    asyncio.run(main())
    assert agent.last_run.status == "cancelled"
    assert len(model.messages) == 2
