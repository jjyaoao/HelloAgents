"""测试会话持久化功能"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from hello_agents.core.session_store import SessionStore
from hello_agents.core.message import Message
from hello_agents.core.agent import Agent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config
from hello_agents.agents.simple_agent import SimpleAgent
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

class TestSessionStore:
    """测试 SessionStore 基础功能"""
    
    def setup_method(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.store = SessionStore(session_dir=self.temp_dir)
    
    def teardown_method(self):
        """每个测试后清理临时目录"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_and_load_session(self):
        """测试保存和加载会话"""
        # 准备测试数据
        agent_config = {
            "name": "test_agent",
            "llm_model": "gpt-4",
            "llm_provider": "openai"
        }
        
        history = [
            Message("Hello", "user"),
            Message("Hi there!", "assistant")
        ]
        
        metadata = {
            "created_at": datetime.now().isoformat(),
            "total_tokens": 100,
            "total_steps": 2
        }
        
        # 保存会话
        filepath = self.store.save(
            agent_config=agent_config,
            history=history,
            tool_schema_hash="abc123",
            read_cache={},
            metadata=metadata,
            session_name="test-session"
        )
        
        # 验证文件存在
        assert Path(filepath).exists()
        
        # 加载会话
        loaded_data = self.store.load(filepath)
        
        # 验证数据
        assert loaded_data["agent_config"]["name"] == "test_agent"
        assert len(loaded_data["history"]) == 2
        assert loaded_data["history"][0]["content"] == "Hello"
        assert loaded_data["tool_schema_hash"] == "abc123"
        assert loaded_data["metadata"]["total_tokens"] == 100
    
    def test_list_sessions(self):
        """测试列出所有会话"""
        # 保存多个会话
        for i in range(3):
            self.store.save(
                agent_config={"name": f"agent_{i}"},
                history=[],
                tool_schema_hash="hash",
                read_cache={},
                metadata={"total_tokens": i * 100},
                session_name=f"session-{i}"
            )
        
        # 列出会话
        sessions = self.store.list_sessions()
        
        # 验证
        assert len(sessions) == 3
        assert all("filename" in s for s in sessions)
        assert all("session_id" in s for s in sessions)
    
    def test_delete_session(self):
        """测试删除会话"""
        # 保存会话
        self.store.save(
            agent_config={"name": "test"},
            history=[],
            tool_schema_hash="hash",
            read_cache={},
            metadata={},
            session_name="to-delete"
        )
        
        # 删除会话
        result = self.store.delete("to-delete")
        assert result is True
        
        # 验证文件不存在
        filepath = Path(self.temp_dir) / "to-delete.json"
        assert not filepath.exists()
        
        # 再次删除应该返回 False
        result = self.store.delete("to-delete")
        assert result is False
    
    def test_check_config_consistency(self):
        """测试配置一致性检查"""
        saved_config = {
            "llm_provider": "openai",
            "llm_model": "gpt-4",
            "max_steps": 10
        }
        
        # 相同配置
        current_config = saved_config.copy()
        result = self.store.check_config_consistency(saved_config, current_config)
        assert result["consistent"] is True
        assert len(result["warnings"]) == 0
        
        # 不同配置
        current_config["llm_model"] = "gpt-3.5-turbo"
        result = self.store.check_config_consistency(saved_config, current_config)
        assert result["consistent"] is False
        assert len(result["warnings"]) > 0
    
    def test_check_tool_schema_consistency(self):
        """测试工具 Schema 一致性检查"""
        saved_hash = "abc123"
        
        # 相同哈希
        result = self.store.check_tool_schema_consistency(saved_hash, "abc123")
        assert result["changed"] is False
        
        # 不同哈希
        result = self.store.check_tool_schema_consistency(saved_hash, "def456")
        assert result["changed"] is True
        assert "建议" in result["recommendation"]


class TestAgentSessionPersistence:
    """测试 Agent 会话持久化集成"""

    def setup_method(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config(
            session_enabled=True,
            session_dir=self.temp_dir,
            trace_enabled=False  # 禁用 trace 避免干扰
        )

    def teardown_method(self):
        """每个测试后清理临时目录"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_agent_save_session(self):
        """测试 Agent 保存会话"""
        # 创建 Agent
        llm = HelloAgentsLLM()
        agent = SimpleAgent(
            name="test_agent",
            llm=llm,
            config=self.config
        )

        # 添加一些消息
        agent.add_message(Message("Hello", "user"))
        agent.add_message(Message("Hi!", "assistant"))

        # 保存会话
        filepath = agent.save_session("test-save")

        # 验证文件存在
        assert Path(filepath).exists()

        # 验证文件内容
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data["agent_config"]["name"] == "test_agent"
        assert len(data["history"]) == 2

    def test_agent_load_session(self):
        """测试 Agent 加载会话"""
        # 创建并保存会话
        llm = HelloAgentsLLM()
        agent1 = SimpleAgent(
            name="agent1",
            llm=llm,
            config=self.config
        )

        agent1.add_message(Message("Question 1", "user"))
        agent1.add_message(Message("Answer 1", "assistant"))
        filepath = agent1.save_session("test-load")

        # 创建新 Agent 并加载会话
        agent2 = SimpleAgent(
            name="agent2",
            llm=llm,
            config=self.config
        )

        agent2.load_session(filepath, check_consistency=False)

        # 验证历史已恢复
        history = agent2.get_history()
        assert len(history) == 2
        assert history[0].content == "Question 1"
        assert history[1].content == "Answer 1"

    def test_agent_list_sessions(self):
        """测试 Agent 列出会话"""
        llm = HelloAgentsLLM()
        agent = SimpleAgent(
            name="test_agent",
            llm=llm,
            config=self.config
        )

        # 保存多个会话
        for i in range(3):
            agent.add_message(Message(f"Message {i}", "user"))
            agent.save_session(f"session-{i}")

        # 列出会话
        sessions = agent.list_sessions()

        # 验证
        assert len(sessions) >= 3

    def test_session_disabled(self):
        """测试禁用会话持久化"""
        config = Config(session_enabled=False)
        llm = HelloAgentsLLM()
        agent = SimpleAgent(
            name="test_agent",
            llm=llm,
            config=config
        )

        # 尝试保存会话应该抛出异常
        with pytest.raises(RuntimeError, match="会话持久化未启用"):
            agent.save_session("test")

    def test_auto_save(self):
        """测试自动保存功能"""
        config = Config(
            session_enabled=True,
            session_dir=self.temp_dir,
            auto_save_enabled=True,
            auto_save_interval=2,  # 每 2 条消息自动保存
            trace_enabled=False
        )

        llm = HelloAgentsLLM()
        agent = SimpleAgent(
            name="test_agent",
            llm=llm,
            config=config
        )

        # 添加消息触发自动保存
        agent.add_message(Message("Message 1", "user"))
        agent.add_message(Message("Message 2", "assistant"))

        # 验证自动保存文件存在
        auto_save_path = Path(self.temp_dir) / "session-auto.json"
        assert auto_save_path.exists()

    def test_compute_tool_schema_hash(self):
        """测试工具 Schema 哈希计算"""
        from hello_agents.tools.registry import ToolRegistry
        from hello_agents.tools.builtin.calculator import CalculatorTool

        llm = HelloAgentsLLM()
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())

        agent = SimpleAgent(
            name="test_agent",
            llm=llm,
            config=self.config,
            tool_registry=registry
        )

        # 计算哈希
        hash1 = agent._compute_tool_schema_hash()
        assert hash1 != "no-tools"
        assert len(hash1) == 16

        # 相同工具应该产生相同哈希
        hash2 = agent._compute_tool_schema_hash()
        assert hash1 == hash2

    def test_session_metadata_tracking(self):
        """测试会话元数据追踪"""
        llm = HelloAgentsLLM()
        agent = SimpleAgent(
            name="test_agent",
            llm=llm,
            config=self.config
        )

        # 验证初始元数据
        assert "created_at" in agent._session_metadata
        assert "total_tokens" in agent._session_metadata
        assert "total_steps" in agent._session_metadata

        # 保存会话
        filepath = agent.save_session("test-metadata")

        # 验证元数据已保存
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert "duration_seconds" in data["metadata"]
        assert data["metadata"]["duration_seconds"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


