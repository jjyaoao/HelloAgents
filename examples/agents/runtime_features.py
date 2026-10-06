"""无需密钥的组件与运行协议示例。

ScriptedLLM 是预设响应的协议替身，不是模型。SQLite、工具执行、上下文组装、
会话保存恢复和流式事件均运行真实框架代码。默认使用临时目录；--workspace 保留产物。
"""

import argparse
import asyncio
from contextlib import aclosing
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from hello_agents import AgentComponents, Config, SimpleAgent, ToolRegistry
from hello_agents.context import ContextBuilder, ContextConfig, MemoryContextProvider
from hello_agents.core.llm_response import LLMToolResponse, ToolCall
from hello_agents.core.session_store import SessionStore
from hello_agents.core.streaming import StreamEventType
from hello_agents.memory import MemoryStore
from hello_agents.retrieval import RAGStore
from hello_agents.tools import Tool, ToolParameter, ToolResponse
from hello_agents.tools.builtin import RAGTool


class ScriptedLLM:
    """明确的离线测试替身：按序返回给定响应，同时捕获实际模型输入。"""

    model = "offline-protocol-fixture"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []
        self.closed_streams = 0

    def invoke(self, messages, **kwargs):
        self.requests.append(
            {"messages": deepcopy(messages), "kwargs": deepcopy(kwargs)}
        )
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response

    def invoke_with_tools(self, messages, tools, **kwargs):
        return self.invoke(messages, tools=tools, **kwargs)

    async def astream_invoke_with_tools(self, messages, tools, **kwargs):
        try:
            response = self.invoke_with_tools(messages, tools, **kwargs)
            if response.content:
                yield response.content
            yield response
        finally:
            self.closed_streams += 1


class RouteTool(Tool):
    """演示结构化数组与真正 await 的异步入口；距离为虚构教学数据。"""

    def __init__(self):
        super().__init__("route_distance", "查询教学线路步行距离；线路取值见参数")
        self.executions = 0

    def get_parameters(self):
        return [
            ToolParameter(
                name="legs",
                type="array",
                description="需要核对的线路列表",
                json_schema={
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "route": {"type": "string", "enum": ["museum", "lake"]}
                        },
                        "required": ["route"],
                        "additionalProperties": False,
                    },
                },
            )
        ]

    def run(self, parameters):
        distances = {"museum": 3, "lake": 7}
        legs = parameters.get("legs")
        if (
            not isinstance(legs, list)
            or not legs
            or any(
                not isinstance(leg, dict)
                or set(leg) != {"route"}
                or not isinstance(leg["route"], str)
                or leg["route"] not in distances
                for leg in legs
            )
        ):
            return ToolResponse.error("INVALID_PARAM", "legs 必须包含合法线路对象")
        self.executions += 1
        return ToolResponse.success(
            "取得教学线路距离",
            data={
                "routes": [
                    {"route": leg["route"], "walking_km": distances[leg["route"]]}
                    for leg in legs
                ],
                "source": "fixture://routes/v1",
            },
        )

    async def arun(self, parameters):
        await asyncio.sleep(0)  # 真正的异步调度点；没有网络请求。
        return self.run(parameters)


def response(text="", calls=(), reason="stop"):
    return LLMToolResponse(text, list(calls), ScriptedLLM.model, finish_reason=reason)


def build_agent(workspace, llm, memory=None):
    """显式组合会话、工具与上下文；可传真实 LLM，但默认例子不会创建客户端。"""
    workspace = Path(workspace)
    registry = ToolRegistry()
    registry.register_tool(RouteTool())
    registry.register_tool(RAGTool(RAGStore(workspace / "knowledge.sqlite")))
    config = Config(
        trace_enabled=False,
        session_enabled=False,
        skills_enabled=False,
        subagent_enabled=False,
        todowrite_enabled=False,
        devlog_enabled=False,
        tool_output_dir=str(workspace / "tool-output"),
    )
    return SimpleAgent(
        "旅行协议示例",
        llm,
        system_prompt="依据返回资料作答；教学资料不代表真实旅游信息。",
        config=config,
        tool_registry=registry,
        components=AgentComponents(
            session_store=SessionStore(str(workspace / "sessions")), skill_loader=None
        ),
        context_builder=ContextBuilder(ContextConfig(max_tokens=6000)),
        context_providers=(
            [MemoryContextProvider(memory, required=True)] if memory is not None else []
        ),
    )


async def consume_events(agent, text):
    events = []
    async with aclosing(agent.arun_stream(text)) as stream:
        async for event in stream:
            events.append(event)
    return events


async def interrupt_save_resume(workspace):
    """工具写入已取得回执后关闭流，保存并恢复；恢复阶段不重放写请求。"""
    workspace = Path(workspace)
    note_path = workspace / "confirmed-note.txt"
    writes = []

    async def record_note(text):
        await asyncio.sleep(0)
        with note_path.open("a", encoding="utf-8") as target:
            target.write(text + "\n")
        writes.append(text)
        return ToolResponse.success(
            "已保存本地教学记录", data={"path": str(note_path), "saved": True}
        )

    request = ToolCall("note-1", "record_note", '{"input":"已确认步行偏好"}')
    interrupted = build_agent(workspace, ScriptedLLM([response(calls=[request])]))
    interrupted.tool_registry.register_function(record_note)
    async with aclosing(interrupted.arun_stream("保存一条教学记录")) as stream:
        async for event in stream:
            if event.type == StreamEventType.TOOL_CALL_FINISH:
                break
    assert interrupted.last_run.status == "cancelled"
    saved = interrupted.save_session("interrupted-write")

    llm = ScriptedLLM([response("已有写入回执，继续处理，不重复保存。")])
    restored = build_agent(workspace, llm)
    restored.tool_registry.register_function(record_note)
    restored.load_session(saved)
    await restored.arun("先检查已有回执，再继续，不重复写入")
    receipts = [
        m for m in llm.requests[0]["messages"] if m.get("tool_call_id") == "note-1"
    ]
    assert len(receipts) == 1
    assert json.loads(receipts[0]["content"])["data"]["saved"] is True
    assert len(writes) == 1 and restored.last_run.tool_calls == 0
    return {
        "interrupted_status": interrupted.last_run.status,
        "resumed_status": restored.last_run.status,
        "tool_receipt_preserved": True,
        "writes_this_run": len(writes),
        "resume_tool_calls": restored.last_run.tool_calls,
        "session_path": str(saved),
    }


def run_demo(workspace):
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    knowledge = RAGStore(workspace / "knowledge.sqlite")
    knowledge.add_document(
        "示例博物馆节假日需要预约。", source="fixture://museum", document_id="museum"
    )
    hit = knowledge.search("博物馆节假日预约")[0]
    assert knowledge.read_chunk(hit.chunk_id).content == hit.content

    memory = MemoryStore(workspace / "memory.sqlite", user_id="alice", task_id="trip")
    old = memory.add("每天步行不超过八公里", source="user:1")
    current = memory.revise(old.memory_id, "每天步行不超过五公里", source="user:2")
    other = MemoryStore(workspace / "memory.sqlite", user_id="bob", task_id="trip")
    assert other.search() == []

    call = ToolCall(
        "route-1", "route_distance", '{"legs":[{"route":"museum"},{"route":"lake"}]}'
    )
    llm = ScriptedLLM(
        [
            response(calls=[call], reason="tool_calls"),
            response("教学线路中，博物馆线为三公里。"),
        ]
    )
    agent = build_agent(workspace, llm, memory)
    answer = agent.run("比较两条线路的步行距离")
    assert agent.last_run.status == "completed"
    assert agent.last_run.tool_calls == 1
    assert "五公里" in json.dumps(llm.requests[0]["messages"], ensure_ascii=False)
    first_run = asdict(agent.last_run)
    tool_result = next(
        json.loads(m["content"])
        for m in llm.requests[1]["messages"]
        if m.get("tool_call_id") == "route-1"
    )
    session_path = agent.save_session("travel-protocol")

    resumed_llm = ScriptedLLM([response("继续采用五公里以内的教学线路。")])
    restored = build_agent(workspace, resumed_llm, memory)
    restored.load_session(session_path)
    events = asyncio.run(consume_events(restored, "继续规划"))
    assert events[-1].type == StreamEventType.AGENT_FINISH
    assert any(
        m.get("tool_call_id") == "route-1" for m in resumed_llm.requests[0]["messages"]
    )

    # 用同一运行器观察正常结束之外的三种状态；不伪装为真实服务响应。
    exhausted = build_agent(
        workspace,
        ScriptedLLM([response(calls=[call]), response("次数达到上限的总结。")]),
    )
    exhausted.max_tool_iterations = 1
    exhausted.run("检查上限")
    limited = build_agent(
        workspace, ScriptedLLM([response("未完整输出", reason="length")])
    )
    limited.run("检查输出截断")
    failed = build_agent(workspace, ScriptedLLM([RuntimeError("离线模拟服务错误")]))
    try:
        failed.run("检查失败")
    except RuntimeError:
        pass

    memory.retract(current.memory_id)
    reopened = MemoryStore(workspace / "memory.sqlite", user_id="alice", task_id="trip")
    assert reopened.get(current.memory_id, include_inactive=True).status == "retracted"
    result = {
        "mode": "offline protocol fixture; not a model quality evaluation",
        "answer": answer,
        "first_run": first_run,
        "tool_result": tool_result,
        "evidence": {
            "source": hit.source,
            "version": hit.version,
            "content": hit.content,
        },
        "context": agent.last_context_diagnostics,
        "session_path": str(session_path),
        "resumed_tool_pair": True,
        "stream_events": [event.type.value for event in events],
        "memory_old_status": reopened.get(old.memory_id, include_inactive=True).status,
        "memory_current_status": reopened.get(
            current.memory_id, include_inactive=True
        ).status,
        "other_user_records": len(other.search()),
        "statuses": {
            "limit": exhausted.last_run.status,
            "output": limited.last_run.status,
            "error": failed.last_run.status,
        },
        "interrupted_resume": asyncio.run(interrupt_save_resume(workspace)),
    }
    (workspace / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        type=Path,
        help="保留 SQLite、会话和 result.json；默认使用临时目录",
    )
    args = parser.parse_args()
    if args.workspace:
        print(json.dumps(run_demo(args.workspace), ensure_ascii=False, indent=2))
    else:
        with TemporaryDirectory(prefix="helloagents-runtime-") as directory:
            print(json.dumps(run_demo(directory), ensure_ascii=False, indent=2))
            print("临时目录将在示例退出时清理；保留结果请指定 --workspace。")


if __name__ == "__main__":
    main()
