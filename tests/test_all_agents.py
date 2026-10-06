"""四类 Agent 的显式真实服务冒烟测试与本地输入/异常检查。"""

from unittest.mock import Mock
import pytest
from hello_agents import (
    Config,
    HelloAgentsLLM,
    SimpleAgent,
    ReActAgent,
    ReflectionAgent,
    PlanSolveAgent,
    ToolRegistry,
)
from hello_agents.core.llm_response import LLMToolResponse
from hello_agents.tools.builtin import CalculatorTool


def quiet_config():
    return Config(
        trace_enabled=False,
        session_enabled=False,
        skills_enabled=False,
        subagent_enabled=False,
        todowrite_enabled=False,
        devlog_enabled=False,
    )


def test_llm_initialization():
    llm = HelloAgentsLLM(
        model="offline-constructor",
        api_key="test-key",
        base_url="http://127.0.0.1:9/v1",
        provider="openai",
    )
    assert llm.model == "offline-constructor"


@pytest.mark.parametrize(
    "agent_type", [SimpleAgent, ReActAgent, ReflectionAgent, PlanSolveAgent]
)
@pytest.mark.live
def test_live_agent_answer(agent_type, live_llm_config):
    agent = agent_type(
        "服务冒烟", HelloAgentsLLM(**live_llm_config), config=quiet_config()
    )
    answer = agent.run("用一句中文说明什么是递归。")
    assert isinstance(answer, str) and answer.strip()
    assert agent.last_run.status == "completed"
    assert agent.last_run.model_calls >= 1


@pytest.mark.live
def test_live_calculator(live_llm_config):
    registry = ToolRegistry()
    registry.register_tool(CalculatorTool())
    agent = SimpleAgent(
        "工具冒烟",
        HelloAgentsLLM(**live_llm_config),
        tool_registry=registry,
        config=quiet_config(),
    )
    answer = agent.run("必须调用计算器计算 256 * 789，再报告精确结果。")
    assert "201984" in answer.replace(",", "").replace(" ", "")
    assert agent.last_run.tool_calls >= 1
    assert agent.last_run.status == "completed"


@pytest.mark.live
def test_live_multi_turn(live_llm_config):
    agent = SimpleAgent(
        "会话冒烟", HelloAgentsLLM(**live_llm_config), config=quiet_config()
    )
    assert agent.run("记住本次项目的代号是青鹭。只需确认。")
    assert "青鹭" in agent.run("本次项目的代号是什么？")


def test_empty_input_reaches_model_without_swallowing_errors():
    llm = Mock(model="offline")
    llm.invoke.return_value = LLMToolResponse("请提供任务。", [], "offline")
    agent = SimpleAgent("输入检查", llm, config=quiet_config())
    assert agent.run("") == "请提供任务。"
    assert llm.invoke.call_args.kwargs["messages"][-1]["content"] == ""


def test_model_failure_propagates():
    llm = Mock(model="offline")
    llm.invoke.side_effect = RuntimeError("local failure")
    agent = SimpleAgent("失败检查", llm, config=quiet_config())
    with pytest.raises(RuntimeError, match="local failure"):
        agent.run("任务")
    assert agent.last_run.status == "failed"
