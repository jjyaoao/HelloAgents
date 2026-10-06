"""Cache experiments need observed provider usage, not fabricated zeroes."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from openai.types import CompletionUsage
from hello_agents.core.llm_adapters import OpenAIAdapter


def make_usage():
    return CompletionUsage(prompt_tokens=120, completion_tokens=8, total_tokens=128,
                           prompt_tokens_details={"cached_tokens": 96},
                           prompt_cache_hit_tokens=96, prompt_cache_miss_tokens=24)


@pytest.mark.parametrize("method", ["invoke", "invoke_with_tools"])
def test_sync_response_preserves_nested_and_provider_metrics(method):
    adapter = OpenAIAdapter("test-key", "https://example.invalid/v1", 10, "test-model")
    message = SimpleNamespace(content="ok", tool_calls=[])
    adapter._client = Mock()
    adapter._client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=message)], model="test-model", usage=make_usage())
    kwargs = {"tools": []} if method.endswith("tools") else {}
    result = getattr(adapter, method)([{"role": "user", "content": "hi"}], **kwargs)
    assert result.usage["prompt_tokens_details"]["cached_tokens"] == 96
    assert result.usage["prompt_cache_miss_tokens"] == 24


def test_empty_footer_keeps_usage_details():
    adapter = OpenAIAdapter("test-key", "https://example.invalid/v1", 10, "test-model")
    adapter._client = Mock()
    adapter._client.chat.completions.create.return_value = iter([
        SimpleNamespace(choices=[], usage=make_usage())])
    assert list(adapter.stream_invoke([{"role": "user", "content": "hi"}])) == []
    assert adapter.last_stats.usage["prompt_tokens_details"]["cached_tokens"] == 96


@pytest.mark.asyncio
async def test_async_empty_footer_keeps_usage_details():
    async def chunks():
        yield SimpleNamespace(choices=[], usage=make_usage())
    adapter = OpenAIAdapter("test-key", "https://example.invalid/v1", 10, "test-model")
    adapter._async_client = Mock()
    adapter._async_client.chat.completions.create = AsyncMock(return_value=chunks())
    assert [x async for x in adapter.astream_invoke([{"role": "user", "content": "hi"}])] == []
    assert adapter.last_stats.usage["prompt_cache_hit_tokens"] == 96


def test_unreported_cache_is_unknown():
    adapter = OpenAIAdapter("test-key", "https://example.invalid/v1", 10, "test-model")
    adapter._client = Mock()
    adapter._client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))],
        usage=CompletionUsage(prompt_tokens=10, completion_tokens=2, total_tokens=12))
    result = adapter.invoke([{"role": "user", "content": "hi"}])
    assert "prompt_tokens_details" not in result.usage
    assert "prompt_cache_hit_tokens" not in result.usage
