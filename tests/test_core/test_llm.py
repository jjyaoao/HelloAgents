"""LLM模块测试"""

import pytest
from unittest.mock import Mock, patch
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.exceptions import HelloAgentsException

class TestHelloAgentsLLM:
    """HelloAgentsLLM测试类"""
    
    def test_init_with_openai(self):
        """测试OpenAI初始化"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            llm = HelloAgentsLLM(provider="openai")
            assert llm.provider == "openai"
    
    def test_init_with_deepseek(self):
        """测试DeepSeek初始化"""
        with patch.dict('os.environ', {'DEEPSEEK_API_KEY': 'test-key'}):
            llm = HelloAgentsLLM(provider="deepseek")
            assert llm.provider == "deepseek"
    
    def test_unsupported_provider(self):
        """测试不支持的提供商"""
        with pytest.raises(HelloAgentsException):
            HelloAgentsLLM(provider="unsupported")
    
    def test_missing_api_key(self):
        """测试缺少API密钥"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(HelloAgentsException):
                HelloAgentsLLM(provider="openai")