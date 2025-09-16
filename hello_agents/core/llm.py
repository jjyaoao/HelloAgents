"""HelloAgents统一LLM接口"""

import os
from typing import Literal, Optional, Dict, Any
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek  
from langchain_community.chat_models import ChatTongyi

from .exceptions import HelloAgentsException

# 支持的LLM提供商
SUPPORTED_PROVIDERS = Literal["openai", "deepseek", "qwen"]

class HelloAgentsLLM:
    """HelloAgents统一LLM接口类"""
    
    def __init__(
        self,
        provider: SUPPORTED_PROVIDERS = "deepseek",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs
    ):
        """
        初始化LLM实例
        
        Args:
            provider: LLM提供商
            model: 模型名称
            api_key: API密钥
            base_url: API基础URL
            **kwargs: 其他参数
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.kwargs = kwargs
        
        self._llm = self._create_llm()
    
    def _create_llm(self) -> BaseChatModel:
        """创建具体的LLM实例"""
        if self.provider == "openai":
            return self._create_openai_llm()
        elif self.provider == "deepseek":
            return self._create_deepseek_llm()
        elif self.provider == "qwen":
            return self._create_qwen_llm()
        else:
            raise HelloAgentsException(f"不支持的LLM提供商: {self.provider}")
    
    def _create_openai_llm(self) -> ChatOpenAI:
        """创建OpenAI LLM"""
        api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HelloAgentsException("OpenAI API密钥未设置")
        
        return ChatOpenAI(
            model=self.model or "gpt-4",
            api_key=api_key,
            base_url=self.base_url,
            **self.kwargs
        )
    
    def _create_deepseek_llm(self) -> ChatDeepSeek:
        """创建DeepSeek LLM"""
        api_key = self.api_key or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise HelloAgentsException("DeepSeek API密钥未设置")
        
        return ChatDeepSeek(
            model=self.model or "deepseek-chat",
            api_key=api_key,
            **self.kwargs
        )
    
    def _create_qwen_llm(self) -> ChatTongyi:
        """创建通义千问LLM"""
        api_key = self.api_key or os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise HelloAgentsException("通义千问API密钥未设置")
        
        return ChatTongyi(
            model=self.model or "qwen-plus",
            dashscope_api_key=api_key,
            **self.kwargs
        )
    
    @property
    def llm(self) -> BaseChatModel:
        """获取LLM实例"""
        return self._llm
    
    def bind_tools(self, tools):
        """绑定工具到LLM"""
        return self._llm.bind_tools(tools)