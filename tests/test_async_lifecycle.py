"""异步生命周期测试套件"""

import pytest
import asyncio
import time
from hello_agents.core.lifecycle import AgentEvent, EventType, ExecutionContext
from hello_agents.core.agent import Agent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config
from hello_agents.agents.react_agent import ReActAgent
from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.registry import ToolRegistry


# ==================== 测试工具 ====================

class MockTool(Tool):
    """模拟工具（用于测试）"""
    
    def __init__(self, name: str = "MockTool", delay: float = 0.1):
        super().__init__(name, f"模拟工具 {name}")
        self.delay = delay
        self.call_count = 0
    
    def run(self, parameters: dict) -> ToolResponse:
        self.call_count += 1
        time.sleep(self.delay)
        return ToolResponse.success(
            text=f"MockTool executed with {parameters}",
            data={"call_count": self.call_count}
        )
    
    def get_parameters(self):
        return [
            ToolParameter(name="query", type="string", description="查询参数")
        ]


class SlowTool(Tool):
    """慢速工具（用于测试并行）"""
    
    def __init__(self):
        super().__init__("SlowTool", "慢速工具")
    
    def run(self, parameters: dict) -> ToolResponse:
        time.sleep(1.0)  # 模拟耗时操作
        return ToolResponse.success(text="SlowTool completed")
    
    def get_parameters(self):
        return [
            ToolParameter(name="data", type="string", description="数据")
        ]


# ==================== 测试类 ====================

class TestAgentEvent:
    """测试 AgentEvent 事件系统"""
    
    def test_event_creation(self):
        """测试事件创建"""
        event = AgentEvent.create(
            EventType.AGENT_START,
            "test_agent",
            input_text="Hello"
        )
        
        assert event.type == EventType.AGENT_START
        assert event.agent_name == "test_agent"
        assert event.data["input_text"] == "Hello"
        assert event.timestamp > 0
    
    def test_event_to_dict(self):
        """测试事件序列化"""
        event = AgentEvent.create(
            EventType.TOOL_CALL,
            "test_agent",
            tool_name="search",
            tool_args={"query": "test"}
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["type"] == "tool_call"
        assert event_dict["agent_name"] == "test_agent"
        assert event_dict["data"]["tool_name"] == "search"
        assert event_dict["data"]["tool_args"]["query"] == "test"


class TestExecutionContext:
    """测试执行上下文"""
    
    def test_context_creation(self):
        """测试上下文创建"""
        ctx = ExecutionContext(input_text="Hello")
        
        assert ctx.input_text == "Hello"
        assert ctx.current_step == 0
        assert ctx.total_tokens == 0
    
    def test_context_operations(self):
        """测试上下文操作"""
        ctx = ExecutionContext(input_text="Hello")
        
        ctx.increment_step()
        assert ctx.current_step == 1
        
        ctx.add_tokens(100)
        assert ctx.total_tokens == 100
        
        ctx.set_metadata("key", "value")
        assert ctx.get_metadata("key") == "value"
        assert ctx.get_metadata("missing", "default") == "default"


@pytest.mark.asyncio
class TestAsyncLLM:
    """测试 LLM 异步接口"""
    
    async def test_ainvoke_basic(self):
        """测试基础异步调用"""
        # 注意：这个测试需要真实的 LLM 配置
        # 在 CI 环境中可以跳过
        pytest.skip("需要真实 LLM 配置")
    
    async def test_astream_invoke(self):
        """测试异步流式调用"""
        pytest.skip("需要真实 LLM 配置")


@pytest.mark.asyncio
class TestAsyncTool:
    """测试工具异步接口"""
    
    async def test_tool_arun(self):
        """测试工具异步执行"""
        tool = MockTool(delay=0.1)
        
        start_time = time.time()
        response = await tool.arun({"query": "test"})
        elapsed = time.time() - start_time
        
        assert response.status.value == "success"
        assert "MockTool executed" in response.text
        assert elapsed >= 0.1  # 至少等待了 delay 时间
    
    async def test_tool_arun_with_timing(self):
        """测试带时间统计的异步执行"""
        tool = MockTool(delay=0.1)
        
        response = await tool.arun_with_timing({"query": "test"})
        
        assert response.stats is not None
        assert "time_ms" in response.stats
        assert response.stats["time_ms"] >= 100  # 至少 100ms
        assert response.context["tool_name"] == "MockTool"


@pytest.mark.asyncio
class TestAsyncAgent:
    """测试 Agent 异步基础功能"""
    
    async def test_lifecycle_hooks(self):
        """测试生命周期钩子"""
        pytest.skip("需要真实 LLM 配置")



