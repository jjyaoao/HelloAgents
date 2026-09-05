"""Tests for the LiteLLM gateway adapter."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from hello_agents.core.exceptions import HelloAgentsException
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.llm_adapters import (
    AnthropicAdapter,
    GeminiAdapter,
    LiteLLMAdapter,
    OpenAIAdapter,
    create_adapter,
)


def _chat_response(content="4"):
    return SimpleNamespace(
        model="anthropic/claude-3-5-sonnet",
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, tool_calls=None)
            )
        ],
    )


def _tool_schema():
    return [{
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Run a calculation",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    }]


def _tool_response():
    return SimpleNamespace(
        model="anthropic/claude-3-5-sonnet",
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[
                        SimpleNamespace(
                            id="call_1",
                            function=SimpleNamespace(
                                name="calculate",
                                arguments='{"expression": "2+3"}',
                            ),
                        )
                    ],
                )
            )
        ],
    )


def _mock_litellm(return_value=None):
    """A stand-in for the litellm module with mocked completion()."""
    fake = MagicMock(name="litellm")
    fake.completion = MagicMock(name="litellm.completion", return_value=return_value)
    return fake


class TestCreateAdapter:
    def test_explicit_litellm_provider(self):
        adapter = create_adapter(
            api_key=None, base_url=None, timeout=60,
            model="anthropic/claude-3-5-sonnet", provider="litellm",
        )
        assert isinstance(adapter, LiteLLMAdapter)

    def test_explicit_provider_overrides_base_url_autodetect(self):
        # anthropic.com would auto-detect to AnthropicAdapter, but an explicit
        # provider must win.
        adapter = create_adapter(
            api_key="k", base_url="https://api.anthropic.com", timeout=60,
            model="claude", provider="openai",
        )
        assert isinstance(adapter, OpenAIAdapter)

    def test_no_provider_still_autodetects(self):
        assert isinstance(
            create_adapter("k", "https://api.anthropic.com", 60, "claude"),
            AnthropicAdapter,
        )
        assert isinstance(
            create_adapter("k", "https://generativelanguage.googleapis.com", 60, "gemini"),
            GeminiAdapter,
        )
        assert isinstance(create_adapter("k", "https://api.openai.com/v1", 60, "gpt"), OpenAIAdapter)


class TestLiteLLMAdapter:
    def test_invoke_dispatch_and_defaults(self):
        adapter = LiteLLMAdapter(api_key=None, base_url=None, timeout=60,
                                 model="anthropic/claude-3-5-sonnet")
        fake = _mock_litellm(_chat_response("4"))
        with patch.object(LiteLLMAdapter, "create_client", return_value=fake):
            resp = adapter.invoke([{"role": "user", "content": "2+2?"}], temperature=0.3)

        fake.completion.assert_called_once()
        call_kwargs = fake.completion.call_args[1]
        assert call_kwargs["model"] == "anthropic/claude-3-5-sonnet"
        assert call_kwargs["messages"] == [{"role": "user", "content": "2+2?"}]
        # drop_params defaults to True for cross-provider compatibility.
        assert call_kwargs["drop_params"] is True
        assert call_kwargs["temperature"] == 0.3
        # Blank credentials are omitted so litellm falls back to provider env vars.
        assert "api_key" not in call_kwargs
        assert "api_base" not in call_kwargs
        assert resp.content == "4"
        assert resp.usage["total_tokens"] == 15

    def test_drop_params_can_be_overridden(self):
        adapter = LiteLLMAdapter(None, None, 60, "gpt-4o-mini")
        fake = _mock_litellm(_chat_response())
        with patch.object(LiteLLMAdapter, "create_client", return_value=fake):
            adapter.invoke([{"role": "user", "content": "hi"}], drop_params=False)
        assert fake.completion.call_args[1]["drop_params"] is False

    def test_credentials_forwarded_when_set(self):
        adapter = LiteLLMAdapter(
            api_key="sk-test", base_url="http://localhost:4000/v1", timeout=30,
            model="gpt-4o-mini",
        )
        fake = _mock_litellm(_chat_response())
        with patch.object(LiteLLMAdapter, "create_client", return_value=fake):
            adapter.invoke([{"role": "user", "content": "hi"}])
        call_kwargs = fake.completion.call_args[1]
        assert call_kwargs["api_key"] == "sk-test"
        assert call_kwargs["api_base"] == "http://localhost:4000/v1"
        assert call_kwargs["timeout"] == 30

    def test_stream_invoke_yields_content(self):
        adapter = LiteLLMAdapter(None, None, 60, "gpt-4o-mini")
        chunks = [
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Hel"))], usage=None),
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="lo"))], usage=None),
        ]
        fake = _mock_litellm(iter(chunks))
        with patch.object(LiteLLMAdapter, "create_client", return_value=fake):
            out = list(adapter.stream_invoke([{"role": "user", "content": "hi"}]))
        assert "".join(out) == "Hello"
        assert fake.completion.call_args[1]["stream"] is True

    def test_invoke_with_tools(self):
        adapter = LiteLLMAdapter(None, None, 60, "anthropic/claude-3-5-sonnet")
        fake = _mock_litellm(_tool_response())
        with patch.object(LiteLLMAdapter, "create_client", return_value=fake):
            resp = adapter.invoke_with_tools(
                [{"role": "user", "content": "2+3?"}], _tool_schema(), tool_choice="auto"
            )
        call_kwargs = fake.completion.call_args[1]
        assert call_kwargs["tools"] == _tool_schema()
        assert call_kwargs["tool_choice"] == "auto"
        assert call_kwargs["drop_params"] is True
        assert resp.tool_calls[0].name == "calculate"
        assert resp.tool_calls[0].arguments == '{"expression": "2+3"}'

    def test_errors_wrapped(self):
        adapter = LiteLLMAdapter(None, None, 60, "gpt-4o-mini")
        fake = MagicMock()
        fake.completion.side_effect = RuntimeError("boom")
        with patch.object(LiteLLMAdapter, "create_client", return_value=fake):
            with pytest.raises(HelloAgentsException) as exc:
                adapter.invoke([{"role": "user", "content": "hi"}])
        assert "LiteLLM" in str(exc.value)
        assert "boom" in str(exc.value)

    def test_missing_litellm_raises_helpful_error(self):
        adapter = LiteLLMAdapter(None, None, 60, "gpt-4o-mini")
        with patch("builtins.__import__", side_effect=ImportError("no litellm")):
            with pytest.raises(HelloAgentsException) as exc:
                adapter.create_client()
        assert "pip install litellm" in str(exc.value)


class TestHelloAgentsLLMLiteLLM:
    def test_litellm_provider_needs_no_base_url_or_key(self):
        """The litellm path routes by model prefix + provider env vars."""
        fake = _mock_litellm(_chat_response("4"))
        with patch.object(LiteLLMAdapter, "create_client", return_value=fake):
            llm = HelloAgentsLLM(model="anthropic/claude-3-5-sonnet", provider="litellm")
            resp = llm.invoke([{"role": "user", "content": "2+2?"}])
        assert isinstance(llm._adapter, LiteLLMAdapter)
        assert resp.content == "4"

    def test_provider_from_env(self):
        fake = _mock_litellm(_chat_response())
        with patch.dict("os.environ", {"LLM_PROVIDER": "litellm", "LLM_MODEL_ID": "gpt-4o-mini"}):
            with patch.object(LiteLLMAdapter, "create_client", return_value=fake):
                llm = HelloAgentsLLM()
        assert isinstance(llm._adapter, LiteLLMAdapter)

    def test_non_litellm_still_requires_base_url(self):
        with pytest.raises(HelloAgentsException):
            HelloAgentsLLM(model="gpt-4o-mini", api_key="k")
