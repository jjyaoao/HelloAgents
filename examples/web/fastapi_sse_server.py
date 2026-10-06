"""运行 python -m examples.web.fastapi_sse_server，浏览 http://127.0.0.1:8000。
默认离线；设置 HELLOAGENTS_DEMO_LIVE=1 并配置 LLM 环境变量后使用真实模型。
"""

import os
from pathlib import Path
from contextlib import aclosing
from typing import Literal
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from hello_agents import (
    SimpleAgent,
    ReActAgent,
    ReflectionAgent,
    PlanSolveAgent,
    ToolRegistry,
)
from hello_agents.tools.builtin import CalculatorTool
from hello_agents.core.streaming import StreamEvent, StreamEventType
from examples._support import demo_config, demo_llm, response, tool_response


class AgentRequest(BaseModel):
    input: str = Field(min_length=1, max_length=10000)
    agent_type: Literal["simple", "react", "reflection", "plan"] = "simple"


def build_agent(kind):
    # 每次请求独立创建 Agent、工具注册表和模型会话。
    fixtures = [response("离线演示回答：已收到任务。")]
    if kind == "reflection":
        fixtures.append(response("无需改进"))
    elif kind == "plan":
        fixtures.insert(0, tool_response("generate_plan", {"steps": ["回答用户问题"]}))
    registry = ToolRegistry()
    registry.register_tool(CalculatorTool())
    cls = dict(
        simple=SimpleAgent,
        react=ReActAgent,
        reflection=ReflectionAgent,
        plan=PlanSolveAgent,
    )[kind]
    return cls(
        "SSE-" + kind,
        demo_llm(fixtures, live=os.getenv("HELLOAGENTS_DEMO_LIVE") == "1"),
        tool_registry=registry,
        config=demo_config(),
    )


def create_app(agent_factory=build_agent):
    app = FastAPI(title="HelloAgents SSE")

    @app.get("/")
    async def root():
        return FileResponse(Path(__file__).with_name("sse_client.html"))

    @app.post("/agent/stream")
    async def agent_stream(request: AgentRequest):
        agent = agent_factory(request.agent_type)

        async def events():
            try:
                async with aclosing(agent.arun_stream(request.input)) as source:
                    async for event in source:
                        yield event.to_sse()
            except Exception:
                # 不把凭据、服务端路径或上游原始错误发送给浏览器。
                yield StreamEvent.create(
                    StreamEventType.ERROR,
                    agent.name,
                    message="运行失败，请检查服务端配置与日志。",
                ).to_sse()
            finally:
                close = getattr(type(agent.llm), "aclose", None)
                if close is not None:
                    await agent.llm.aclose()

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
