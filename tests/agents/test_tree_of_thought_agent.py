"""Tests for TreeOfThoughtAgent"""

from unittest.mock import MagicMock
import pytest

from hello_agents.agents.tree_of_thought_agent import (
    TreeOfThoughtAgent,
    ThoughtNode,
)
from hello_agents.tools.base import Tool, ToolParameter
from typing import Dict, Any, List


def make_mock_llm(responses: dict = None):
    llm = MagicMock()
    llm.provider = "test"

    def invoke(messages, **kwargs):
        content = messages[-1]["content"] if messages else ""
        if responses:
            for pattern, response in responses.items():
                if pattern in content:
                    return response
        return ""

    llm.invoke = invoke
    return llm


class TestThoughtNode:
    def test_create_node(self):
        node = ThoughtNode(content="test", depth=1, score=8.5)
        assert node.content == "test"
        assert node.depth == 1
        assert node.score == 8.5
        assert node.parent is None
        assert node.children == []
        assert node.solution is None
        assert node.visits == 0
        assert node.value == 0.0

    def test_add_child(self):
        parent = ThoughtNode(content="parent", depth=0)
        child = ThoughtNode(content="child", depth=1)
        result = parent.add_child(child)
        assert result is child
        assert child.parent is parent
        assert child in parent.children

    def test_get_path(self):
        root = ThoughtNode(content="ROOT", depth=0)
        n1 = ThoughtNode(content="step1", depth=1, parent=root)
        n2 = ThoughtNode(content="step2", depth=2, parent=n1)
        root.children = [n1]
        n1.children = [n2]

        path = n2.get_path()
        assert path == ["ROOT", "step1", "step2"]

    def test_path_str(self):
        root = ThoughtNode(content="ROOT", depth=0)
        n1 = ThoughtNode(content="step1", depth=1, parent=root)
        root.children = [n1]

        assert n1.path_str(" -> ") == "ROOT -> step1"

    def test_get_ancestor(self):
        root = ThoughtNode(content="ROOT", depth=0)
        n1 = ThoughtNode(content="L1", depth=1, parent=root)
        n2 = ThoughtNode(content="L2", depth=2, parent=n1)
        root.children = [n1]
        n1.children = [n2]

        assert n2.get_ancestor(0) is root
        assert n2.get_ancestor(1) is n1
        assert n2.get_ancestor(3) is None

    def test_is_leaf(self):
        parent = ThoughtNode(content="p", depth=0)
        child = ThoughtNode(content="c", depth=1)
        parent.add_child(child)
        assert not parent.is_leaf()
        assert child.is_leaf()

    def test_best_child_ucb(self):
        parent = ThoughtNode(content="p", depth=0)
        c1 = ThoughtNode(content="c1", depth=1, score=8.0)
        c2 = ThoughtNode(content="c2", depth=1, score=6.0)
        parent.add_child(c1)
        parent.add_child(c2)

        parent.visits = 10
        c1.visits = 5
        c1.value = 40.0
        c2.visits = 5
        c2.value = 30.0

        best = parent.best_child(exploration_weight=0)
        assert best is c1

    def test_best_child_unvisited(self):
        parent = ThoughtNode(content="p", depth=0)
        c1 = ThoughtNode(content="c1", depth=1)
        c2 = ThoughtNode(content="c2", depth=1)
        parent.add_child(c1)
        parent.add_child(c2)
        parent.visits = 1

        best = parent.best_child(exploration_weight=1.0)
        assert best in (c1, c2)

    def test_best_child_no_children(self):
        leaf = ThoughtNode(content="leaf", depth=1)
        assert leaf.best_child() is None


class TestTreeOfThoughtAgent:
    def test_init_defaults(self):
        llm = make_mock_llm()
        agent = TreeOfThoughtAgent(name="test_tot", llm=llm)
        assert agent.name == "test_tot"
        assert agent.max_depth == 3
        assert agent.num_branches == 3
        assert agent.top_k == 2
        assert agent.strategy == "bfs"
        assert agent.max_iterations == 50

    def test_init_custom(self):
        llm = make_mock_llm()
        agent = TreeOfThoughtAgent(
            name="custom_tot",
            llm=llm,
            max_depth=5,
            num_branches=4,
            top_k=3,
            strategy="dfs",
            max_iterations=100,
        )
        assert agent.max_depth == 5
        assert agent.num_branches == 4
        assert agent.top_k == 3
        assert agent.strategy == "dfs"
        assert agent.max_iterations == 100

    def test_init_invalid_strategy(self):
        llm = make_mock_llm()
        with pytest.raises(ValueError, match="Unsupported strategy"):
            TreeOfThoughtAgent(name="bad", llm=llm, strategy="invalid")

    def test_parse_thoughts(self):
        agent = TreeOfThoughtAgent(name="t", llm=make_mock_llm())
        text = "Thought 1: 分析题目条件\nThought 2: 寻找隐含假设\nThought 3: 验证结论"
        result = agent._parse_thoughts(text)
        assert len(result) == 3
        assert result[0] == "分析题目条件"
        assert result[1] == "寻找隐含假设"
        assert result[2] == "验证结论"

    def test_parse_evaluations(self):
        agent = TreeOfThoughtAgent(name="t", llm=make_mock_llm())
        text = """Evaluation 1: 8 - 相关性高
Evaluation 2: 6 - 可行性中等
Evaluation 3: 9 - 思路新颖"""
        result = agent._parse_evaluations(text, 3)
        assert len(result) == 3
        assert result == [8.0, 6.0, 9.0]

    def test_parse_evaluations_out_of_range(self):
        agent = TreeOfThoughtAgent(name="t", llm=make_mock_llm())
        text = "Evaluation 1: 15 - 超出范围"
        result = agent._parse_evaluations(text, 1)
        assert result == [10.0]

    def test_build_history_empty(self):
        agent = TreeOfThoughtAgent(name="t", llm=make_mock_llm())
        root = ThoughtNode(content="ROOT", depth=0)
        assert agent._build_history(root) == ""

    def test_build_history_with_steps(self):
        agent = TreeOfThoughtAgent(name="t", llm=make_mock_llm())
        root = ThoughtNode(content="ROOT", depth=0)
        n1 = ThoughtNode(content="分析", depth=1, parent=root)
        n2 = ThoughtNode(content="计算", depth=2, parent=n1)
        root.children = [n1]
        n1.children = [n2]

        history = agent._build_history(n2)
        assert "Step 1: 分析" in history
        assert "Step 2: 计算" in history

    def test_add_tool(self):
        llm = make_mock_llm()
        agent = TreeOfThoughtAgent(name="t", llm=llm)

        class SimpleCalcTool(Tool):
            def run(self, parameters: Dict[str, Any]) -> str:
                return "42"

            def get_parameters(self) -> List[ToolParameter]:
                return [ToolParameter(name="x", type="int", description="a number")]

        tool = SimpleCalcTool(name="calc", description="simple calculator")
        tool.auto_expand = False
        agent.add_tool(tool)
        assert tool.name in agent.tool_registry.list_tools()

    def test_run_bfs_no_solution(self):
        llm = make_mock_llm(
            responses={
                "思考方向": "Thought 1: 一个方向\nThought 2: 另一个方向",
                "评估": "Evaluation 1: 5\nEvaluation 2: 5",
            }
        )
        agent = TreeOfThoughtAgent(
            name="t", llm=llm, max_depth=1, num_branches=2, top_k=1
        )
        result = agent.run("test question")
        assert isinstance(result, str)

    def test_run_bfs_with_solution(self):
        llm = make_mock_llm(
            responses={
                "思考方向": "Thought 1: 一个方向\nThought 2: 另一个方向",
                "评估": "Evaluation 1: 9\nEvaluation 2: 5",
                "得出最终答案": "答案是42",
                "无法确定": "无法确定",
            }
        )

        def smart_invoke(messages, **kwargs):
            content = messages[-1]["content"] if messages else ""
            if "得出最终答案" in content:
                return "答案是42"
            if "无法确定" in content:
                return str(len(content))
            if "评估" in content:
                return "Evaluation 1: 9\nEvaluation 2: 5"
            if "思考方向" in content:
                return "Thought 1: 分析条件\nThought 2: 验证假设"
            return ""

        llm.invoke = smart_invoke
        agent = TreeOfThoughtAgent(
            name="t", llm=llm, max_depth=1, num_branches=2, top_k=1
        )
        result = agent.run("test question")
        assert "42" in result or "分析条件" in result

    def test_get_history(self):
        llm = make_mock_llm(
            responses={
                "思考方向": "Thought 1: 方向一",
                "评估": "Evaluation 1: 5",
            }
        )
        agent = TreeOfThoughtAgent(name="t", llm=llm, max_depth=1, num_branches=1)
        agent.run("test")
        history = agent.get_history()
        assert len(history) == 2
        assert history[0].content == "test"
        assert history[0].role == "user"

    def test_clear_history(self):
        llm = make_mock_llm()
        agent = TreeOfThoughtAgent(name="t", llm=llm)
        agent.add_message(type("Msg", (), {"content": "x", "role": "user"})())
        agent.clear_history()
        assert agent.get_history() == []

    def test_strategy_dfs(self):
        llm = make_mock_llm(
            responses={
                "思考方向": "Thought 1: 方向一\nThought 2: 方向二",
                "评估": "Evaluation 1: 7\nEvaluation 2: 5",
            }
        )
        agent = TreeOfThoughtAgent(
            name="t", llm=llm, max_depth=1, num_branches=2, strategy="dfs"
        )
        result = agent.run("test dfs")
        assert isinstance(result, str)

    def test_strategy_mcts(self):
        llm = make_mock_llm(
            responses={
                "思考方向": "Thought 1: 方向一",
                "评估": "Evaluation 1: 6",
            }
        )
        agent = TreeOfThoughtAgent(
            name="t",
            llm=llm,
            max_depth=1,
            num_branches=1,
            strategy="mcts",
            max_iterations=5,
        )
        result = agent.run("test mcts")
        assert isinstance(result, str)

    def test_run_with_custom_prompts(self):
        llm = make_mock_llm(
            responses={
                "custom": "Thought 1: 定制方向",
                "my_eval": "Evaluation 1: 8",
            }
        )
        custom = {
            "generate": "custom {question} {history} {num_branches}",
            "evaluate": "my_eval {question} {thoughts}",
        }
        agent = TreeOfThoughtAgent(
            name="t", llm=llm, max_depth=1, num_branches=1, custom_prompts=custom
        )
        result = agent.run("test custom")
        assert isinstance(result, str)

    def test_add_tool_mcp_expand(self):
        llm = make_mock_llm()
        agent = TreeOfThoughtAgent(name="t", llm=llm)

        from hello_agents.tools.base import tool_action

        class MCPTool(Tool):
            def __init__(self):
                super().__init__(
                    name="mcp_server", description="MCP server", expandable=True
                )
                self.auto_expand = True

            @tool_action("mcp_call", "Call an MCP tool")
            def call_tool(
                self, action: str, tool_name: str, arguments: dict = None
            ) -> str:
                return "result"

            def run(self, parameters: Dict[str, Any]) -> str:
                return "result"

            def get_parameters(self) -> List[ToolParameter]:
                return [
                    ToolParameter(name="action", type="str", description="action"),
                    ToolParameter(name="tool_name", type="str", description="tool"),
                    ToolParameter(
                        name="arguments",
                        type="object",
                        description="args",
                        required=False,
                    ),
                ]

        mock_mcp = MCPTool()
        agent.add_tool(mock_mcp)
        tool_names = agent.tool_registry.list_tools()
        assert "mcp_call" in tool_names

    def test_mcts_select_expand(self):
        llm = make_mock_llm()
        agent = TreeOfThoughtAgent(name="t", llm=llm)
        root = ThoughtNode(content="ROOT", depth=0)
        c1 = ThoughtNode(content="c1", depth=1, parent=root)
        c2 = ThoughtNode(content="c2", depth=1, parent=root)
        root.children = [c1, c2]
        root.visits = 1
        c1.visits = 1
        c2.visits = 0

        selected = agent._mcts_select(root)
        assert selected is c2

    def test_mcts_best_child_by_visits(self):
        agent = TreeOfThoughtAgent(name="t", llm=make_mock_llm())
        root = ThoughtNode(content="ROOT", depth=0)
        c1 = ThoughtNode(content="c1", depth=1, parent=root)
        c2 = ThoughtNode(content="c2", depth=1, parent=root)
        root.children = [c1, c2]
        c1.visits = 10
        c2.visits = 5

        best = agent._mcts_best_child(root)
        assert best is c1

    def test_mcts_best_child_no_children(self):
        agent = TreeOfThoughtAgent(name="t", llm=make_mock_llm())
        leaf = ThoughtNode(content="leaf", depth=1)
        assert agent._mcts_best_child(leaf) is None

    def test_collect_leaf_solutions(self):
        agent = TreeOfThoughtAgent(name="t", llm=make_mock_llm())
        root = ThoughtNode(content="ROOT", depth=0)
        n1 = ThoughtNode(content="n1", depth=1, parent=root)
        n2 = ThoughtNode(content="n2", depth=1, parent=root)
        root.children = [n1, n2]
        n1.solution = "sol1"
        n2.solution = None

        sols = agent._collect_leaf_solutions(root)
        assert sols == ["sol1"]

    def test_collect_all_paths(self):
        agent = TreeOfThoughtAgent(name="t", llm=make_mock_llm())
        root = ThoughtNode(content="ROOT", depth=0)
        n1 = ThoughtNode(content="L1", depth=1, parent=root)
        n2 = ThoughtNode(content="L2", depth=2, parent=n1)
        root.children = [n1]
        n1.children = [n2]

        paths = agent._collect_all_paths(root)
        assert len(paths) == 1
        assert "L1" in paths[0]
        assert "L2" in paths[0]
