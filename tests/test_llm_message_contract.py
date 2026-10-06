"""Public LLM message boundary and empty streaming footer regressions; no network."""

import asyncio
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from hello_agents import HelloAgentsLLM
from hello_agents.core.llm_adapters import OpenAIAdapter


METHODS = [
    "invoke",
    "think",
    "stream_invoke",
    "invoke_with_tools",
    "ainvoke",
    "astream_invoke",
    "ainvoke_with_tools",
]


def consume(llm, method, messages):
    kwargs = {"tools": []} if method.endswith("with_tools") else {}
    result = getattr(llm, method)(messages, **kwargs)
    if method == "astream_invoke":

        async def collect():
            return [part async for part in result]

        return asyncio.run(collect())
    if method.startswith("a"):
        return asyncio.run(result)
    if method in {"think", "stream_invoke"}:
        return list(result)
    return result


@pytest.fixture
def client(monkeypatch):
    adapter = Mock()
    adapter.stream_invoke.return_value = iter(["reply"])

    async def stream(*args, **kwargs):
        adapter.capture(*args, **kwargs)
        yield "reply"

    adapter.astream_invoke = stream
    monkeypatch.setattr(
        "hello_agents.core.llm.create_adapter", lambda **kwargs: adapter
    )
    llm = HelloAgentsLLM(
        model="test-model", api_key="test-key", base_url="https://example.invalid/v1"
    )
    return llm, adapter


@pytest.mark.parametrize("method", METHODS)
def test_foreign_message_objects_fail_before_adapter(client, method):
    llm, adapter = client
    # Minimal foreign object; no LangChain dependency or implied conversion.
    foreign = SimpleNamespace(content="private prompt", type="human")
    with pytest.raises(TypeError, match=r"messages\[0\].*字典") as error:
        consume(llm, method, [foreign])
    assert "private prompt" not in str(error.value)
    assert "HumanMessage" in str(error.value)
    assert adapter.mock_calls == []


@pytest.mark.parametrize("method", METHODS)
def test_provider_fields_pass_through_without_mutation(client, method):
    llm, adapter = client
    messages = [
        {"role": "developer", "content": "policy"},
        {"role": "user", "content": [{"type": "text", "text": "hi"}]},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {"name": "read", "arguments": "{}"},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "c1", "content": "evidence", "name": "read"},
    ]
    before = deepcopy(messages)
    consume(llm, method, messages)
    assert messages == before
    assert adapter.mock_calls[0].args[0] == before


@pytest.mark.parametrize(
    "messages, error",
    [
        ("hello", TypeError),
        ({"role": "user", "content": "hi"}, TypeError),
        ([{"content": "hi"}], ValueError),
        ([{"role": ""}], ValueError),
    ],
)
def test_invalid_container_or_role_fails_locally(client, messages, error):
    llm, adapter = client
    with pytest.raises(error):
        llm.invoke(messages)
    assert adapter.mock_calls == []


@pytest.mark.parametrize("method", ["think", "stream_invoke", "astream_invoke"])
def test_public_stream_keeps_usage_with_empty_choices_footer(monkeypatch, method):
    adapter = OpenAIAdapter("test-key", "https://example.invalid/v1", 60, "test-model")
    chunks = [
        SimpleNamespace(choices=[], usage=None),
        SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="hello"))],
            usage=None,
        ),
        SimpleNamespace(
            choices=[],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2, total_tokens=5),
        ),
    ]
    adapter._client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kw: iter(chunks))
        )
    )

    async def parts():
        for part in chunks:
            yield part

    adapter._async_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(return_value=parts()))
        )
    )
    monkeypatch.setattr(
        "hello_agents.core.llm.create_adapter", lambda **kwargs: adapter
    )
    llm = HelloAgentsLLM(
        model="test-model", api_key="test-key", base_url="https://example.invalid/v1"
    )
    assert consume(llm, method, [{"role": "user", "content": "hi"}]) == ["hello"]
    assert llm.last_call_stats.usage == {
        "prompt_tokens": 3,
        "completion_tokens": 2,
        "total_tokens": 5,
    }
