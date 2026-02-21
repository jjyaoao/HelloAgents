"""LLM适配器 - 支持OpenAI、Anthropic、Gemini等不同接口格式"""

import time
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Iterator, List, Dict, Any, Union, AsyncIterator

from .llm_response import LLMResponse, StreamStats
from .exceptions import HelloAgentsException


class BaseLLMAdapter(ABC):
    """LLM适配器基类"""

    def __init__(self, api_key: str, base_url: Optional[str], timeout: int, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.model = model
        self._client = None
        self._async_client = None

    @abstractmethod
    def create_client(self) -> Any:
        """创建客户端实例"""
        pass

    def create_async_client(self) -> Any:
        """创建异步客户端实例（子类可选实现）"""
        return None

    @abstractmethod
    def invoke(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """非流式调用"""
        pass

    @abstractmethod
    def stream_invoke(self, messages: List[Dict], **kwargs) -> Iterator[str]:
        """流式调用，返回生成器"""
        pass

    async def astream_invoke(self, messages: List[Dict], **kwargs) -> AsyncIterator[str]:
        """异步流式调用（子类可选实现真正的异步）

        默认实现：使用队列 + 线程池包装同步流式方法
        """
        queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def _stream_to_queue():
            try:
                for chunk in self.stream_invoke(messages, **kwargs):
                    asyncio.run_coroutine_threadsafe(queue.put(chunk), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(queue.put(e), loop)
            finally:
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        # 在线程池中运行同步流式方法
        loop.run_in_executor(None, _stream_to_queue)

        # 从队列中逐个取出 chunk
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk

    @abstractmethod
    def invoke_with_tools(self, messages: List[Dict], tools: List[Dict], **kwargs) -> Any:
        """工具调用（Function Calling）"""
        pass

    def _is_thinking_model(self, model_name: str) -> bool:
        """判断是否为thinking model"""
        thinking_keywords = ["reasoner", "o1", "o3", "thinking"]
        model_lower = model_name.lower()
        return any(keyword in model_lower for keyword in thinking_keywords)


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI兼容接口适配器（默认）

    支持：
    - OpenAI官方API
    - 所有OpenAI兼容接口（DeepSeek、Qwen、Kimi、智谱等）
    - Thinking Models（o1、deepseek-reasoner等）
    """

    def create_client(self) -> Any:
        """创建OpenAI客户端"""
        from openai import OpenAI

        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )

    def create_async_client(self) -> Any:
        """创建OpenAI异步客户端"""
        from openai import AsyncOpenAI

        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
    
    def invoke(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """非流式调用"""
        if not self._client:
            self._client = self.create_client()
        
        start_time = time.time()
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 提取内容和推理过程
            choice = response.choices[0]
            content = choice.message.content or ""
            reasoning_content = None
            
            # Thinking model特殊处理
            if self._is_thinking_model(self.model):
                # OpenAI o1系列：reasoning_content在message中
                if hasattr(choice.message, 'reasoning_content'):
                    reasoning_content = choice.message.reasoning_content
                # DeepSeek reasoner：可能在其他字段
                elif hasattr(choice, 'reasoning_content'):
                    reasoning_content = choice.reasoning_content
            
            # 提取usage信息
            usage = {}
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            
            return LLMResponse(
                content=content,
                model=self.model,
                usage=usage,
                latency_ms=latency_ms,
                reasoning_content=reasoning_content
            )
            
        except Exception as e:
            raise HelloAgentsException(f"OpenAI API调用失败: {str(e)}")
    
    def stream_invoke(self, messages: List[Dict], **kwargs) -> Iterator[str]:
        """流式调用"""
        if not self._client:
            self._client = self.create_client()
        
        start_time = time.time()
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                **kwargs
            )
            
            collected_content = []
            reasoning_content = None
            usage = {}
            
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    
                    # 提取内容
                    if delta.content:
                        collected_content.append(delta.content)
                        yield delta.content
                    
                    # Thinking model的推理过程
                    if self._is_thinking_model(self.model):
                        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                            if reasoning_content is None:
                                reasoning_content = ""
                            reasoning_content += delta.reasoning_content

                # 提取usage（流式最后一个chunk可能包含）
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    }

            latency_ms = int((time.time() - start_time) * 1000)

            # 返回统计信息（存储到适配器，供外部获取）
            self.last_stats = StreamStats(
                model=self.model,
                usage=usage,
                latency_ms=latency_ms,
                reasoning_content=reasoning_content
            )

        except Exception as e:
            raise HelloAgentsException(f"OpenAI API流式调用失败: {str(e)}")

    async def astream_invoke(self, messages: List[Dict], **kwargs) -> AsyncIterator[str]:
        """真正的异步流式调用（使用 OpenAI 原生异步客户端）"""
        if not self._async_client:
            self._async_client = self.create_async_client()

        start_time = time.time()

        try:
            response = await self._async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                **kwargs
            )

            collected_content = []
            reasoning_content = None
            usage = {}

            async for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta

                    # 提取内容
                    if delta.content:
                        collected_content.append(delta.content)
                        yield delta.content

                    # Thinking model的推理过程
                    if self._is_thinking_model(self.model):
                        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                            if reasoning_content is None:
                                reasoning_content = ""
                            reasoning_content += delta.reasoning_content

                # 提取usage（流式最后一个chunk可能包含）
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    }

            latency_ms = int((time.time() - start_time) * 1000)

            # 返回统计信息（存储到适配器，供外部获取）
            self.last_stats = StreamStats(
                model=self.model,
                usage=usage,
                latency_ms=latency_ms,
                reasoning_content=reasoning_content
            )

        except Exception as e:
            raise HelloAgentsException(f"OpenAI API异步流式调用失败: {str(e)}")

    def invoke_with_tools(self, messages: List[Dict], tools: List[Dict],
                         tool_choice: Union[str, Dict] = "auto", **kwargs) -> Any:
        """工具调用（Function Calling）"""
        if not self._client:
            self._client = self.create_client()

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                **kwargs
            )
            return response

        except Exception as e:
            raise HelloAgentsException(f"OpenAI Function Calling调用失败: {str(e)}")


class AnthropicAdapter(BaseLLMAdapter):
    """Anthropic Claude适配器

    处理Claude特有的消息格式：
    - system参数独立（不在messages中）
    - 消息格式转换
    """

    def create_client(self) -> Any:
        """创建Anthropic客户端"""
        try:
            from anthropic import Anthropic
        except ImportError:
            raise HelloAgentsException(
                "使用Anthropic需要安装: pip install anthropic"
            )

        return Anthropic(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )

    def _convert_messages(self, messages: List[Dict]) -> tuple[Optional[str], List[Dict]]:
        """转换消息格式，提取system消息"""
        system_content = None
        converted_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                converted_messages.append(msg)

        return system_content, converted_messages

    def invoke(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """非流式调用"""
        if not self._client:
            self._client = self.create_client()

        start_time = time.time()
        system_content, converted_messages = self._convert_messages(messages)

        try:
            # 构建请求参数
            request_params = {
                "model": self.model,
                "messages": converted_messages,
                "max_tokens": kwargs.pop("max_tokens", 4096),
                **kwargs
            }
            if system_content:
                request_params["system"] = system_content

            response = self._client.messages.create(**request_params)

            latency_ms = int((time.time() - start_time) * 1000)

            # 提取内容
            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, 'text'):
                        content += block.text

            # 提取usage
            usage = {}
            if hasattr(response, 'usage') and response.usage:
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                }

            return LLMResponse(
                content=content,
                model=self.model,
                usage=usage,
                latency_ms=latency_ms
            )

        except Exception as e:
            raise HelloAgentsException(f"Anthropic API调用失败: {str(e)}")

    def stream_invoke(self, messages: List[Dict], **kwargs) -> Iterator[str]:
        """流式调用"""
        if not self._client:
            self._client = self.create_client()

        start_time = time.time()
        system_content, converted_messages = self._convert_messages(messages)

        try:
            request_params = {
                "model": self.model,
                "messages": converted_messages,
                "max_tokens": kwargs.pop("max_tokens", 4096),
                "stream": True,
                **kwargs
            }
            if system_content:
                request_params["system"] = system_content

            usage = {}

            with self._client.messages.stream(**request_params) as stream:
                for text in stream.text_stream:
                    yield text

                # 获取最终消息以提取usage
                final_message = stream.get_final_message()
                if hasattr(final_message, 'usage') and final_message.usage:
                    usage = {
                        "prompt_tokens": final_message.usage.input_tokens,
                        "completion_tokens": final_message.usage.output_tokens,
                        "total_tokens": final_message.usage.input_tokens + final_message.usage.output_tokens,
                    }

            latency_ms = int((time.time() - start_time) * 1000)

            self.last_stats = StreamStats(
                model=self.model,
                usage=usage,
                latency_ms=latency_ms
            )

        except Exception as e:
            raise HelloAgentsException(f"Anthropic API流式调用失败: {str(e)}")

    def invoke_with_tools(self, messages: List[Dict], tools: List[Dict], **kwargs) -> Any:
        """工具调用（Anthropic格式）"""
        if not self._client:
            self._client = self.create_client()

        system_content, converted_messages = self._convert_messages(messages)

        try:
            request_params = {
                "model": self.model,
                "messages": converted_messages,
                "tools": tools,
                "max_tokens": kwargs.pop("max_tokens", 4096),
                **kwargs
            }
            if system_content:
                request_params["system"] = system_content

            response = self._client.messages.create(**request_params)
            return response

        except Exception as e:
            raise HelloAgentsException(f"Anthropic工具调用失败: {str(e)}")


class GeminiAdapter(BaseLLMAdapter):
    """Google Gemini适配器

    处理Gemini特有的API格式
    """

    def create_client(self) -> Any:
        """创建Gemini客户端"""
        try:
            import google.generativeai as genai
        except ImportError:
            raise HelloAgentsException(
                "使用Gemini需要安装: pip install google-generativeai"
            )

        genai.configure(api_key=self.api_key)
        return genai

    def _convert_messages(self, messages: List[Dict]) -> tuple[Optional[str], List[Dict]]:
        """转换消息格式"""
        system_instruction = None
        converted_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                # Gemini使用 "user" 和 "model" 作为角色
                role = "model" if msg["role"] == "assistant" else "user"
                converted_messages.append({
                    "role": role,
                    "parts": [msg["content"]]
                })

        return system_instruction, converted_messages

    def invoke(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """非流式调用"""
        if not self._client:
            self._client = self.create_client()

        start_time = time.time()
        system_instruction, converted_messages = self._convert_messages(messages)

        try:
            # 创建生成配置
            generation_config = {}
            if "temperature" in kwargs:
                generation_config["temperature"] = kwargs.pop("temperature")
            if "max_tokens" in kwargs:
                generation_config["max_output_tokens"] = kwargs.pop("max_tokens")

            # 创建模型
            model_params = {"model_name": self.model}
            if system_instruction:
                model_params["system_instruction"] = system_instruction

            model = self._client.GenerativeModel(**model_params)

            # 生成内容
            response = model.generate_content(
                converted_messages,
                generation_config=generation_config if generation_config else None
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # 提取内容
            content = response.text if hasattr(response, 'text') else ""

            # 提取usage
            usage = {}
            if hasattr(response, 'usage_metadata'):
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                }

            return LLMResponse(
                content=content,
                model=self.model,
                usage=usage,
                latency_ms=latency_ms
            )

        except Exception as e:
            raise HelloAgentsException(f"Gemini API调用失败: {str(e)}")

    def stream_invoke(self, messages: List[Dict], **kwargs) -> Iterator[str]:
        """流式调用"""
        if not self._client:
            self._client = self.create_client()

        start_time = time.time()
        system_instruction, converted_messages = self._convert_messages(messages)

        try:
            generation_config = {}
            if "temperature" in kwargs:
                generation_config["temperature"] = kwargs.pop("temperature")
            if "max_tokens" in kwargs:
                generation_config["max_output_tokens"] = kwargs.pop("max_tokens")

            model_params = {"model_name": self.model}
            if system_instruction:
                model_params["system_instruction"] = system_instruction

            model = self._client.GenerativeModel(**model_params)

            usage = {}

            response = model.generate_content(
                converted_messages,
                generation_config=generation_config if generation_config else None,
                stream=True
            )

            for chunk in response:
                if hasattr(chunk, 'text'):
                    yield chunk.text

                # 尝试提取usage（可能在最后一个chunk）
                if hasattr(chunk, 'usage_metadata'):
                    usage = {
                        "prompt_tokens": chunk.usage_metadata.prompt_token_count,
                        "completion_tokens": chunk.usage_metadata.candidates_token_count,
                        "total_tokens": chunk.usage_metadata.total_token_count,
                    }

            latency_ms = int((time.time() - start_time) * 1000)

            self.last_stats = StreamStats(
                model=self.model,
                usage=usage,
                latency_ms=latency_ms
            )

        except Exception as e:
            raise HelloAgentsException(f"Gemini API流式调用失败: {str(e)}")

    def invoke_with_tools(self, messages: List[Dict], tools: List[Dict], **kwargs) -> Any:
        """工具调用（Gemini格式）"""
        if not self._client:
            self._client = self.create_client()

        system_instruction, converted_messages = self._convert_messages(messages)

        try:
            # 转换工具格式为Gemini格式
            gemini_tools = []
            for tool in tools:
                if tool.get("type") == "function":
                    func = tool["function"]
                    gemini_tools.append({
                        "name": func["name"],
                        "description": func.get("description", ""),
                        "parameters": func.get("parameters", {})
                    })

            model_params = {"model_name": self.model}
            if system_instruction:
                model_params["system_instruction"] = system_instruction

            model = self._client.GenerativeModel(**model_params, tools=gemini_tools)

            response = model.generate_content(converted_messages)
            return response

        except Exception as e:
            raise HelloAgentsException(f"Gemini工具调用失败: {str(e)}")


def create_adapter(
    api_key: str,
    base_url: Optional[str],
    timeout: int,
    model: str
) -> BaseLLMAdapter:
    """
    根据base_url自动选择适配器

    检测逻辑：
    - anthropic.com -> AnthropicAdapter
    - googleapis.com 或 generativelanguage -> GeminiAdapter
    - 其他 -> OpenAIAdapter（默认）
    """
    if base_url:
        base_url_lower = base_url.lower()

        if "anthropic.com" in base_url_lower:
            return AnthropicAdapter(api_key, base_url, timeout, model)

        if "googleapis.com" in base_url_lower or "generativelanguage" in base_url_lower:
            return GeminiAdapter(api_key, base_url, timeout, model)

    # 默认使用OpenAI适配器（兼容所有OpenAI格式接口）
    return OpenAIAdapter(api_key, base_url, timeout, model)

