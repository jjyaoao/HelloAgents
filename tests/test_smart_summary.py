"""测试智能摘要与 Token 计数优化功能"""

import pytest
import os
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.core.message import Message
from hello_agents.core.config import Config

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


@pytest.fixture
def llm():
    """创建真实的 LLM"""
    return HelloAgentsLLM()


@pytest.fixture
def agent_with_smart_summary(llm):
    """创建启用智能摘要的 Agent"""
    config = Config(
        enable_smart_compression=True,
        min_retain_rounds=3,
        compression_threshold=0.5,
        context_window=8000,
        summary_llm_provider="deepseek",
        summary_llm_model="deepseek-chat",
        summary_max_tokens=800,
        summary_temperature=0.3
    )
    return SimpleAgent("智能摘要测试助手", llm, config=config)


@pytest.fixture
def agent_with_simple_summary(llm):
    """创建使用简单摘要的 Agent"""
    config = Config(
        enable_smart_compression=False,
        min_retain_rounds=3,
        context_window=8000
    )
    return SimpleAgent("简单摘要测试助手", llm, config=config)


def test_simple_summary_generation(agent_with_simple_summary):
    """测试简单摘要生成"""
    # 创建历史消息并添加到历史管理器
    history = [
        Message("Hello", "user"),
        Message("Hi there", "assistant"),
        Message("How are you?", "user"),
        Message("I'm good", "assistant"),
    ]
    
    # 添加到历史管理器以正确计算轮次
    for msg in history:
        agent_with_simple_summary.history_manager.append(msg)
    
    # 获取历史并生成摘要
    history = agent_with_simple_summary.history_manager.get_history()
    summary = agent_with_simple_summary._generate_simple_summary(history)
    
    print(f"\n简单摘要: {summary}")
    assert "轮对话" in summary
    assert "用户消息：2 条" in summary
    assert "助手消息：2 条" in summary
    assert "总消息数：4 条" in summary
    print("✅ 简单摘要生成测试通过")


def test_smart_summary_generation(agent_with_smart_summary):
    """测试智能摘要生成（真实 LLM 调用）"""
    # 创建历史消息（需要超过 min_retain_rounds 才会触发智能摘要）
    history = [
        Message("帮我分析项目结构", "user"),
        Message("好的，我会分析", "assistant"),
        Message("发现了什么问题？", "user"),
        Message("发现了架构问题", "assistant"),
        Message("继续分析", "user"),
        Message("正在分析中", "assistant"),
        Message("还有其他问题吗？", "user"),
        Message("还在检查", "assistant"),
    ]
    
    # 添加消息到历史管理器
    for msg in history:
        agent_with_smart_summary.history_manager.append(msg)
    
    # 获取历史并生成摘要
    history = agent_with_smart_summary.history_manager.get_history()
    summary = agent_with_smart_summary._generate_smart_summary(history)
    
    print(f"\n智能摘要: {summary}")
    # 验证摘要包含关键信息
    assert "历史摘要" in summary
    assert "已压缩" in summary
    # 智能摘要应该比简单摘要更长
    assert len(summary) > 100
    print("✅ 智能摘要生成测试通过")


def test_token_counter_basic(agent_with_simple_summary):
    """测试 Token 计数器基本功能"""
    msg = Message("Hello, world!", "user")
    
    # 计算 Token 数
    tokens = agent_with_simple_summary.token_counter.count_message(msg)
    
    print(f"\n消息 Token 数: {tokens}")
    # Token 数应该大于 0
    assert tokens > 0
    
    # 再次计算应该使用缓存（结果相同）
    tokens2 = agent_with_simple_summary.token_counter.count_message(msg)
    assert tokens == tokens2
    print("✅ Token 计数器基本功能测试通过")


def test_token_counter_incremental(agent_with_simple_summary):
    """测试增量 Token 计算"""
    # 初始 Token 数应该为 0
    assert agent_with_simple_summary._history_token_count == 0
    
    # 添加第一条消息
    msg1 = Message("First message", "user")
    agent_with_simple_summary.add_message(msg1)
    count1 = agent_with_simple_summary._history_token_count
    print(f"\n第一条消息后 Token 数: {count1}")
    assert count1 > 0
    
    # 添加第二条消息
    msg2 = Message("Second message", "assistant")
    agent_with_simple_summary.add_message(msg2)
    count2 = agent_with_simple_summary._history_token_count
    print(f"第二条消息后 Token 数: {count2}")
    assert count2 > count1
    
    # 清空历史
    agent_with_simple_summary.clear_history()
    assert agent_with_simple_summary._history_token_count == 0
    print("✅ 增量 Token 计算测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

