from contextlib import aclosing, closing
"""HelloAgents统一LLM接口 - 支持OpenAI、Anthropic、Gemini等多种接口"""

import os
import asyncio
import math
from copy import deepcopy
from typing import Optional, Iterator, List, Dict, Union, Any, AsyncIterator

from .budget import RunBudget, budgeted, budgeted_stream, budgeted_astream
from .exceptions import HelloAgentsException
from .llm_response import LLMResponse, StreamStats, LLMToolResponse
from .llm_adapters import create_adapter, BaseLLMAdapter


class HelloAgentsLLM:
    """
    HelloAgents统一LLM客户端

    设计理念：
    - 统一配置：只需 LLM_MODEL_ID、LLM_API_KEY、LLM_BASE_URL、LLM_TIMEOUT
    - 自动适配：根据base_url自动选择适配器（OpenAI/Anthropic/Gemini）
    - 统计信息：返回token使用量、耗时等信息，方便日志记录
    - Thinking Model：自动识别并处理推理过程（o1、deepseek-reasoner等）

    支持的接口：
    - OpenAI及所有兼容接口（DeepSeek、Qwen、Kimi、智谱、Ollama等）
    - Anthropic Claude
    - Google Gemini
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        provider: Optional[str] = None,
        budget: Optional[RunBudget] = None,
        **kwargs
    ):
        """
        初始化LLM客户端

        参数优先级：传入参数 > 环境变量

        Args:
            model: 模型名称，默认从 LLM_MODEL_ID 读取
            api_key: API密钥，默认从 LLM_API_KEY 读取
            base_url: 服务地址，默认从 LLM_BASE_URL 读取
            temperature: 温度参数，默认0.7
            max_tokens: 最大token数
            timeout: 超时时间（秒），默认从 LLM_TIMEOUT 读取，默认60秒
        """
        # 加载配置
        self.model = model or os.getenv("LLM_MODEL_ID")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.timeout = timeout if timeout is not None else float(os.getenv("LLM_TIMEOUT", "60"))
        if isinstance(self.timeout, bool) or not isinstance(self.timeout, (int, float)) or not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        self._closed = False
        if budget is not None and not isinstance(budget, RunBudget):
            raise TypeError("budget must be RunBudget")
        self.budget = budget

        self.temperature = temperature
        self.max_tokens = max_tokens
        if {"messages", "tools", "stream", "model", "tool_choice"} & kwargs.keys():
            raise ValueError("messages/tools/stream/model/tool_choice belong to call methods")
        self.kwargs = deepcopy(kwargs)

        # 验证必要参数
        if not self.model:
            raise HelloAgentsException("必须提供模型名称（model参数或LLM_MODEL_ID环境变量）")
        if not self.api_key:
            raise HelloAgentsException("必须提供API密钥（api_key参数或LLM_API_KEY环境变量）")
        if not self.base_url:
            raise HelloAgentsException("必须提供服务地址（base_url参数或LLM_BASE_URL环境变量）")

        # 创建适配器（自动检测）
        self._adapter: BaseLLMAdapter = create_adapter(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            model=self.model,
            provider=provider
        )

        self.provider = {"OpenAIAdapter": "openai", "AnthropicAdapter": "anthropic", "GeminiAdapter": "gemini"}.get(type(self._adapter).__name__, "custom")

        # 最后一次调用的统计信息（用于流式调用）
        self.last_call_stats: Optional[StreamStats] = None

    @staticmethod
    def _validate_messages(messages: List[Dict]) -> None:
        """检查公共消息边界；具体内容块和工具字段仍由适配器处理。"""
        if not isinstance(messages, list):
            raise TypeError('messages 必须是字典列表，例如 [{"role": "user", "content": "你好"}]')
        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                raise TypeError(
                    f"messages[{index}] 必须是字典，收到 {type(message).__name__}。"
                    '请使用 {"role": "user", "content": prompt}；'
                    "LangChain HumanMessage 等消息对象需要显式转换。"
                )
            if not isinstance(message.get("role"), str) or not message["role"].strip():
                raise ValueError(f"messages[{index}].role 必须是非空字符串")

    def _call_kwargs(self, overrides):
        if self._closed:
            raise RuntimeError("HelloAgentsLLM is closed")
        result = deepcopy(self.kwargs)
        result["temperature"] = self.temperature
        if self.max_tokens is not None:
            result["max_tokens"] = self.max_tokens
        result.update(deepcopy(overrides))
        return result

    def think(self, messages, temperature=None):
        """文本流式接口的别名；展示方式由调用方决定。"""
        kwargs = {} if temperature is None else {"temperature": temperature}
        yield from self.stream_invoke(messages, **kwargs)

    @budgeted
    def invoke(self, messages, **kwargs) -> LLMResponse:
        self._validate_messages(messages)
        return self._adapter.invoke(messages, **self._call_kwargs(kwargs))

    @budgeted
    def invoke_with_tools(self, messages, tools, tool_choice="auto", **kwargs) -> LLMToolResponse:
        self._validate_messages(messages)
        return self._adapter.invoke_with_tools(messages, tools, **self._call_kwargs(dict(kwargs, tool_choice=tool_choice)))

    @budgeted_stream
    def stream_invoke(self, messages, **kwargs):
        self._validate_messages(messages)
        source = self._adapter.stream_invoke(messages, **self._call_kwargs(kwargs))
        try:
            yield from source
            self.last_call_stats = getattr(self._adapter, "last_stats", None)
        finally:
            close = getattr(source, "close", None)
            if close:
                close()

    async def ainvoke(self, messages, **kwargs):
        return await asyncio.to_thread(self.invoke, messages, **kwargs)

    async def ainvoke_with_tools(self, messages, tools, tool_choice="auto", **kwargs):
        return await asyncio.to_thread(self.invoke_with_tools, messages, tools, tool_choice, **kwargs)

    @budgeted_astream
    async def astream_invoke(self, messages, **kwargs):
        self._validate_messages(messages)
        async with aclosing(self._adapter.astream_invoke(messages, **self._call_kwargs(kwargs))) as source:
            async for chunk in source:
                yield chunk
        self.last_call_stats = getattr(self._adapter, "last_stats", None)

    @budgeted_astream
    async def astream_invoke_with_tools(self, messages, tools, tool_choice="auto", **kwargs):
        self._validate_messages(messages)
        call_kwargs = self._call_kwargs(dict(kwargs, tool_choice=tool_choice))
        async with aclosing(self._adapter.astream_invoke_with_tools(messages, tools, **call_kwargs)) as source:
            async for item in source:
                if not isinstance(item, str):
                    self.last_call_stats = StreamStats(model=item.model, usage=item.usage,
                        latency_ms=item.latency_ms, finish_reason=item.finish_reason)
                yield item

    def close(self):
        """释放自身持有的客户端；异步应用中应使用 aclose。"""
        if not self._closed:
            self._adapter.close()
            self._closed = True

    async def aclose(self):
        if not self._closed:
            await self._adapter.aclose()
            self._closed = True

    def __enter__(self):
        self._call_kwargs({})
        return self

    def __exit__(self, *_):
        self.close()

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, *_):
        await self.aclose()
