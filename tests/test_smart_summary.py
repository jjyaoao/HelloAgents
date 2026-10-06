"""摘要机制默认离线；真实摘要模型用 --run-live 显式调用。"""

from unittest.mock import Mock
import os
import pytest
from hello_agents import SimpleAgent, HelloAgentsLLM, Config, Message, AgentComponents


def make_agent():
    return SimpleAgent(
        "摘要机制",
        Mock(model="offline-summary"),
        config=Config(
            min_retain_rounds=1,
            context_window=8000,
            trace_enabled=False,
            session_enabled=False,
            skills_enabled=False,
            subagent_enabled=False,
            todowrite_enabled=False,
            devlog_enabled=False,
        ),
    )


def history():
    return [
        Message("预算1500元", "user"),
        Message("已记录预算", "assistant"),
        Message("只安排室内活动", "user"),
        Message("继续核对预约", "assistant"),
    ]


def test_simple_summary_generation():
    agent = make_agent()
    for message in history():
        agent.history_manager.append(message)
    summary = agent._generate_simple_summary(agent.get_history())
    assert "用户消息：2 条" in summary
    assert "助手消息：2 条" in summary
    assert "总消息数：4 条" in summary


def test_smart_summary_uses_only_history_before_retention_boundary():
    agent = make_agent()
    summary_llm = Mock()
    summary_llm.invoke.return_value = "已确认预算1500元。"
    agent._component_options = AgentComponents(summary_llm=summary_llm)
    for message in history():
        agent.history_manager.append(message)
    summary = agent._generate_smart_summary(agent.get_history())
    assert "已确认预算1500元" in summary
    messages = summary_llm.invoke.call_args.args[0]
    assert "预算1500元" in messages[-1]["content"]
    assert "只安排室内活动" not in messages[-1]["content"]
    summary_llm.invoke.assert_called_once()


def test_smart_summary_failure_has_explicit_simple_fallback():
    agent = make_agent()
    summary_llm = Mock()
    summary_llm.invoke.side_effect = RuntimeError("local summary failure")
    agent._component_options = AgentComponents(summary_llm=summary_llm)
    messages = history()
    for message in messages:
        agent.history_manager.append(message)
    assert agent._generate_smart_summary(messages) == agent._generate_simple_summary(
        messages
    )
    summary_llm.invoke.assert_called_once()


@pytest.mark.live
def test_live_smart_summary(live_llm_config):
    agent = make_agent()
    settings = dict(live_llm_config)
    settings["model"] = os.getenv("LLM_SUMMARY_MODEL", settings["model"])
    # Reuse configured service credentials; a separate summary model is optional.
    agent._component_options = AgentComponents(summary_llm=HelloAgentsLLM(**settings))
    for message in history():
        agent.history_manager.append(message)
    summary = agent._generate_smart_summary(agent.get_history())
    assert "历史摘要" in summary
    assert "1500" in summary  # A failed call's count-only fallback cannot pass.


def test_token_counter_basic_and_incremental():
    agent = make_agent()
    first, second = Message("First message", "user"), Message(
        "Second message", "assistant"
    )
    assert agent.token_counter.count_message(first) > 0
    assert agent.token_counter.count_message(
        first
    ) == agent.token_counter.count_message(first)
    assert agent._history_token_count == 0
    agent.add_message(first)
    count = agent._history_token_count
    agent.add_message(second)
    assert agent._history_token_count > count > 0
    agent.clear_history()
    assert agent._history_token_count == 0
