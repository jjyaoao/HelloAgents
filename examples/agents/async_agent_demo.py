"""python -m examples.agents.async_agent_demo [--live]"""

import asyncio
from contextlib import aclosing
from hello_agents import SimpleAgent, ToolRegistry
from hello_agents.core.streaming import StreamEventType
from hello_agents.tools.builtin import CalculatorTool
from examples._support import demo_config, demo_llm, response, tool_response


def build_agent():
    registry = ToolRegistry()
    registry.register_tool(CalculatorTool())
    llm = demo_llm(
        [
            tool_response("python_calculator", {"input": "(320 + 80) * 2"}),
            response("两人的费用合计 800 元。"),
        ]
    )
    return SimpleAgent("预算助手", llm, tool_registry=registry, config=demo_config())


async def main():
    prompt = "请调用计算器计算两人各花 320 元住宿、80 元交通的总费用。"
    calls = []

    async def on_tool_call(event):
        calls.append(event)
        print("工具事件：", event.data)

    agent = build_agent()
    print(await agent.arun(prompt, on_tool_call=on_tool_call))
    assert agent.last_run.status == "completed" and calls
    streamed = build_agent()
    async with aclosing(streamed.arun_stream(prompt)) as events:
        async for event in events:
            if event.type == StreamEventType.LLM_CHUNK:
                print(event.data["chunk"], end="", flush=True)
            elif event.type == StreamEventType.AGENT_FINISH:
                print("\n运行结果：", event.data)
    assert streamed.last_run.status == "completed"


if __name__ == "__main__":
    asyncio.run(main())
