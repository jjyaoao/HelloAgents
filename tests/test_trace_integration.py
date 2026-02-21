"""端到端集成测试 - 验证 TraceLogger 与 Agent 的集成"""

import pytest
import tempfile
import shutil
from pathlib import Path

from hello_agents.core.config import Config
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.agents.react_agent import ReActAgent
from hello_agents.tools.registry import ToolRegistry
from hello_agents.tools.builtin.calculator import CalculatorTool


class TestTraceIntegration:
    """TraceLogger 与 Agent 集成测试"""
    
    def setup_method(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """每个测试后清理临时目录"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_react_agent_with_trace(self):
        """测试 ReActAgent 启用 Trace"""
        # 配置
        config = Config(
            trace_enabled=True,
            trace_dir=self.temp_dir,
            trace_sanitize=True
        )
        
        # 创建 LLM（使用 mock）
        llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")
        
        # 创建工具注册表
        tool_registry = ToolRegistry()
        tool_registry.register_tool(CalculatorTool())
        
        # 创建 Agent
        agent = ReActAgent(
            name="TestAgent",
            llm=llm,
            tool_registry=tool_registry,
            config=config
        )
        
        # 验证 TraceLogger 已创建
        assert agent.trace_logger is not None
        assert agent.trace_logger.session_id.startswith("s-")
        
        # 验证配置传递
        assert agent.trace_logger.sanitize == True
        assert agent.trace_logger.output_dir == Path(self.temp_dir)
    
    def test_trace_disabled(self):
        """测试禁用 Trace"""
        config = Config(trace_enabled=False)
        
        llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")
        agent = ReActAgent(
            name="TestAgent",
            llm=llm,
            config=config
        )
        
        # 验证 TraceLogger 未创建
        assert agent.trace_logger is None
    
    def test_trace_files_generated(self):
        """测试 Trace 文件生成"""
        config = Config(
            trace_enabled=True,
            trace_dir=self.temp_dir
        )
        
        llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")
        agent = ReActAgent(
            name="TestAgent",
            llm=llm,
            config=config
        )
        
        # 手动记录一些事件并 finalize
        if agent.trace_logger:
            agent.trace_logger.log_event("session_start", {"agent_name": "TestAgent"})
            agent.trace_logger.log_event("tool_call", {"tool_name": "Calculator"}, step=1)
            agent.trace_logger.finalize()
            
            # 验证文件生成
            session_id = agent.trace_logger.session_id
            jsonl_path = Path(self.temp_dir) / f"trace-{session_id}.jsonl"
            html_path = Path(self.temp_dir) / f"trace-{session_id}.html"
            
            assert jsonl_path.exists()
            assert html_path.exists()
            
            # 验证 HTML 包含统计面板
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                assert "统计" in html_content
                assert "Calculator" in html_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

