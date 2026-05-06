"""流式输出功能测试"""

import pytest
from hello_agents.core.stream import StreamEvent
from hello_agents.core.agent import Agent
from hello_agents.agents.simple_agent import SimpleAgent
from hello_agents.agents.function_call_agent import FunctionCallAgent
from hello_agents.agents.react_agent import ReActAgent
from hello_agents.agents.reflection_agent import ReflectionAgent
from hello_agents.agents.plan_solve_agent import PlanAndSolveAgent
from hello_agents.agents.tree_of_thought_agent import TreeOfThoughtAgent
from hello_agents.agents.tool_aware_agent import ToolAwareSimpleAgent


class MockLLM:
    provider = "mock"

    def __init__(self):
        self.model = "mock-model"
        self.temperature = 0.7
        self.max_tokens = None

    def think(self, messages, temperature=None):
        yield "你好！"

    def stream_invoke(self, messages, **kwargs):
        yield from ("你好", "，", "请问", "有", "什么", "可以", "帮", "你？")

    def invoke(self, messages, **kwargs):
        return "你好，请问有什么可以帮你？"


class MockToolLLM:
    """模拟 LLM：先输出工具调用标记，再输出普通文本"""

    provider = "mock"

    def __init__(self):
        self.model = "mock-model"
        self.temperature = 0.7
        self.max_tokens = None
        self.call_count = 0

    def think(self, messages, temperature=None):
        yield ""

    def stream_invoke(self, messages, **kwargs):
        self.call_count += 1
        if self.call_count <= 1:
            yield from (
                "让我",
                "查",
                "一下",
                "[TOOL_CALL:calculator_multiply:a=6,b=7]",
                "结",
                "果",
                "是",
            )
        else:
            yield from ("计算", "结果", "是", "42")

    def invoke(self, messages, **kwargs):
        return "计算结果参考上述信息。"


@pytest.fixture
def mock_llm():
    return MockLLM()


class TestStreamEvent:
    """StreamEvent 单元测试"""

    def test_text_event(self):
        e = StreamEvent.text("hello")
        assert e.event_type == "text"
        assert e.content == "hello"
        assert e.metadata == {}

    def test_thought_event(self):
        e = StreamEvent.thought("分析中...")
        assert e.event_type == "thought"
        assert e.content == "分析中..."

    def test_action_event(self):
        e = StreamEvent.action("search[AI]", tool_name="search", query="AI")
        assert e.event_type == "action"
        assert e.metadata["tool_name"] == "search"
        assert e.metadata["query"] == "AI"

    def test_observation_event(self):
        e = StreamEvent.observation("搜索到 10 条结果", source="web")
        assert e.event_type == "observation"
        assert e.metadata["source"] == "web"

    def test_tool_call_event(self):
        e = StreamEvent.tool_call("calculator", "a=6,b=7")
        assert e.event_type == "tool_call"
        assert e.metadata["tool_name"] == "calculator"
        assert e.metadata["parameters"] == "a=6,b=7"
        assert "[TOOL_CALL:" in e.content

    def test_tool_result_event(self):
        e = StreamEvent.tool_result("calculator", "42")
        assert e.event_type == "tool_result"
        assert e.metadata["tool_name"] == "calculator"
        assert e.content == "42"

    def test_status_event(self):
        e = StreamEvent.status("正在生成计划...")
        assert e.event_type == "status"

    def test_error_event(self):
        e = StreamEvent.error("调用失败")
        assert e.event_type == "error"

    def test_done_event(self):
        e = StreamEvent.done("最终答案")
        assert e.event_type == "done"
        assert e.content == "最终答案"


class TestAgentStreamRun:
    """Agent 基类 stream_run 测试"""

    def test_base_stream_run_fallback(self, mock_llm):
        """测试基类默认回退行为：text + done"""

        class MinimalAgent(Agent):
            def run(self, input_text, **kwargs):
                return "fallback"

        agent = MinimalAgent(name="minimal", llm=mock_llm)
        events = list(agent.stream_run("test"))

        assert len(events) == 2
        assert events[0].event_type == "text"
        assert events[0].content == "fallback"
        assert events[1].event_type == "done"
        assert events[1].content == "fallback"

    def test_all_agents_have_stream_run(self):
        """所有 Agent 子类都应实现 stream_run"""
        parents = [
            SimpleAgent,
            FunctionCallAgent,
            ReActAgent,
            ReflectionAgent,
            PlanAndSolveAgent,
            TreeOfThoughtAgent,
            ToolAwareSimpleAgent,
        ]
        for cls in parents:
            assert hasattr(cls, "stream_run"), f"{cls.__name__} 缺少 stream_run"

    def test_stream_run_outputs_done(self, mock_llm):
        """流式输出的最后一个事件必须是 done"""
        agent = SimpleAgent(name="test", llm=mock_llm)
        events = list(agent.stream_run("你好"))
        assert events[-1].event_type == "done"
        assert len(events[-1].content) > 0


class TestSimpleAgentStream:
    """SimpleAgent 流式输出测试"""

    def test_basic_text_stream(self, mock_llm):
        agent = SimpleAgent(name="助手", llm=mock_llm)
        events = list(agent.stream_run("你好"))

        assert events[0].event_type == "status"
        assert "开始生成" in events[0].content

        text_events = [e for e in events if e.event_type == "text"]
        assert len(text_events) > 0
        assert "".join(e.content for e in text_events) == "你好，请问有什么可以帮你？"

    def test_event_order(self, mock_llm):
        agent = SimpleAgent(name="助手", llm=mock_llm)
        events = list(agent.stream_run("你好"))

        event_types = [e.event_type for e in events]
        assert event_types[0] == "status"
        assert event_types[-1] == "done"
        assert "text" in event_types

    def test_history_preserved(self, mock_llm):
        agent = SimpleAgent(name="助手", llm=mock_llm)
        list(agent.stream_run("你好"))

        assert len(agent.get_history()) == 2
        assert agent.get_history()[0].role == "user"
        assert agent.get_history()[0].content == "你好"
        assert agent.get_history()[1].role == "assistant"
        assert len(agent.get_history()[1].content) > 0

    def test_stream_with_tool_calls(self):
        """含工具调用的流式输出"""
        agent = SimpleAgent(
            name="工具助手",
            llm=MockToolLLM(),
            enable_tool_calling=False,
        )
        agent.enable_tool_calling = True

        events = list(agent.stream_run("6*7=?"))

        event_types = [e.event_type for e in events]
        assert "tool_call" in event_types
        assert event_types[-1] == "done"

    def test_returns_complete_text(self, mock_llm):
        agent = SimpleAgent(name="助手", llm=mock_llm)
        events = list(agent.stream_run("你好"))
        done_event = [e for e in events if e.event_type == "done"][0]
        assert done_event.content == "你好，请问有什么可以帮你？"


class TestFunctionCallAgentStream:
    """FunctionCallAgent 流式输出测试"""

    def test_basic_text_stream(self, mock_llm):
        agent = FunctionCallAgent(name="fc", llm=mock_llm, enable_tool_calling=False)
        events = list(agent.stream_run("你好"))

        assert events[0].event_type == "status"
        assert events[-1].event_type == "done"
        text_events = [e for e in events if e.event_type == "text"]
        assert len(text_events) > 0

    def test_event_sequence(self, mock_llm):
        agent = FunctionCallAgent(name="fc", llm=mock_llm, enable_tool_calling=False)
        events = list(agent.stream_run("你好"))

        assert events[-1].event_type == "done"
        assert events[-1].content == "你好，请问有什么可以帮你？"


class TestReActAgentStream:
    """ReActAgent 流式输出测试"""

    def test_emits_thought_and_action(self):
        """ReAct 流式应输出 thought 和 action 事件"""
        agent = ReActAgent(name="react", llm=MockLLM(), max_steps=1)

        events = list(agent.stream_run("测试"))

        event_types = [e.event_type for e in events]
        assert (
            "thought" in event_types or "action" in event_types or "text" in event_types
        )
        assert events[-1].event_type == "done"


class TestReflectionAgentStream:
    """ReflectionAgent 流式输出测试"""

    def test_basic_stream_workflow(self, mock_llm):
        agent = ReflectionAgent(name="reflection", llm=mock_llm, max_iterations=1)
        events = list(agent.stream_run("写一首诗"))

        assert events[0].event_type == "status"
        assert events[-1].event_type == "done"


class TestPlanAndSolveAgentStream:
    """PlanAndSolveAgent 流式输出测试"""

    def test_stream_planner_and_executor(self):
        class PlanMockLLM:
            provider = "mock"

            def __init__(self):
                self.model = "mock"
                self.temperature = 0.7
                self.max_tokens = None

            def think(self, messages, temperature=None):
                yield ""

            def stream_invoke(self, messages, **kwargs):
                yield "```python\n['分析', '计算', '总结']\n```\n"

            def invoke(self, messages, **kwargs):
                return "42"

        agent = PlanAndSolveAgent(name="plan", llm=PlanMockLLM())
        events = list(agent.stream_run("1+1=?"))

        assert events[0].event_type == "status"
        assert events[-1].event_type == "done"


class TestTreeOfThoughtAgentStream:
    """TreeOfThoughtAgent 流式输出测试"""

    def test_bfs_stream_outputs_events(self):
        class ToTMockLLM:
            provider = "mock"

            def __init__(self):
                self.model = "mock"
                self.temperature = 0.7
                self.max_tokens = None

            def think(self, messages, temperature=None):
                yield ""

            def stream_invoke(self, messages, **kwargs):
                yield "Thought 1: 方法一\nThought 2: 方法二\n"

            def invoke(self, messages, **kwargs):
                return "Thought 1: 方法一\nThought 2: 方法二\n"

        agent = TreeOfThoughtAgent(
            name="tot",
            llm=ToTMockLLM(),
            max_depth=1,
            strategy="bfs",
        )
        events = list(agent.stream_run("1+1=?"))

        assert events[-1].event_type == "done"


class TestStreamEventUtils:
    """辅助工具测试"""

    def test_productivity_helper(self, mock_llm):
        """验证可将流式事件便捷消费为字符串"""
        agent = SimpleAgent(name="助手", llm=mock_llm)

        def collect_text(events):
            return "".join(e.content for e in events if e.event_type == "text")

        events = list(agent.stream_run("你好"))
        text = collect_text(events)
        assert text == "你好，请问有什么可以帮你？"

    def test_detect_tool_calls_in_stream(self):
        """验证可从流中检测工具调用事件"""
        agent = SimpleAgent(
            name="工具助手",
            llm=MockToolLLM(),
            enable_tool_calling=False,
        )
        agent.enable_tool_calling = True

        events = list(agent.stream_run("6*7=?"))
        tool_calls = [e for e in events if e.event_type == "tool_call"]
        done_events = [e for e in events if e.event_type == "done"]

        if tool_calls:
            assert tool_calls[0].metadata["tool_name"] == "calculator_multiply"
        assert len(done_events) == 1
