"""测试子代理机制"""

import pytest
from hello_agents.core.agent import Agent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config
from hello_agents.core.message import Message
from hello_agents.tools.registry import ToolRegistry
from hello_agents.tools.tool_filter import ReadOnlyFilter, FullAccessFilter
from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode
from typing import Dict, Any, List
from dotenv import load_dotenv
load_dotenv()

# ==================== Mock 工具 ====================

class MockReadTool(Tool):
    """模拟只读工具"""
    
    def __init__(self):
        super().__init__(name="Read", description="读取文件")
    
    def get_parameters(self) -> List[ToolParameter]:
        return [ToolParameter(name="path", type="string", required=True)]
    
    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        return ToolResponse.success(text="文件内容")


class MockWriteTool(Tool):
    """模拟写入工具"""
    
    def __init__(self):
        super().__init__(name="Write", description="写入文件")
    
    def get_parameters(self) -> List[ToolParameter]:
        return [ToolParameter(name="path", type="string", required=True)]
    
    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        return ToolResponse.success(text="写入成功")


class MockBashTool(Tool):
    """模拟危险工具"""
    
    def __init__(self):
        super().__init__(name="Bash", description="执行命令")
    
    def get_parameters(self) -> List[ToolParameter]:
        return [ToolParameter(name="command", type="string", required=True)]
    
    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        return ToolResponse.success(text="命令执行")


# ==================== Mock Agent ====================

class MockSimpleAgent(Agent):
    """简单的 Mock Agent，用于测试"""
    
    def __init__(self, name: str, llm: HelloAgentsLLM, config: Config = None, tool_registry: ToolRegistry = None):
        super().__init__(name, llm, config=config, tool_registry=tool_registry)
        self.run_count = 0
    
    def run(self, input_text: str, **kwargs) -> str:
        """简单返回输入"""
        self.run_count += 1
        
        # 模拟添加历史
        self.add_message(Message(role="user", content=input_text))
        
        # 模拟工具调用
        if self.tool_registry and "使用工具" in input_text:
            tools = self.tool_registry.list_tools()
            if tools:
                tool_name = tools[0]
                self.add_message(Message(
                    role="assistant",
                    content=f"Action: {tool_name}[test]"
                ))
        
        result = f"完成任务: {input_text}"
        self.add_message(Message(role="assistant", content=result))
        
        return result


# ==================== 测试用例 ====================

class TestAgentRunAsSubagent:
    """测试 Agent.run_as_subagent() 方法"""
    
    def test_basic_subagent_execution(self):
        """测试基本的子代理执行"""
        llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")
        config = Config(subagent_enabled=False)  # 禁用自动注册
        agent = MockSimpleAgent("test", llm, config=config)
        
        # 执行子代理任务
        result = agent.run_as_subagent(
            task="测试任务",
            return_summary=True
        )
        
        # 验证返回结构
        assert "success" in result
        assert "summary" in result
        assert "metadata" in result
        
        assert result["success"] is True
        assert "测试任务" in result["summary"]
        assert result["metadata"]["steps"] > 0
    
    def test_context_isolation(self):
        """测试上下文隔离"""
        llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")
        config = Config(subagent_enabled=False)
        agent = MockSimpleAgent("test", llm, config=config)
        
        # 主 Agent 添加一些历史
        agent.add_message(Message(role="user", content="主任务消息1"))
        agent.add_message(Message(role="assistant", content="主任务回复1"))
        
        original_history_len = len(agent.get_history())
        
        # 执行子代理任务
        result = agent.run_as_subagent(task="子任务")
        
        # 验证主 Agent 历史未被污染
        assert len(agent.get_history()) == original_history_len
        
        # 验证子代理确实执行了（有元数据）
        assert result["metadata"]["steps"] > 0
    
    def test_tool_filter_readonly(self):
        """测试只读工具过滤"""
        llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")
        # 禁用 skills 和 subagent 自动注册
        config = Config(subagent_enabled=False, skills_enabled=False)

        # 创建工具注册表
        registry = ToolRegistry()
        registry.register_tool(MockReadTool())
        registry.register_tool(MockWriteTool())
        registry.register_tool(MockBashTool())

        agent = MockSimpleAgent("test", llm, config=config, tool_registry=registry)

        # 验证初始工具列表
        initial_tools = registry.list_tools()
        assert len(initial_tools) == 3

        # 使用只读过滤器执行子代理
        tool_filter = ReadOnlyFilter()
        result = agent.run_as_subagent(
            task="使用工具完成任务",
            tool_filter=tool_filter
        )

        # 验证执行后工具列表恢复
        final_tools = registry.list_tools()
        assert len(final_tools) == 3
        assert "Read" in final_tools
        assert "Write" in final_tools
        assert "Bash" in final_tools
    
    def test_tool_filter_full_access(self):
        """测试完全访问过滤器"""
        llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")
        # 禁用 skills 和 subagent 自动注册
        config = Config(subagent_enabled=False, skills_enabled=False)

        registry = ToolRegistry()
        registry.register_tool(MockReadTool())
        registry.register_tool(MockWriteTool())
        registry.register_tool(MockBashTool())

        agent = MockSimpleAgent("test", llm, config=config, tool_registry=registry)

        initial_tools = registry.list_tools()
        assert len(initial_tools) == 3

        # 使用完全访问过滤器
        tool_filter = FullAccessFilter()
        result = agent.run_as_subagent(
            task="使用工具完成任务",
            tool_filter=tool_filter
        )

        # 验证执行成功
        assert result["success"] is True

        # 验证执行后工具列表恢复
        final_tools = registry.list_tools()
        assert len(final_tools) == 3
    
    def test_return_full_result(self):
        """测试返回完整结果（而非摘要）"""
        llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")
        config = Config(subagent_enabled=False)
        agent = MockSimpleAgent("test", llm, config=config)
        
        result = agent.run_as_subagent(
            task="测试任务",
            return_summary=False
        )
        
        # 验证返回完整结果
        assert "result" in result
        assert "summary" not in result
        assert "完成任务" in result["result"]
    
    def test_max_steps_override(self):
        """测试覆盖最大步数"""
        llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")
        config = Config(subagent_enabled=False)
        agent = MockSimpleAgent("test", llm, config=config)
        
        # 设置初始 max_steps
        agent.max_steps = 10
        
        # 使用覆盖值执行
        result = agent.run_as_subagent(
            task="测试任务",
            max_steps_override=5
        )
        
        # 验证执行后恢复原值
        assert agent.max_steps == 10
    
    def test_metadata_collection(self):
        """测试元数据收集"""
        llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")
        config = Config(subagent_enabled=False)
        agent = MockSimpleAgent("test", llm, config=config)
        
        result = agent.run_as_subagent(task="测试任务")
        
        metadata = result["metadata"]
        
        # 验证元数据字段
        assert "steps" in metadata
        assert "tokens" in metadata
        assert "duration_seconds" in metadata
        assert "tools_used" in metadata
        
        assert metadata["steps"] >= 0
        assert metadata["tokens"] >= 0
        assert metadata["duration_seconds"] >= 0
        assert isinstance(metadata["tools_used"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

