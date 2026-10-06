"""执行预算工具任务，检查实际 JSONL 轨迹；可用 --live 接入真实模型。"""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from hello_agents import SimpleAgent, ToolRegistry
from hello_agents.tools.builtin import CalculatorTool
from examples._support import demo_config, demo_llm, response, tool_response


def run(directory):
    registry = ToolRegistry()
    registry.register_tool(CalculatorTool())
    llm = demo_llm(
        [
            tool_response("python_calculator", {"input": "1500 - 800"}),
            response("预算还剩 700 元。"),
        ]
    )
    agent = SimpleAgent(
        "预算核对",
        llm,
        tool_registry=registry,
        config=demo_config(trace_enabled=True, trace_dir=str(directory)),
    )
    print(agent.run("使用计算器，核对 1500 元预算扣除 800 元住宿后还有多少。"))
    assert agent.last_run.status == "completed" and agent.last_run.tool_calls >= 1
    trace = agent.trace_logger
    events = [
        json.loads(line)
        for line in Path(trace.jsonl_path).read_text(encoding="utf-8").splitlines()
    ]
    assert any(item["event"] == "tool_result" for item in events)
    assert Path(trace.html_path).is_file()
    print("记录的事件：", [item["event"] for item in events])
    print("模型用量来自服务返回；离线预设响应的零值不能用于估算实际费用。")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.workspace:
        run(args.workspace)
    else:
        with TemporaryDirectory() as directory:
            run(Path(directory))


if __name__ == "__main__":
    main()
