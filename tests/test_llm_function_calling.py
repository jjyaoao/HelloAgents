"""测试 HelloAgentsLLM 的 Function Calling 功能"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock, patch
from hello_agents.core.llm import HelloAgentsLLM


class TestLLMFunctionCalling:
    """测试 LLM 的 Function Calling 接口"""
    
    @pytest.fixture
    def mock_adapter(self):
        """创建 Mock LLM 适配器"""
        with patch('hello_agents.core.llm.create_adapter') as mock_create_adapter:
            mock_adapter = MagicMock()
            mock_create_adapter.return_value = mock_adapter
            yield mock_adapter
    
    @pytest.fixture
    def llm(self, mock_adapter):
        """创建 HelloAgentsLLM 实例"""
        with patch.dict('os.environ', {
            'LLM_API_KEY': 'test-key',
            'LLM_BASE_URL': 'https://api.test.com/v1',
            'LLM_MODEL_ID': 'test-model'
        }):
            return HelloAgentsLLM()
    
    def test_invoke_with_tools_basic(self, llm, mock_adapter):
        """测试基本的 Function Calling 调用"""
        # 准备测试数据
        messages = [{"role": "user", "content": "计算 2+3"}]
        tools = [{
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
        
        # Mock 响应
        mock_response = MagicMock()
        mock_adapter.invoke_with_tools.return_value = mock_response
        
        # 调用方法
        response = llm.invoke_with_tools(messages, tools, tool_choice="auto")
        
        # 验证调用
        mock_adapter.invoke_with_tools.assert_called_once()
        call_args = mock_adapter.invoke_with_tools.call_args
        call_kwargs = call_args.kwargs

        assert llm.model == "test-model"
        assert call_args.args[0] == messages
        assert call_args.args[1] == tools
        assert call_kwargs["tool_choice"] == "auto"
        assert call_kwargs["temperature"] == 0.7
        assert response == mock_response
    
    def test_invoke_with_tools_custom_params(self, llm, mock_adapter):
        """测试自定义参数传递"""
        messages = [{"role": "user", "content": "测试"}]
        tools = []
        
        mock_response = MagicMock()
        mock_adapter.invoke_with_tools.return_value = mock_response
        
        # 使用自定义参数
        response = llm.invoke_with_tools(
            messages,
            tools,
            tool_choice="required",
            temperature=0.5,
            max_tokens=1000
        )
        
        call_kwargs = mock_adapter.invoke_with_tools.call_args.kwargs
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["max_tokens"] == 1000
        assert call_kwargs["tool_choice"] == "required"
    
    def test_invoke_with_tools_error_handling(self, llm, mock_adapter):
        """测试错误处理"""
        from hello_agents.core.exceptions import HelloAgentsException
        
        messages = [{"role": "user", "content": "测试"}]
        tools = []
        
        # Mock 抛出异常
        mock_adapter.invoke_with_tools.side_effect = HelloAgentsException(
            "Function Calling 调用失败: API 错误"
        )
        
        # 应该抛出 HelloAgentsException
        with pytest.raises(HelloAgentsException) as exc_info:
            llm.invoke_with_tools(messages, tools)
        
        assert "Function Calling 调用失败" in str(exc_info.value)
        assert "API 错误" in str(exc_info.value)


class TestLLMFunctionCallingIntegration:
    """集成测试 - 需要真实 LLM"""
    
    @pytest.mark.skip(reason="需要真实 LLM 环境")
    def test_real_function_calling(self):
        """测试真实的 Function Calling"""
        llm = HelloAgentsLLM()
        
        messages = [{"role": "user", "content": "帮我计算 15 * 8"}]
        tools = [{
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "执行数学计算",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }]
        
        response = llm.invoke_with_tools(messages, tools)
        
        # 验证响应结构
        assert response.choices[0].message.tool_calls is not None
        assert len(response.choices[0].message.tool_calls) > 0
        
        tool_call = response.choices[0].message.tool_calls[0]
        assert tool_call.function.name == "calculate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
