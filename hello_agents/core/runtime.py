"""阻塞、异步与流式 Agent 入口共用同一工具循环。

本模块负责执行顺序与终止条件。Agent 提供提示词、上下文
选择与工具调度，展示层消费同一组事件。
"""

import asyncio
import json
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from contextlib import aclosing, asynccontextmanager
from .llm_response import LLMToolResponse


@dataclass
class RunResult:
    answer: str = ""
    status: str = "running"
    stop_reason: str | None = None
    model_calls: int = 0
    tool_calls: int = 0
    usage: dict[str, Any] = field(default_factory=dict)


class EmptyModelResponse(RuntimeError):
    """服务商既未返回可见文本，也未返回工具请求。"""


def close_interrupted_turn(messages):
    """保留回执并关闭待处理请求，不将未知结果标记为执行失败。

    同步工具被取消后，仍可能在线程中完成执行。因此，缺少
    回执表示结果未知，不能据此直接重试写入操作。
    """
    closed = []
    pending = {}

    def flush():
        for call_id in pending:
            closed.append(
                {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(
                        {
                            "status": "error",
                            "execution_status": "unknown",
                            "text": "运行已中断，未取得此请求的执行回执。请先核实外部状态，不要直接重试有副作用的操作。",
                        },
                        ensure_ascii=False,
                    ),
                }
            )
        pending.clear()

    for message in messages:
        if message["role"] != "tool":
            flush()
        else:
            pending.pop(message.get("tool_call_id"), None)
        closed.append(message)
        for call in message.get("tool_calls", []):
            pending[call["id"]] = call
    flush()
    closed.append(
        {"role": "assistant", "content": "本轮运行已中断，任务尚未确认完成。"}
    )
    return closed


def stopped_by_limit(reason):
    value = getattr(reason, "value", reason)
    return str(value).lower() in {"length", "max_tokens", "max_output_tokens"}


def sync_events(iterator):
    """在普通同步 Python 代码中消费异步事件源。"""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise RuntimeError(
            "同步入口不能在运行中的事件循环内调用，请使用 await arun 或 arun_stream"
        )
    loop = asyncio.new_event_loop()
    try:
        while True:
            try:
                yield loop.run_until_complete(anext(iterator))
            except StopAsyncIteration:
                return
    finally:
        loop.run_until_complete(iterator.aclose())
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.run_until_complete(loop.shutdown_default_executor())
        loop.close()


@asynccontextmanager
async def deadline(seconds):
    task = asyncio.current_task()
    cancelling = task.cancelling() if hasattr(task, "cancelling") else 0
    expired = False

    def cancel():
        nonlocal expired
        expired = True
        task.cancel()

    handle = asyncio.get_running_loop().call_later(seconds, cancel)
    try:
        yield
    except asyncio.CancelledError:
        if expired:
            if not hasattr(task, "uncancel") or task.uncancel() <= cancelling:
                raise TimeoutError("执行超过配置时限") from None
        raise
    finally:
        handle.cancel()


async def model_events(llm, messages, schemas, stream, kwargs):
    messages = deepcopy(messages)
    kwargs = dict(kwargs)
    if schemas:
        kwargs.setdefault("tool_choice", "auto")
    else:
        kwargs.pop("tool_choice", None)
    # 检查类本身：Mock 对象与透明记录包装器不能通过
    # __getattr__ 动态伪造的能力，静默绕过自身的 invoke 方法。
    native = getattr(type(llm), "astream_invoke_with_tools", None)
    if stream and native:
        final = None
        async with aclosing(
            llm.astream_invoke_with_tools(messages, schemas, **kwargs)
        ) as source:
            async for item in source:
                if isinstance(item, str):
                    yield {"kind": "chunk", "text": item}
                else:
                    final = item
        if final is None:
            raise EmptyModelResponse("流未返回完整模型响应")
        yield {"kind": "response", "response": final}
    elif stream and not schemas and getattr(type(llm), "astream_invoke", None):
        chunks = []
        async with aclosing(llm.astream_invoke(messages, **kwargs)) as source:
            async for chunk in source:
                chunks.append(chunk)
                yield {"kind": "chunk", "text": chunk}
        stats = getattr(llm, "last_call_stats", None)
        yield {
            "kind": "response",
            "response": LLMToolResponse(
                "".join(chunks),
                [],
                llm.model,
                usage=getattr(stats, "usage", {}) or {},
                finish_reason=getattr(stats, "finish_reason", None),
            ),
        }
    else:
        method = "invoke_with_tools" if schemas else "invoke"
        params = dict(messages=messages, **kwargs)
        if schemas:
            params["tools"] = schemas
        if getattr(type(llm), "a" + method, None):
            response = await getattr(llm, "a" + method)(**params)
        else:
            response = await asyncio.to_thread(getattr(llm, method), **params)
        if stream and getattr(response, "content", None):
            yield {"kind": "chunk", "text": response.content}
        yield {"kind": "response", "response": response}


async def turn_events(agent, messages, packets, *, stream, kwargs):
    schemas = agent._build_tool_schemas() if agent.enable_tool_calling else []
    result = agent.last_run
    limit = agent.max_tool_iterations if schemas else 1
    for step in range(limit + (1 if schemas else 0)):
        # 保留最后一次总结调用，但将结果标记为预算耗尽，
        # 不能据此认为任务已验证完成。
        exhausted = step == limit
        active_schemas = [] if exhausted else schemas
        model_messages = agent._prepare_context(messages, packets, active_schemas)
        if getattr(agent, "_parallel_tools", False):
            yield {
                "kind": "step_start",
                "phase": "tool_loop",
                "step": step + 1,
                "max_steps": limit,
            }
        response = None
        remaining = agent.config.llm_async_timeout
        async with aclosing(
            model_events(agent.llm, model_messages, active_schemas, stream, kwargs)
        ) as events:
            while True:
                started = asyncio.get_running_loop().time()
                try:
                    async with deadline(remaining):
                        event = await anext(events)
                except StopAsyncIteration:
                    break
                remaining -= asyncio.get_running_loop().time() - started
                if event["kind"] == "response":
                    response = event["response"]
                else:
                    yield dict(event, step=step + 1)
        result.model_calls += 1
        usage = getattr(response, "usage", None) or {}
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            if key in usage:
                result.usage[key] = result.usage.get(key, 0) + usage[key]
        result.stop_reason = getattr(response, "finish_reason", None)
        calls = getattr(response, "tool_calls", []) or []
        text = getattr(response, "content", None) or ""
        reasoning = getattr(response, "reasoning_content", None)
        private_fields = {"reasoning_content": reasoning} if isinstance(reasoning, str) and reasoning else {}
        yield {
            "kind": "model",
            "usage": usage,
            "step": result.model_calls,
            "content": text,
            "finish_reason": result.stop_reason,
            "tool_count": len(calls),
        }
        if stopped_by_limit(result.stop_reason):
            result.answer, result.status = text, "output_limit"
            if text:
                messages.append({"role": "assistant", "content": text, **private_fields})
            return
        if not calls or exhausted:
            if not text.strip():
                raise EmptyModelResponse("模型没有返回公开回答或工具请求")
            result.answer = text
            result.status = "max_iterations" if exhausted else "completed"
            messages.append({"role": "assistant", "content": text, **private_fields})
            return
        ids = [call.id for call in calls]
        if any(not isinstance(i, str) or not i.strip() for i in ids) or len(
            set(ids)
        ) != len(ids):
            raise ValueError("工具请求 ID 必须非空且在同一批次内唯一")
        messages.append(
            {
                "role": "assistant",
                "content": text or None,
                **private_fields,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": call.arguments},
                    }
                    for call in calls
                ],
            }
        )
        if (
            getattr(agent, "_parallel_tools", False)
            and len(calls) > 1
            and not any(c.name in agent._builtin_tools for c in calls)
        ):
            for call in calls:
                yield {
                    "kind": "tool_start",
                    "name": call.name,
                    "id": call.id,
                    "arguments": call.arguments,
                    "step": step + 1,
                }

            def record(call_id, output):
                result.tool_calls += 1
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": output["content"],
                    }
                )

            outputs = await agent._execute_tools_async(
                calls, current_step=step + 1, on_result=record
            )
            for name, call_id, output in outputs:
                yield {
                    "kind": "tool_finish",
                    "name": name,
                    "id": call_id,
                    "result": output["content"],
                    "step": step + 1,
                }
            yield {
                "kind": "step_finish",
                "phase": "tool_loop",
                "step": step + 1,
                "tool_calls": len(calls),
            }
            continue
        finished = None
        for call in calls:
            yield {
                "kind": "tool_start",
                "name": call.name,
                "id": call.id,
                "arguments": call.arguments,
                "step": step + 1,
            }
            try:
                args = json.loads(call.arguments)
                if not isinstance(args, dict):
                    raise ValueError("工具参数必须是 JSON 对象")
                if finished is not None:
                    output = json.dumps(
                        {"status": "error", "text": "本轮已经结束，未执行此请求"},
                        ensure_ascii=False,
                    )
                elif call.name in getattr(agent, "_builtin_tools", set()):
                    value = agent._handle_builtin_tool(call.name, args)
                    output = value["content"]
                    if value.get("finished"):
                        finished = value["final_answer"]
                else:
                    async with deadline(agent.config.tool_async_timeout):
                        output = await agent._aexecute_tool_call(call.name, args)
            except (ValueError, TypeError) as exc:
                output = json.dumps(
                    {"status": "error", "text": str(exc)}, ensure_ascii=False
                )
            result.tool_calls += 1
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": output}
            )
            yield {
                "kind": "tool_finish",
                "name": call.name,
                "id": call.id,
                "result": output,
                "step": step + 1,
            }
        if finished is not None:
            result.answer, result.status = finished, "completed"
            messages.append({"role": "assistant", "content": finished})
            if stream:
                yield {"kind": "chunk", "text": finished}
            return
        if getattr(agent, "_parallel_tools", False):
            yield {
                "kind": "step_finish",
                "phase": "tool_loop",
                "step": step + 1,
                "tool_calls": len(calls),
            }
