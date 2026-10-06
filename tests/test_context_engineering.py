"""测试上下文工程模块

测试内容：
1. HistoryManager - 历史管理与压缩
2. ObservationTruncator - 工具输出截断
3. Agent 集成 - 端到端测试
4. Message 增强 - summary role 支持
"""

import pytest
import os
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock


# 加载环境变量


from hello_agents.core.message import Message
from hello_agents.context.history import HistoryManager
from hello_agents.context.truncator import ObservationTruncator
from hello_agents.core.config import Config


class TestMessage:
    """测试 Message 类的增强功能"""
    
    def test_summary_role(self):
        """测试 summary role 支持"""
        msg = Message("这是摘要", "summary")
        assert msg.role == "summary"
        assert msg.content == "这是摘要"
    
    def test_to_dict_with_metadata(self):
        """测试 to_dict 包含完整信息"""
        msg = Message(
            "测试内容",
            "user",
            metadata={"key": "value"}
        )
        data = msg.to_dict()
        
        assert data["role"] == "user"
        assert data["content"] == "测试内容"
        assert data["metadata"] == {"key": "value"}
        assert "timestamp" in data
    
    def test_from_dict(self):
        """测试 from_dict 反序列化"""
        data = {
            "role": "assistant",
            "content": "回复内容",
            "timestamp": "2025-01-18T12:00:00",
            "metadata": {"test": True}
        }
        
        msg = Message.from_dict(data)
        assert msg.role == "assistant"
        assert msg.content == "回复内容"
        assert msg.metadata == {"test": True}
    
    def test_to_text(self):
        """测试 to_text 格式化"""
        msg = Message("hello", "user")
        assert msg.to_text() == "[user] hello"


class TestHistoryManager:
    """测试 HistoryManager"""
    
    def test_append_and_get(self):
        """测试消息追加和获取"""
        manager = HistoryManager()
        
        msg1 = Message("hello", "user")
        msg2 = Message("hi", "assistant")
        
        manager.append(msg1)
        manager.append(msg2)
        
        history = manager.get_history()
        assert len(history) == 2
        assert history[0].content == "hello"
        assert history[1].content == "hi"
    
    def test_estimate_rounds(self):
        """测试轮次估算"""
        manager = HistoryManager()
        
        # 第 1 轮
        manager.append(Message("问题1", "user"))
        manager.append(Message("回答1", "assistant"))
        
        # 第 2 轮
        manager.append(Message("问题2", "user"))
        manager.append(Message("回答2", "assistant"))
        manager.append(Message("工具结果", "tool"))
        
        # 第 3 轮
        manager.append(Message("问题3", "user"))
        
        assert manager.estimate_rounds() == 3
    
    def test_find_round_boundaries(self):
        """测试轮次边界检测"""
        manager = HistoryManager()
        
        manager.append(Message("问题1", "user"))  # index 0
        manager.append(Message("回答1", "assistant"))
        manager.append(Message("问题2", "user"))  # index 2
        manager.append(Message("回答2", "assistant"))
        
        boundaries = manager.find_round_boundaries()
        assert boundaries == [0, 2]
    
    def test_compress(self):
        """测试历史压缩"""
        manager = HistoryManager(min_retain_rounds=2)
        
        # 创建 5 轮对话
        for i in range(5):
            manager.append(Message(f"问题{i+1}", "user"))
            manager.append(Message(f"回答{i+1}", "assistant"))
        
        assert manager.estimate_rounds() == 5
        
        # 压缩历史
        manager.compress("前面3轮的摘要")
        
        # 应该保留最近 2 轮 + 1 条 summary
        history = manager.get_history()
        assert history[0].role == "summary"
        assert "前面3轮的摘要" in history[0].content
        
        # 验证保留了最近 2 轮（4 条消息）
        assert manager.estimate_rounds() == 2
        assert history[-1].content == "回答5"
    
    def test_compress_insufficient_rounds(self):
        """测试轮次不足时不压缩"""
        manager = HistoryManager(min_retain_rounds=10)
        
        # 只有 3 轮
        for i in range(3):
            manager.append(Message(f"问题{i+1}", "user"))
            manager.append(Message(f"回答{i+1}", "assistant"))
        
        original_len = len(manager.get_history())
        
        # 尝试压缩
        manager.compress("摘要")
        
        # 应该没有变化
        assert len(manager.get_history()) == original_len
    
    def test_to_dict_and_load(self):
        """测试序列化和反序列化"""
        manager = HistoryManager()
        
        manager.append(Message("hello", "user"))
        manager.append(Message("hi", "assistant"))
        
        # 序列化
        data = manager.to_dict()
        assert "history" in data
        assert "created_at" in data
        assert "rounds" in data
        assert data["rounds"] == 1
        
        # 反序列化
        new_manager = HistoryManager()
        new_manager.load_from_dict(data)
        
        history = new_manager.get_history()
        assert len(history) == 2
        assert history[0].content == "hello"
    
    def test_clear(self):
        """测试清空历史"""
        manager = HistoryManager()
        manager.append(Message("test", "user"))
        
        assert len(manager.get_history()) == 1
        
        manager.clear()
        assert len(manager.get_history()) == 0


class TestObservationTruncator:
    """测试 ObservationTruncator"""
    
    def setup_method(self):
        """每个测试前的设置"""
        self.test_output_dir = "test-tool-output"
        self.truncator = ObservationTruncator(
            max_lines=10,
            max_bytes=1000,
            truncate_direction="head",
            output_dir=self.test_output_dir
        )
    
    def teardown_method(self):
        """每个测试后的清理"""
        # 清理测试输出目录
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, file))
            os.rmdir(self.test_output_dir)
    
    def test_no_truncation_needed(self):
        """测试无需截断的情况"""
        output = "短输出\n只有几行"
        
        result = self.truncator.truncate("test_tool", output)
        
        assert result["truncated"] is False
        assert result["preview"] == output
        assert result["full_output_path"] is None
        assert "stats" in result
    
    def test_truncation_by_lines(self):
        """测试按行数截断"""
        # 生成 20 行输出
        lines = [f"Line {i+1}" for i in range(20)]
        output = "\n".join(lines)
        
        result = self.truncator.truncate("test_tool", output)
        
        assert result["truncated"] is True
        assert result["stats"]["original_lines"] == 20
        assert result["stats"]["kept_lines"] == 10
        assert result["full_output_path"] is not None
        
        # 验证文件已保存
        assert os.path.exists(result["full_output_path"])
        
        # 验证预览内容
        preview_lines = result["preview"].split("\n")
        assert len(preview_lines) == 10
        assert preview_lines[0] == "Line 1"
    
    def test_truncation_direction_tail(self):
        """测试 tail 方向截断"""
        truncator = ObservationTruncator(
            max_lines=5,
            truncate_direction="tail",
            output_dir=self.test_output_dir
        )
        
        lines = [f"Line {i+1}" for i in range(10)]
        output = "\n".join(lines)
        
        result = truncator.truncate("test_tool", output)
        
        preview_lines = result["preview"].split("\n")
        assert len(preview_lines) == 5
        assert preview_lines[0] == "Line 6"  # 保留最后 5 行
        assert preview_lines[-1] == "Line 10"
    
    def test_truncation_direction_head_tail(self):
        """测试 head_tail 方向截断"""
        truncator = ObservationTruncator(
            max_lines=6,  # 前3行 + 中间省略 + 后3行
            truncate_direction="head_tail",
            output_dir=self.test_output_dir
        )
        
        lines = [f"Line {i+1}" for i in range(20)]
        output = "\n".join(lines)
        
        result = truncator.truncate("test_tool", output)
        
        preview_lines = result["preview"].split("\n")
        assert "...(中间省略)..." in preview_lines
    
    def test_save_full_output(self):
        """测试完整输出保存"""
        output = "\n".join([f"Line {i+1}" for i in range(20)])
        metadata = {"query": "test", "timestamp": "2025-01-18"}
        
        result = self.truncator.truncate("search_tool", output, metadata)
        
        # 验证文件存在
        filepath = result["full_output_path"]
        assert os.path.exists(filepath)
        
        # 验证文件内容
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["tool"] == "search_tool"
        assert data["output"] == output
        assert data["metadata"] == metadata
        assert "timestamp" in data


class TestAgentIntegration:
    """本地组件集成；真实服务用例显式标记 live。"""

    def test_agent_history_manager_integration(self):
        """测试 Agent 集成 HistoryManager"""
        from hello_agents import SimpleAgent, HelloAgentsLLM

        llm = Mock(model="offline-components")
        config = Config(min_retain_rounds=2)
        agent = SimpleAgent("测试助手", llm, config=config)

        # 验证 HistoryManager 已初始化
        assert hasattr(agent, 'history_manager')
        assert isinstance(agent.history_manager, HistoryManager)

        # 测试 add_message
        agent.add_message(Message("test", "user"))
        assert len(agent.get_history()) == 1

        assert agent.history_manager.get_history()[0].content == "test"

        print("✅ Agent HistoryManager 集成测试通过")

    def test_agent_auto_compression(self):
        """先低于预算，再跨越 token 阈值；使用测试替身，不调用模型。"""
        from hello_agents import SimpleAgent

        llm = Mock()
        llm.model = "test-capture"
        config = Config(
            context_window=240, compression_threshold=0.75, min_retain_rounds=2,
            trace_enabled=False, skills_enabled=False, session_enabled=False,
            subagent_enabled=False, todowrite_enabled=False, devlog_enabled=False,
        )
        agent = SimpleAgent("测试助手", llm, config=config)
        agent.add_message(Message("短问题", "user"))
        agent.add_message(Message("短回复", "assistant"))
        assert all(msg.role != "summary" for msg in agent.get_history())

        added = []
        for i in range(4):
            question = Message(f"question-{i}: " + "evidence " * 50, "user")
            answer = Message(f"answer-{i}: " + "result " * 50, "assistant")
            added.extend([question, answer])
            agent.add_message(question)
            agent.add_message(answer)

        history = agent.get_history()
        assert history[0].role == "summary"
        assert [msg.content for msg in history[-4:]] == [msg.content for msg in added[-4:]]
        assert agent.history_manager.estimate_rounds() == 2
        llm.invoke.assert_not_called()

    def test_agent_truncator_integration(self):
        """测试 Agent 集成 ObservationTruncator"""
        from hello_agents import SimpleAgent, HelloAgentsLLM

        llm = Mock(model="offline-components")
        agent = SimpleAgent("测试助手", llm)

        # 验证 ObservationTruncator 已初始化
        assert hasattr(agent, 'truncator')
        assert isinstance(agent.truncator, ObservationTruncator)

        print("✅ Agent ObservationTruncator 集成测试通过")

    @pytest.mark.live
    def test_agent_real_conversation_with_compression(self, live_llm_config):
        """真实回答后加入足量本地历史，明确跨越压缩预算。"""
        from hello_agents import SimpleAgent, HelloAgentsLLM
        config = Config(min_retain_rounds=1, context_window=500,
                        compression_threshold=0.5, enable_smart_compression=False,
                        trace_enabled=False, session_enabled=False, skills_enabled=False,
                        subagent_enabled=False, todowrite_enabled=False, devlog_enabled=False)
        agent = SimpleAgent("上下文服务检查", HelloAgentsLLM(**live_llm_config), config=config)
        assert agent.run("用一句中文解释什么是上下文。")
        assert agent.last_run.status == "completed"
        for i in range(4):
            agent.add_message(Message(f"资料{i}: " + "evidence " * 150, "user"))
            agent.add_message(Message(f"确认{i}: " + "checked " * 150, "assistant"))
        assert any(message.role == "summary" for message in agent.get_history())
        assert agent.history_manager.estimate_rounds() <= config.min_retain_rounds


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

