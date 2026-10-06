"""固定相同批次比较并发上限；人工延迟不代表真实模型性能。"""

import asyncio
import time
from hello_agents import ReActAgent, ToolRegistry
from hello_agents.tools import Tool, ToolResponse
from hello_agents.core.llm_response import ToolCall
from examples._support import demo_config, ScriptedLLM, response


class DelayedTool(Tool):
    def __init__(self, name, counters):
        super().__init__(name, "等待后返回，用于测试调度")
        self.counters = counters

    def get_parameters(self):
        return []

    def run(self, parameters):
        raise RuntimeError("使用原生异步入口 arun")

    async def arun(self, parameters):
        self.counters["active"] += 1
        self.counters["peak"] = max(self.counters["peak"], self.counters["active"])
        try:
            await asyncio.sleep(0.05)
            self.counters["completed"] += 1
            return ToolResponse.success(text=self.name + " 完成")
        finally:
            self.counters["active"] -= 1


async def measure(limit):
    counters = dict(active=0, peak=0, completed=0)
    registry = ToolRegistry()
    calls = []
    for i in range(5):
        name = f"wait_{i}"
        registry.register_tool(DelayedTool(name, counters))
        calls.append(ToolCall(str(i), name, "{}"))
    agent = ReActAgent(
        "并发实验",
        ScriptedLLM([response(calls=calls), response("完成")]),
        registry,
        config=demo_config(max_concurrent_tools=limit),
    )
    start = time.perf_counter()
    await agent.arun("执行全部等待任务")
    assert counters["completed"] == 5 and counters["active"] == 0
    assert counters["peak"] == limit and agent.last_run.status == "completed"
    return dict(limit=limit, elapsed=round(time.perf_counter() - start, 3), **counters)


async def main():
    for limit in (1, 2):
        print(await measure(limit))


if __name__ == "__main__":
    asyncio.run(main())
