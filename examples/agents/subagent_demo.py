"""只读子任务、独立历史和结果回传；python -m examples.agents.subagent_demo [--live]。"""

from pathlib import Path
from tempfile import TemporaryDirectory
from hello_agents import SimpleAgent, ToolRegistry
from hello_agents.tools.builtin import ReadTool, WriteTool, TaskTool
from hello_agents.tools.response import ToolStatus
from examples._support import demo_config, demo_llm, response, tool_response


class AuditedReadTool(ReadTool):
    """保留本例实际读到的回执，避免只凭模型回答判断读取成功。"""

    def __init__(self, directory):
        super().__init__(project_root=directory)
        self.receipts = []

    def run(self, parameters):
        result = super().run(parameters)
        self.receipts.append(result)
        return result


def main():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "preferences.md").write_text(
            "杭州两日游；预算 1500 元；步行每天不超过 5 公里。", encoding="utf-8"
        )
        registry = ToolRegistry()
        reader = AuditedReadTool(directory)
        registry.register_tool(reader)
        registry.register_tool(WriteTool(project_root=directory))
        children = []

        def factory(agent_type):
            if agent_type != "simple":
                raise ValueError("本例只构建 simple 子代理")
            llm = demo_llm(
                [
                    tool_response("Read", {"path": str(root / "preferences.md")}),
                    response("约束：杭州两日游，1500 元，每天步行至多 5 公里。"),
                ]
            )
            child = SimpleAgent(
                "偏好核对", llm, tool_registry=registry.fork(), config=demo_config()
            )
            children.append(child)
            return child

        task = TaskTool(factory, registry, config=demo_config())
        result = task.run(
            dict(
                task="读取 preferences.md 并整理旅行约束，不修改文件。",
                agent_type="simple",
                tool_filter="readonly",
                max_steps=3,
            )
        )
        assert result.status == ToolStatus.SUCCESS, result.text
        assert "Read" in result.data["tools_used"]
        assert children[0].last_run is None
        assert children[0].get_history() == []
        assert any(
            receipt.status == ToolStatus.SUCCESS
            and "1500" in receipt.data.get("content", "")
            for receipt in reader.receipts
        ), "必须核对实际读取回执，不能只相信模型最终回答"
        assert registry.get_tool("Write") is not None
        assert (root / "preferences.md").read_text(encoding="utf-8").startswith("杭州")
        print(result.text)
        print("子任务使用独立历史；工具过滤只限制注册表能力，不等于操作系统沙箱。")


if __name__ == "__main__":
    main()
