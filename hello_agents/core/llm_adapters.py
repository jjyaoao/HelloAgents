"""LLM适配器 - 支持OpenAI、Anthropic、Gemini等不同接口格式"""

import time
import asyncio
import json
import queue as thread_queue
import threading
from urllib.parse import urlparse
from abc import ABC, abstractmethod
from typing import Optional, Iterator, List, Dict, Any, Union, AsyncIterator

from .llm_response import LLMResponse, StreamStats, LLMToolResponse, ToolCall
from .exceptions import HelloAgentsException


def _openai_usage(value) -> Dict[str, Any]:
    """保留服务端报告的 Token 明细，不补造缺失的缓存指标。"""
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if callable(getattr(value, "model_dump", None)):
        return value.model_dump(exclude_none=True)
    return {name: getattr(value, name) for name in (
        "prompt_tokens", "completion_tokens", "total_tokens",
        "prompt_tokens_details", "completion_tokens_details",
        "prompt_cache_hit_tokens", "prompt_cache_miss_tokens",
    ) if hasattr(value, name) and getattr(value, name) is not None}


class BaseLLMAdapter(ABC):
    """LLM适配器基类"""

    def __init__(self, api_key: str, base_url: Optional[str], timeout: int, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.model = model
        self._client = None
        self._async_client = None
        self._client_lock = threading.Lock()

    def _get_client(self):
        with self._client_lock:
            if self._client is None:
                self._client = self.create_client()
            return self._client

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

    async def astream_invoke(self, messages: List[Dict], **kwargs):
        """使用有界缓冲的回退实现；取消后，在当前阻塞读取结束时停止拉取。"""
        items = thread_queue.Queue(maxsize=8)
        stopped = threading.Event()
        end = object()

        def put(value):
            while not stopped.is_set():
                try:
                    items.put(value, timeout=0.05)
                    return True
                except thread_queue.Full:
                    continue
            return False

        def produce():
            source = self.stream_invoke(messages, **kwargs)
            try:
                while not stopped.is_set():
                    try:
                        item = next(source)
                    except StopIteration:
                        break
                    if not put(item):
                        break
            except Exception as exc:
                put(exc)
            finally:
                close = getattr(source, "close", None)
                if close:
                    close()
                put(end)

        worker = threading.Thread(target=produce, daemon=True, name="helloagents-stream")
        worker.start()
        try:
            while True:
                try:
                    item = items.get_nowait()
                except thread_queue.Empty:
                    await asyncio.sleep(0.01)
                    continue
                if item is end:
                    break
                if isinstance(item, Exception):
                    raise item
                yield item
        finally:
            stopped.set()
            # 同步 SDK 的读取可能阻塞到自身超时；等待线程结束时不能阻塞事件循环。

    def close(self):
        if self._async_client is not None:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(self.aclose())
                return
            raise RuntimeError("Use await llm.aclose() for async clients")
        if self._client is not None:
            self._client.close()
            self._client = None

    async def aclose(self):
        if self._async_client is not None:
            await self._async_client.close()
            self._async_client = None
        if self._client is not None:
            await asyncio.to_thread(self._client.close)
            self._client = None

    @abstractmethod
    def invoke_with_tools(self, messages: List[Dict], tools: List[Dict], **kwargs) -> LLMToolResponse:
        """工具调用（Function Calling）"""
        pass

    async def astream_invoke_with_tools(self, messages, tools, **kwargs):
        """回退适配器只产出一次完整响应，不模拟逐 Token 流式输出。"""
        if tools:
            response = await asyncio.to_thread(self.invoke_with_tools, messages, tools, **kwargs)
        else:
            kwargs.pop("tool_choice", None)
            response = await asyncio.to_thread(self.invoke, messages, **kwargs)
        if response.content:
            yield response.content
        yield response

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
        self._get_client()
        
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
            
            reasoning_content = getattr(choice.message, "reasoning_content", None)

            # 提取usage信息
            usage = {}
            if hasattr(response, 'usage') and response.usage:
                usage = _openai_usage(response.usage)
            
            return LLMResponse(
                finish_reason=getattr(response.choices[0], "finish_reason", None),
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
        self._get_client()
        
        start_time = time.time()
        
        response = None
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                **kwargs
            )
            
            collected_content = []
            reasoning_content = None
            finish_reason = None
            usage = {}
            
            for chunk in response:
                choices = getattr(chunk, "choices", None)
                if choices:
                    finish_reason = getattr(choices[0], "finish_reason", None) or finish_reason
                    delta = getattr(choices[0], "delta", None)
                    if delta is not None:
                        # 提取内容
                        content = getattr(delta, "content", None)
                        if content:
                            collected_content.append(content)
                            yield content

                        # Thinking model的推理过程
                        reasoning_delta = getattr(delta, "reasoning_content", None)
                        if reasoning_delta:
                            if reasoning_content is None:
                                reasoning_content = ""
                            reasoning_content += reasoning_delta

                # 提取usage（流式最后一个chunk可能包含）
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = _openai_usage(chunk.usage)

            latency_ms = int((time.time() - start_time) * 1000)

            # 返回统计信息（存储到适配器，供外部获取）
            self.last_stats = StreamStats(
                model=self.model,
                usage=usage,
                latency_ms=latency_ms,
                reasoning_content=reasoning_content,
                finish_reason=finish_reason
            )

        except Exception as e:
            raise HelloAgentsException(f"OpenAI API流式调用失败: {str(e)}")
        finally:
            close = getattr(response, "close", None)
            if close:
                close()


    async def astream_invoke(self, messages: List[Dict], **kwargs) -> AsyncIterator[str]:
        """真正的异步流式调用（使用 OpenAI 原生异步客户端）"""
        if not self._async_client:
            self._async_client = self.create_async_client()

        start_time = time.time()

        response = None
        try:
            response = await self._async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                **kwargs
            )

            collected_content = []
            reasoning_content = None
            finish_reason = None
            usage = {}

            async for chunk in response:
                choices = getattr(chunk, "choices", None)
                if choices:
                    finish_reason = getattr(choices[0], "finish_reason", None) or finish_reason
                    delta = getattr(choices[0], "delta", None)
                    if delta is not None:
                        # 提取内容
                        content = getattr(delta, "content", None)
                        if content:
                            collected_content.append(content)
                            yield content

                        # Thinking model的推理过程
                        reasoning_delta = getattr(delta, "reasoning_content", None)
                        if reasoning_delta:
                            if reasoning_content is None:
                                reasoning_content = ""
                            reasoning_content += reasoning_delta

                # 提取usage（流式最后一个chunk可能包含）
                if hasattr(chunk, 'usage') and chunk.usage:
                    usage = _openai_usage(chunk.usage)

            latency_ms = int((time.time() - start_time) * 1000)

            # 返回统计信息（存储到适配器，供外部获取）
            self.last_stats = StreamStats(
                model=self.model,
                usage=usage,
                latency_ms=latency_ms,
                reasoning_content=reasoning_content,
                finish_reason=finish_reason
            )

        except Exception as e:
            raise HelloAgentsException(f"OpenAI API异步流式调用失败: {str(e)}")
        finally:
            close = getattr(response, "close", None)
            if close:
                await close()


    def invoke_with_tools(self, messages: List[Dict], tools: List[Dict],
                         tool_choice: Union[str, Dict] = "auto", **kwargs) -> LLMToolResponse:
        """工具调用（Function Calling）"""
        self._get_client()

        start_time = time.time()
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                **kwargs
            )

            latency_ms = int((time.time() - start_time) * 1000)
            message = response.choices[0].message

            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append(ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments
                    ))

            usage = {}
            if response.usage:
                usage = _openai_usage(response.usage)

            return LLMToolResponse(
                finish_reason=getattr(response.choices[0], "finish_reason", None),
                content=message.content,
                reasoning_content=getattr(message, "reasoning_content", None),
                tool_calls=tool_calls,
                model=response.model,
                usage=usage,
                latency_ms=latency_ms
            )

        except Exception as e:
            raise HelloAgentsException(f"OpenAI Function Calling调用失败: {str(e)}")


    async def astream_invoke_with_tools(self, messages, tools, **kwargs):
        """先产出可见文本的增量，最后产出一次组装完成的工具响应。"""
        started = time.monotonic()
        if tools:
            kwargs["tools"] = tools
        else:
            kwargs.pop("tool_choice", None)
        client = self.create_async_client()
        stream = None
        content, calls, usage, reason = [], {}, {}, None
        reasoning = []
        try:
            stream = await client.chat.completions.create(
                model=self.model, messages=messages, stream=True,
                stream_options={"include_usage": True}, **kwargs)
            async for chunk in stream:
                if getattr(chunk, "usage", None):
                    usage = _openai_usage(chunk.usage)
                if not getattr(chunk, "choices", None):
                    continue
                choice = chunk.choices[0]
                reason = getattr(choice, "finish_reason", None) or reason
                delta = choice.delta
                if getattr(delta, "reasoning_content", None):
                    reasoning.append(delta.reasoning_content)
                if getattr(delta, "content", None):
                    content.append(delta.content)
                    yield delta.content
                for part in getattr(delta, "tool_calls", None) or []:
                    item = calls.setdefault(part.index, {"id": "", "name": "", "arguments": ""})
                    if part.id:
                        item["id"] = part.id
                    if part.function:
                        item["name"] += part.function.name or ""
                        item["arguments"] += part.function.arguments or ""
        finally:
            try:
                if stream is not None:
                    await stream.close()
            finally:
                await client.close()
        yield LLMToolResponse(
            content="".join(content), tool_calls=[ToolCall(**calls[i]) for i in sorted(calls)],
            model=self.model, usage=usage, finish_reason=reason, reasoning_content="".join(reasoning) or None,
            latency_ms=int((time.monotonic() - started) * 1000))


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
                "缺少 Anthropic 可选依赖。请按安装文档启用 anthropic 组件；"
                "源码目录执行 python -m pip install -r requirements/anthropic.txt"
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
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                content_blocks = []
                if msg.get("content"):
                    content_blocks.append({"type": "text", "text": msg["content"]})

                for tool_call in msg["tool_calls"]:
                    function = tool_call.get("function", {})
                    arguments = function.get("arguments", {})
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            arguments = {}

                    content_blocks.append({
                        "type": "tool_use",
                        "id": tool_call.get("id"),
                        "name": function.get("name"),
                        "input": arguments,
                    })

                converted_messages.append({
                    "role": "assistant",
                    "content": content_blocks,
                })
            elif msg["role"] == "tool":
                converted_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.get("tool_call_id"),
                        "content": msg.get("content", ""),
                    }],
                })
            else:
                converted_messages.append(msg)

        return system_content, converted_messages

    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """将统一的 OpenAI 风格工具 schema 转换为 Anthropic 工具 schema"""
        converted_tools = []
        for tool in tools:
            if tool.get("type") == "function" and "function" in tool:
                function = tool["function"]
                converted_tools.append({
                    "name": function["name"],
                    "description": function.get("description", ""),
                    "input_schema": function.get("parameters", {
                        "type": "object",
                        "properties": {},
                    }),
                })
            else:
                converted_tools.append(tool)

        return converted_tools

    def _convert_tool_choice(self, tool_choice: Any) -> Optional[Dict]:
        """将统一的 tool_choice 转换为 Anthropic 格式"""
        if tool_choice is None:
            return None
        if tool_choice in ("auto", "none"):
            return {"type": tool_choice}
        if tool_choice == "required":
            return {"type": "any"}
        if isinstance(tool_choice, dict):
            function = tool_choice.get("function")
            if function and function.get("name"):
                return {"type": "tool", "name": function["name"]}
        return tool_choice

    def invoke(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """非流式调用"""
        self._get_client()

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
                finish_reason=getattr(response, "stop_reason", None),
                content=content,
                model=self.model,
                usage=usage,
                latency_ms=latency_ms
            )

        except Exception as e:
            raise HelloAgentsException(f"Anthropic API调用失败: {str(e)}")

    def stream_invoke(self, messages: List[Dict], **kwargs) -> Iterator[str]:
        """流式调用"""
        self._get_client()

        start_time = time.time()
        system_content, converted_messages = self._convert_messages(messages)

        try:
            request_params = {
                "model": self.model,
                "messages": converted_messages,
                "max_tokens": kwargs.pop("max_tokens", 4096),
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

    def invoke_with_tools(self, messages: List[Dict], tools: List[Dict], **kwargs) -> LLMToolResponse:
        """工具调用（Anthropic格式）"""
        self._get_client()

        system_content, converted_messages = self._convert_messages(messages)
        converted_tools = self._convert_tools(tools)
        tool_choice = self._convert_tool_choice(kwargs.pop("tool_choice", None))

        start_time = time.time()
        try:
            request_params = {
                "model": self.model,
                "messages": converted_messages,
                "tools": converted_tools,
                "max_tokens": kwargs.pop("max_tokens", 4096),
                **kwargs
            }
            if system_content:
                request_params["system"] = system_content
            if tool_choice:
                request_params["tool_choice"] = tool_choice

            response = self._client.messages.create(**request_params)
            latency_ms = int((time.time() - start_time) * 1000)

            content = ""
            tool_calls = []
            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    tool_calls.append(ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=json.dumps(block.input)
                    ))

            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }

            return LLMToolResponse(
                finish_reason=getattr(response, "stop_reason", None),
                content=content if content else None,
                tool_calls=tool_calls,
                model=self.model,
                usage=usage,
                latency_ms=latency_ms
            )

        except Exception as e:
            raise HelloAgentsException(f"Anthropic工具调用失败: {str(e)}")


class GeminiAdapter(BaseLLMAdapter):
    """Google Gemini适配器

    处理Gemini特有的API格式
    使用新版 google.genai 包（替代已废弃的 google.generativeai）
    """

    def create_client(self) -> Any:
        """创建Gemini客户端"""
        try:
            from google import genai
        except ImportError:
            raise HelloAgentsException(
                "缺少 Gemini 可选依赖。请按安装文档启用 gemini 组件；"
                "源码目录执行 python -m pip install -r requirements/gemini.txt"
            )

        client = genai.Client(api_key=self.api_key, http_options={"base_url": self.base_url, "timeout": int(self.timeout * 1000)})
        return client

    def _convert_messages(self, messages: List[Dict]) -> tuple[Optional[str], List[Dict]]:
        """转换消息格式"""
        from google.genai import types as genai_types

        system_instruction = None
        converted_messages = []
        tool_call_names = {}

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "assistant" and msg.get("tool_calls"):
                parts = []
                if msg.get("content"):
                    parts.append(genai_types.Part.from_text(text=msg["content"]))

                for tool_call in msg["tool_calls"]:
                    function = tool_call.get("function", {})
                    arguments = function.get("arguments", {})
                    if isinstance(arguments, str):
                        try:
                            arguments = json.loads(arguments)
                        except json.JSONDecodeError:
                            arguments = {}

                    tool_name = function.get("name", "")
                    tool_call_id = tool_call.get("id")
                    if tool_call_id and tool_name:
                        tool_call_names[tool_call_id] = tool_name

                    parts.append(genai_types.Part.from_function_call(
                        name=tool_name,
                        args=arguments,
                    ))

                converted_messages.append(genai_types.Content(
                    role="model",
                    parts=parts,
                ))
            elif msg["role"] == "tool":
                tool_name = tool_call_names.get(msg.get("tool_call_id"), "tool_result")
                converted_messages.append(genai_types.Content(
                    role="tool",
                    parts=[genai_types.Part.from_function_response(
                        name=tool_name,
                        response={"result": msg.get("content", "")},
                    )],
                ))
            else:
                # Gemini使用 "user" 和 "model" 作为角色
                role = "model" if msg["role"] == "assistant" else "user"
                converted_messages.append(genai_types.Content(
                    role=role,
                    parts=[genai_types.Part.from_text(text=msg["content"] or "")],
                ))

        return system_instruction, converted_messages

    def _convert_tool_choice(self, tool_choice: Any) -> Optional[Any]:
        """将统一的 tool_choice 转换为 Gemini 工具配置"""
        from google.genai import types as genai_types

        if tool_choice in (None, "auto"):
            return None
        if tool_choice == "none":
            return genai_types.ToolConfig(
                function_calling_config=genai_types.FunctionCallingConfig(mode="NONE")
            )
        if tool_choice == "required":
            return genai_types.ToolConfig(
                function_calling_config=genai_types.FunctionCallingConfig(mode="ANY")
            )
        if isinstance(tool_choice, dict):
            function = tool_choice.get("function")
            if function and function.get("name"):
                return genai_types.ToolConfig(
                    function_calling_config=genai_types.FunctionCallingConfig(
                        mode="ANY",
                        allowed_function_names=[function["name"]],
                    )
                )
        return tool_choice

    def invoke(self, messages: List[Dict], **kwargs) -> LLMResponse:
        """非流式调用"""
        self._get_client()

        from google.genai import types as genai_types

        start_time = time.time()
        system_instruction, converted_messages = self._convert_messages(messages)

        try:
            # 创建生成配置
            config_params = dict(kwargs)
            if "temperature" in kwargs:
                config_params["temperature"] = kwargs.pop("temperature")
            if "max_tokens" in kwargs:
                config_params["max_output_tokens"] = config_params.pop("max_tokens")
            if system_instruction:
                config_params["system_instruction"] = system_instruction

            response = self._client.models.generate_content(
                model=self.model,
                contents=converted_messages,
                config=genai_types.GenerateContentConfig(**config_params) if config_params else None
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # 提取内容
            content = response.text if hasattr(response, 'text') else ""

            # 提取usage
            usage = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                    "total_tokens": response.usage_metadata.total_token_count or 0,
                }

            return LLMResponse(
                finish_reason=getattr(response.candidates[0], "finish_reason", None) if getattr(response, "candidates", None) else None,
                content=content,
                model=self.model,
                usage=usage,
                latency_ms=latency_ms
            )

        except Exception as e:
            raise HelloAgentsException(f"Gemini API调用失败: {str(e)}")

    def stream_invoke(self, messages: List[Dict], **kwargs) -> Iterator[str]:
        """流式调用"""
        self._get_client()

        from google.genai import types as genai_types

        start_time = time.time()
        system_instruction, converted_messages = self._convert_messages(messages)

        response = None
        try:
            # 创建生成配置
            config_params = dict(kwargs)
            if "temperature" in kwargs:
                config_params["temperature"] = kwargs.pop("temperature")
            if "max_tokens" in kwargs:
                config_params["max_output_tokens"] = config_params.pop("max_tokens")
            if system_instruction:
                config_params["system_instruction"] = system_instruction

            usage = {}

            response = self._client.models.generate_content_stream(
                model=self.model,
                contents=converted_messages,
                config=genai_types.GenerateContentConfig(**config_params) if config_params else None
            )

            for chunk in response:
                if hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text

                # 尝试提取usage（可能在最后一个chunk）
                if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                    usage = {
                        "prompt_tokens": chunk.usage_metadata.prompt_token_count or 0,
                        "completion_tokens": chunk.usage_metadata.candidates_token_count or 0,
                        "total_tokens": chunk.usage_metadata.total_token_count or 0,
                    }

            latency_ms = int((time.time() - start_time) * 1000)

            self.last_stats = StreamStats(
                model=self.model,
                usage=usage,
                latency_ms=latency_ms
            )

        except Exception as e:
            raise HelloAgentsException(f"Gemini API流式调用失败: {str(e)}")
        finally:
            close = getattr(response, "close", None)
            if close:
                close()


    def invoke_with_tools(self, messages: List[Dict], tools: List[Dict], **kwargs) -> LLMToolResponse:
        """工具调用（Gemini格式）"""
        self._get_client()

        from google.genai import types as genai_types

        system_instruction, converted_messages = self._convert_messages(messages)
        tool_choice = self._convert_tool_choice(kwargs.pop("tool_choice", None))

        start_time = time.time()
        try:
            # 转换工具格式为Gemini格式
            gemini_tools = []
            for tool in tools:
                if tool.get("type") == "function":
                    func = tool["function"]
                    gemini_tools.append(
                        genai_types.FunctionDeclaration(
                            name=func["name"],
                            description=func.get("description", ""),
                            parameters_json_schema=func.get("parameters", {})
                        )
                    )

            config_params = dict(kwargs)
            if "temperature" in kwargs:
                config_params["temperature"] = kwargs.pop("temperature")
            if "max_tokens" in kwargs:
                config_params["max_output_tokens"] = config_params.pop("max_tokens")
            if gemini_tools:
                config_params["tools"] = [genai_types.Tool(function_declarations=gemini_tools)]
            if system_instruction:
                config_params["system_instruction"] = system_instruction
            if tool_choice:
                config_params["tool_config"] = tool_choice

            response = self._client.models.generate_content(
                model=self.model,
                contents=converted_messages,
                config=genai_types.GenerateContentConfig(**config_params) if config_params else None
            )
            latency_ms = int((time.time() - start_time) * 1000)

            content = response.text if hasattr(response, 'text') else ""
            tool_calls = []

            # 解析 Gemini 工具调用
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        tool_calls.append(ToolCall(
                            id=f"call_{int(time.time()*1000)}",  # Gemini 没有显式的 call_id，生成一个
                            name=part.function_call.name,
                            arguments=json.dumps(dict(part.function_call.args))
                        ))

            usage = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count or 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count or 0,
                    "total_tokens": response.usage_metadata.total_token_count or 0
                }

            return LLMToolResponse(
                finish_reason=getattr(response.candidates[0], "finish_reason", None) if getattr(response, "candidates", None) else None,
                content=content if content else None,
                tool_calls=tool_calls,
                model=self.model,
                usage=usage,
                latency_ms=latency_ms
            )

        except Exception as e:
            raise HelloAgentsException(f"Gemini工具调用失败: {str(e)}")


def create_adapter(api_key, base_url, timeout, model, provider=None) -> BaseLLMAdapter:
    """显式指定的协议优先于主机名识别，代理地址也遵循此规则。"""
    adapters = {"openai": OpenAIAdapter, "anthropic": AnthropicAdapter, "gemini": GeminiAdapter}
    aliases = {"deepseek": "openai", "qwen": "openai", "ollama": "openai", "claude": "anthropic", "google": "gemini"}
    if provider is not None:
        if not isinstance(provider, str):
            raise TypeError("provider must be a protocol name")
        provider = aliases.get(provider.lower(), provider.lower())
        if provider not in adapters:
            raise ValueError("provider must be openai, anthropic or gemini")
    else:
        host = (urlparse(base_url or "").hostname or "").lower()
        provider = ("anthropic" if host == "anthropic.com" or host.endswith(".anthropic.com")
                    else "gemini" if host == "googleapis.com" or host.endswith(".googleapis.com")
                    else "openai")
    return adapters[provider](api_key, base_url, timeout, model)
