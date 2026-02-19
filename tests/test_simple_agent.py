"""测试 SimpleAgent（使用 Mock LLM，不调用真实 API）。"""

import pytest
from hello_agents.agents.simple_agent import SimpleAgent


def test_simple_agent_run(mock_llm):
    agent = SimpleAgent(name="TestAgent", llm=mock_llm, system_prompt="You are helpful.")
    out = agent.run("Hello")
    assert "Hello from mock LLM" in out or out == "Hello from mock LLM."


def test_simple_agent_stream_run(mock_llm):
    agent = SimpleAgent(name="TestAgent", llm=mock_llm)
    chunks = list(agent.stream_run("Hi"))
    assert len(chunks) > 0
    assert "".join(chunks) == "Hello from mock LLM."


def test_simple_agent_history(mock_llm):
    agent = SimpleAgent(name="TestAgent", llm=mock_llm)
    agent.run("Q1")
    history = agent.get_history()
    assert len(history) >= 1
    agent.clear_history()
    assert len(agent.get_history()) == 0
