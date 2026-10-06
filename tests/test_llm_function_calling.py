"""测试 HelloAgentsLLM 的 Function Calling 功能"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from hello_agents.core.exceptions import HelloAgentsException
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.llm_adapters import AnthropicAdapter, GeminiAdapter, OpenAIAdapter


def _tool_schema():
    return [{
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"}
                },
                "required": ["expression"]
            }
        }
    }]


def _openai_tool_response():
    return SimpleNamespace(
        model="test-model",
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
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


class TestLLMFunctionCalling:
    """测试 LLM 的 Function Calling 接口"""

    @pytest.fixture
    def mock_openai_client(self):
        mock_client = MagicMock()
        with patch.object(OpenAIAdapter, "create_client", return_value=mock_client):
            yield mock_client

    @pytest.fixture
    def llm(self, mock_openai_client):
        """创建 HelloAgentsLLM 实例"""
        with patch.dict("os.environ", {
            "LLM_API_KEY": "test-key",
            "LLM_BASE_URL": "https://api.test.com/v1",
            "LLM_MODEL_ID": "test-model",
        }):
            return HelloAgentsLLM()

    def test_invoke_with_tools_basic(self, llm, mock_openai_client):
        """测试基本的 Function Calling 调用"""
        messages = [{"role": "user", "content": "计算 2+3"}]
        tools = _tool_schema()
        mock_openai_client.chat.completions.create.return_value = _openai_tool_response()

        response = llm.invoke_with_tools(messages, tools, tool_choice="auto")

        mock_openai_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]

        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["messages"] == messages
        assert call_kwargs["tools"] == tools
        assert call_kwargs["tool_choice"] == "auto"
        assert response.content == ""
        assert response.model == "test-model"
        assert response.usage["total_tokens"] == 15
        assert response.tool_calls[0].id == "call_1"
        assert response.tool_calls[0].name == "calculate"
        assert response.tool_calls[0].arguments == '{"expression": "2+3"}'

    def test_invoke_with_tools_custom_params(self, llm, mock_openai_client):
        """测试自定义参数传递"""
        messages = [{"role": "user", "content": "测试"}]
        tools = []
        mock_openai_client.chat.completions.create.return_value = _openai_tool_response()

        llm.invoke_with_tools(
            messages,
            tools,
            tool_choice="required",
            temperature=0.5,
            max_tokens=1000,
        )

        call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 1000
        assert call_kwargs["tool_choice"] == "required"

    def test_invoke_with_tools_error_handling(self, llm, mock_openai_client):
        """测试错误处理"""
        messages = [{"role": "user", "content": "测试"}]
        tools = []
        mock_openai_client.chat.completions.create.side_effect = Exception("API 错误")

        with pytest.raises(HelloAgentsException) as exc_info:
            llm.invoke_with_tools(messages, tools)

        assert "Function Calling调用失败" in str(exc_info.value)
        assert "API 错误" in str(exc_info.value)


def test_anthropic_invoke_with_tools_converts_schema_and_response():
    """Anthropic 路径也应接收统一 schema 并返回统一 LLMToolResponse"""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="需要计算"),
            SimpleNamespace(
                type="tool_use",
                id="toolu_1",
                name="calculate",
                input={"expression": "2+3"},
            ),
        ],
        usage=SimpleNamespace(input_tokens=8, output_tokens=4),
    )

    adapter = AnthropicAdapter("test-key", "https://api.anthropic.com", 60, "claude-test")
    adapter._client = mock_client
    messages = [
        {"role": "system", "content": "你是计算助手"},
        {"role": "user", "content": "计算 2+3"},
    ]

    response = adapter.invoke_with_tools(
        messages,
        _tool_schema(),
        tool_choice={"type": "function", "function": {"name": "calculate"}},
    )

    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["system"] == "你是计算助手"
    assert call_kwargs["tools"] == [{
        "name": "calculate",
        "description": "执行数学计算",
        "input_schema": _tool_schema()[0]["function"]["parameters"],
    }]
    assert call_kwargs["tool_choice"] == {"type": "tool", "name": "calculate"}
    assert response.content == "需要计算"
    assert response.tool_calls[0].id == "toolu_1"
    assert response.tool_calls[0].name == "calculate"
    assert response.tool_calls[0].arguments == '{"expression": "2+3"}'
    assert response.usage["total_tokens"] == 12


def test_anthropic_converts_openai_tool_history_messages():
    """多轮工具调用历史应转换为 Anthropic tool_use/tool_result blocks"""
    adapter = AnthropicAdapter("test-key", "https://api.anthropic.com", 60, "claude-test")

    _, converted = adapter._convert_messages([
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "calculate",
                    "arguments": '{"expression": "2+3"}',
                },
            }],
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": "5",
        },
    ])

    assert converted == [
        {
            "role": "assistant",
            "content": [{
                "type": "tool_use",
                "id": "call_1",
                "name": "calculate",
                "input": {"expression": "2+3"},
            }],
        },
        {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": "call_1",
                "content": "5",
            }],
        },
    ]


def test_gemini_invoke_with_tools_converts_schema_and_response():
    """Gemini 路径也应接收统一 schema 并返回统一 LLMToolResponse"""
    pytest.importorskip("google.genai")

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = SimpleNamespace(
        text="",
        candidates=[
            SimpleNamespace(
                content=SimpleNamespace(
                    parts=[
                        SimpleNamespace(
                            function_call=SimpleNamespace(
                                name="calculate",
                                args={"expression": "2+3"},
                            )
                        )
                    ]
                )
            )
        ],
        usage_metadata=SimpleNamespace(
            prompt_token_count=8,
            candidates_token_count=4,
            total_token_count=12,
        ),
    )

    adapter = GeminiAdapter("test-key", "https://generativelanguage.googleapis.com", 60, "gemini-test")
    adapter._client = mock_client
    messages = [
        {"role": "system", "content": "你是计算助手"},
        {"role": "user", "content": "计算 2+3"},
    ]

    response = adapter.invoke_with_tools(
        messages,
        _tool_schema(),
        tool_choice={"type": "function", "function": {"name": "calculate"}},
        temperature=0.2,
        max_tokens=100,
    )

    from google.genai import types as genai_types

    call_kwargs = mock_client.models.generate_content.call_args[1]
    config = call_kwargs["config"]
    assert call_kwargs["model"] == "gemini-test"
    assert config.system_instruction == "你是计算助手"
    assert config.temperature == 0.2
    assert config.max_output_tokens == 100
    assert config.tools[0].function_declarations[0].name == "calculate"
    assert config.tools[0].function_declarations[0].parameters_json_schema == (
        _tool_schema()[0]["function"]["parameters"]
    )
    assert isinstance(config.tool_config, genai_types.ToolConfig)
    function_config = config.tool_config.function_calling_config
    assert function_config.mode == genai_types.FunctionCallingConfigMode.ANY
    assert function_config.allowed_function_names == ["calculate"]
    assert response.tool_calls[0].name == "calculate"
    assert response.tool_calls[0].arguments == '{"expression": "2+3"}'
    assert response.usage["total_tokens"] == 12


def test_gemini_converts_openai_tool_history_messages():
    """多轮工具调用历史应转换为 Gemini function_call/function_response parts"""
    pytest.importorskip("google.genai")
    adapter = GeminiAdapter("test-key", "https://generativelanguage.googleapis.com", 60, "gemini-test")

    _, converted = adapter._convert_messages([
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "calculate",
                    "arguments": '{"expression": "2+3"}',
                },
            }],
        },
        {
            "role": "tool",
            "tool_call_id": "call_1",
            "content": "5",
        },
    ])

    assert converted[0].role == "model"
    assert converted[0].parts[0].function_call.name == "calculate"
    assert dict(converted[0].parts[0].function_call.args) == {"expression": "2+3"}
    assert converted[1].role == "tool"
    assert converted[1].parts[0].function_response.name == "calculate"
    assert converted[1].parts[0].function_response.response == {"result": "5"}


class TestLLMFunctionCallingIntegration:
    """集成测试 - 需要真实 LLM"""

    @pytest.mark.live
    def test_real_function_calling(self, live_llm_config):
        """测试真实的 Function Calling"""
        llm = HelloAgentsLLM(**live_llm_config)
        response = llm.invoke_with_tools(
            [{"role": "user", "content": "必须调用 calculate 工具计算 15 * 8，不要自行计算。"}],
            _tool_schema(),
            tool_choice="auto",
        )

        assert response.tool_calls
        assert response.tool_calls[0].name == "calculate"
