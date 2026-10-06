"""消息捕获替身验证组装与原生工具关联；不代表远程模型质量测试。"""

import asyncio
from copy import deepcopy
import json

import pytest

from hello_agents import Config, Message, SimpleAgent, ToolRegistry
from hello_agents.context import (
    ContextBuilder,
    ContextConfig,
    ContextPacket,
    ContextBudgetExceeded,
    ContextBuildResult,
    MemoryContextProvider,
    RetrievalContextProvider,
)
from hello_agents.core.llm_response import LLMResponse, LLMToolResponse, ToolCall
from hello_agents.memory import MemoryStore
from hello_agents.retrieval import RAGStore
from hello_agents.tools import Tool, ToolParameter, ToolResponse
from hello_agents.tools.builtin import MemoryTool, RAGTool


class CapturingLLM:
    """测试替身：捕获消息并返回预设文本/工具请求，不运行模型。"""

    model = "test-capture"

    def __init__(self, responses=()):
        self.messages = []
        self.schemas = []
        self.responses = iter(responses)

    def invoke(self, messages, **kwargs):
        assert "context_packets" not in kwargs
        self.messages.append(deepcopy(messages))
        return LLMResponse("完成", self.model)

    def invoke_with_tools(self, messages, tools, **kwargs):
        self.messages.append(deepcopy(messages))
        self.schemas.append(deepcopy(tools))
        return next(self.responses)

    def stream_invoke(self, messages, **kwargs):
        self.invoke(messages, **kwargs)
        yield "完成"

    async def astream_invoke(self, messages, **kwargs):
        self.invoke(messages, **kwargs)
        yield "完成"


def config():
    return Config(
        trace_enabled=False,
        skills_enabled=False,
        session_enabled=False,
        subagent_enabled=False,
        todowrite_enabled=False,
        devlog_enabled=False,
    )


def test_chinese_selection_source_roles_and_diagnostics():
    builder = ContextBuilder(ContextConfig(max_tokens=1500))
    evidence = ContextPacket(
        "杭州旅行每天步行不超过五公里", metadata={"id": "source-1", "source": "user:1"}
    )
    irrelevant = ContextPacket("zzzz unrelated", metadata={"id": "other"})
    base = [
        {"role": "system", "content": "遵守任务约束"},
        {"role": "user", "content": "安排杭州旅行"},
    ]
    result = builder.build_messages(base, (p for p in (evidence, irrelevant)))
    assert result.messages[0] == base[0] and result.messages[-1] == base[-1]
    assert result.messages[1]["role"] == "user"
    assert "source-1" in result.messages[1]["content"]
    assert result.diagnostics["selected"][0]["id"] == "source-1"
    assert result.diagnostics["excluded"][0]["reason"] == "relevance"
    assert result.diagnostics["is_estimate"] is True
    assert len(base) == 2


def test_budget_protects_task_schema_and_required_packets():
    base = [{"role": "system", "content": "规则"}, {"role": "user", "content": "旅行"}]
    builder = ContextBuilder(ContextConfig(max_tokens=250))
    with pytest.raises(ContextBudgetExceeded) as exc:
        builder.build_messages(base, tool_schemas=[{"description": "x " * 500}])
    assert exc.value.diagnostics["tool_schema_tokens"] > 0
    with pytest.raises(ContextBudgetExceeded):
        builder.build_messages(
            base, [ContextPacket("x " * 500, metadata={"required": True})]
        )
    result = builder.build_messages(base, [ContextPacket("旅行" * 1000)])
    assert result.messages == base
    assert result.diagnostics["excluded"][0]["reason"] == "budget"


@pytest.mark.parametrize("mode", ["run", "arun", "stream_run", "arun_stream"])
def test_all_simple_agent_paths_receive_context_and_summary(mode):
    llm = CapturingLLM()
    agent = SimpleAgent("test", llm, config=config(), context_builder=ContextBuilder())
    agent.add_message(Message("历史决定：住在西湖附近", "summary"))
    kwargs = {"context_packets": (p for p in [ContextPacket("杭州旅行预算1500元")])}
    if mode == "run":
        agent.run("安排杭州旅行", **kwargs)
    elif mode == "arun":
        asyncio.run(agent.arun("安排杭州旅行", **kwargs))
    elif mode == "stream_run":
        list(agent.stream_run("安排杭州旅行", **kwargs))
    else:

        async def consume():
            return [
                event async for event in agent.arun_stream("安排杭州旅行", **kwargs)
            ]

        asyncio.run(consume())
    sent = json.dumps(llm.messages[0], ensure_ascii=False)
    assert "1500" in sent and "历史摘要" in sent
    assert all(m["role"] != "summary" for m in llm.messages[0])
    assert agent.last_context_diagnostics["estimated_tokens"] > 0


def test_no_silent_context_ignored_and_default_unchanged():
    llm = CapturingLLM()
    agent = SimpleAgent("test", llm, config=config())
    with pytest.raises(ValueError):
        agent.run("hello", context_packets=[ContextPacket("world")])
    agent.run("hello")
    assert llm.messages == [[{"role": "user", "content": "hello"}]]


def test_native_tool_roundtrip_preserves_source_and_registry(tmp_path):
    store = RAGStore(tmp_path / "rag.db")
    store.add_document("杭州博物馆需要预约", "fixture://notice", version="v2")
    registry = ToolRegistry()
    registry.register_tool(RAGTool(store))
    llm = CapturingLLM(
        [
            LLMToolResponse(
                None, [ToolCall("call-1", "rag_search", '{"query":"杭州预约"}')], "test"
            ),
            LLMToolResponse("请预约", [], "test"),
        ]
    )
    agent = SimpleAgent(
        "test",
        llm,
        config=config(),
        tool_registry=registry,
        context_builder=ContextBuilder(),
    )
    assert agent.run("安排杭州旅行") == "请预约"
    messages = llm.messages[1]
    assert messages[-2]["tool_calls"][0]["id"] == "call-1"
    assert messages[-1]["tool_call_id"] == "call-1"
    data = json.loads(messages[-1]["content"])
    assert data["status"] == "success"
    assert data["data"]["results"][0]["source"] == "fixture://notice"
    assert data["data"]["results"][0]["version"] == "v2"
    assert agent.last_context_diagnostics["tool_schema_tokens"] > 0


def test_memory_provider_refreshes_after_tool_withdrawal(tmp_path):
    store = MemoryStore(tmp_path / "m.db", "u", "t")
    record = store.add("私人偏好：唯一待撤回字符串", "user:1")
    registry = ToolRegistry()
    registry.register_tool(MemoryTool(store))
    llm = CapturingLLM(
        [
            LLMToolResponse(
                None,
                [
                    ToolCall(
                        "withdraw",
                        "memory_retract",
                        json.dumps({"memory_id": record.memory_id}),
                    )
                ],
                "test",
            ),
            LLMToolResponse("已撤回", [], "test"),
        ]
    )
    agent = SimpleAgent(
        "test",
        llm,
        config=config(),
        tool_registry=registry,
        context_builder=ContextBuilder(),
        context_providers=[MemoryContextProvider(store, required=True)],
    )
    agent.run("撤回之前的记忆")
    references_before = [
        m for m in llm.messages[0] if "[参考资料" in (m.get("content") or "")
    ]
    references_after = [
        m for m in llm.messages[1] if "[参考资料" in (m.get("content") or "")
    ]
    assert references_before and not references_after
    assert store.search() == []


def test_custom_assembler_protocol_and_provider(tmp_path):
    class Assembler:
        def build_messages(self, messages, additional_packets=(), tool_schemas=()):
            return ContextBuildResult(
                messages
                + [{"role": "user", "content": p.content} for p in additional_packets],
                {"custom": True},
            )

    store = RAGStore(tmp_path / "rag.db")
    store.add_document("杭州旅行指南", "fixture://travel")
    llm = CapturingLLM()
    agent = SimpleAgent(
        "test",
        llm,
        config=config(),
        context_builder=Assembler(),
        context_providers=[RetrievalContextProvider(store)],
    )
    agent.run("杭州旅行")
    assert llm.messages[0][-1]["content"] == "杭州旅行指南"
    assert agent.last_context_diagnostics == {"custom": True}


def test_agent_tools_obey_open_and_failure_triggered_circuit():
    class FailingTool(Tool):
        def __init__(self):
            super().__init__("fail", "测试失败")
            self.calls = 0

        def get_parameters(self):
            return []

        def run(self, parameters):
            self.calls += 1
            return ToolResponse.error("EXECUTION_ERROR", "失败")

    registry = ToolRegistry()
    tool = FailingTool()
    registry.register_tool(tool)
    agent = SimpleAgent("test", CapturingLLM(), config=config(), tool_registry=registry)
    for _ in range(3):
        agent._execute_tool_call("fail", {})
    assert "CIRCUIT_OPEN" in agent._execute_tool_call("fail", {})
    assert tool.calls == 3
    registry.circuit_breaker.close("fail")
    agent._execute_tool_call("fail", {})
    assert tool.calls == 4


def test_react_async_registry_preserves_native_async_and_partial_data():
    from hello_agents import ReActAgent

    class AsyncOnlyTool(Tool):
        def __init__(self):
            super().__init__("async_source", "读取异步资料")
            self.calls = 0

        def get_parameters(self):
            return []

        def run(self, parameters):
            raise AssertionError("不得调用同步方法")

        async def arun(self, parameters):
            await asyncio.sleep(0)
            self.calls += 1
            return ToolResponse.partial(
                "只取得一条", data={"source": "fixture://async"}
            )

    registry = ToolRegistry()
    tool = AsyncOnlyTool()
    registry.register_tool(tool)
    agent = ReActAgent("test", CapturingLLM(), config=config(), tool_registry=registry)
    call = ToolCall("async-1", "async_source", "{}")
    response = asyncio.run(agent._execute_tools_async([call], current_step=1))
    assert response[0][1] == "async-1"
    content = json.loads(response[0][2]["content"])
    assert (
        content["status"] == "partial"
        and content["data"]["source"] == "fixture://async"
    )
    registry.circuit_breaker.open("async_source")
    response = asyncio.run(agent._execute_tools_async([call], current_step=2))
    assert "CIRCUIT_OPEN" in response[0][2]["content"]
    assert tool.calls == 1
    registry.register_function(lambda input_text: f"收到:{input_text}", name="echo")
    function_call = ToolCall("function-1", "echo", '{"input":"hello"}')
    response = asyncio.run(agent._execute_tools_async([function_call], current_step=3))
    assert json.loads(response[0][2]["content"])["data"]["output"] == "收到:hello"
