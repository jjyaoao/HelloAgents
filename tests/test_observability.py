"""可观测性模块测试"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from hello_agents.observability import TraceLogger


class TestTraceLogger:
    """TraceLogger 核心功能测试"""
    
    def setup_method(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """每个测试后清理临时目录"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_session_id_generation(self):
        """测试会话 ID 生成"""
        logger = TraceLogger(output_dir=self.temp_dir)
        
        # 验证格式: s-YYYYMMDD-HHMMSS-xxxx
        assert logger.session_id.startswith("s-")
        parts = logger.session_id.split("-")
        assert len(parts) == 4
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # HHMMSS
        assert len(parts[3]) == 4  # random suffix
        
        logger.finalize()
    
    def test_log_event_creates_jsonl(self):
        """测试事件记录到 JSONL"""
        logger = TraceLogger(output_dir=self.temp_dir)
        
        # 记录事件
        logger.log_event(
            "session_start",
            {"agent_name": "TestAgent", "config": {}}
        )
        logger.log_event(
            "tool_call",
            {"tool_name": "Calculator", "args": {"input": "2+2"}},
            step=1
        )
        
        logger.finalize()
        
        # 验证 JSONL 文件存在
        jsonl_path = Path(self.temp_dir) / f"trace-{logger.session_id}.jsonl"
        assert jsonl_path.exists()
        
        # 验证内容
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 2
            
            # 解析第一个事件
            event1 = json.loads(lines[0])
            assert event1["event"] == "session_start"
            assert event1["session_id"] == logger.session_id
            assert event1["payload"]["agent_name"] == "TestAgent"
            
            # 解析第二个事件
            event2 = json.loads(lines[1])
            assert event2["event"] == "tool_call"
            assert event2["step"] == 1
            assert event2["payload"]["tool_name"] == "Calculator"
    
    def test_html_generation(self):
        """测试 HTML 文件生成"""
        logger = TraceLogger(output_dir=self.temp_dir)
        
        # 记录一些事件
        logger.log_event("session_start", {"agent_name": "TestAgent"})
        logger.log_event("tool_call", {"tool_name": "Calculator"}, step=1)
        logger.log_event("tool_result", {"result": "4"}, step=1)
        logger.log_event("model_output", {"usage": {"total_tokens": 100}}, step=1)
        
        logger.finalize()
        
        # 验证 HTML 文件存在
        html_path = Path(self.temp_dir) / f"trace-{logger.session_id}.html"
        assert html_path.exists()
        
        # 验证 HTML 内容
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            assert "<!DOCTYPE html>" in html_content
            assert logger.session_id in html_content
            assert "session_start" in html_content
            assert "tool_call" in html_content
            assert "Calculator" in html_content
            assert "统计" in html_content  # 统计面板
    
    def test_sanitize_api_key(self):
        """测试 API Key 脱敏"""
        logger = TraceLogger(output_dir=self.temp_dir, sanitize=True)
        
        # 记录包含 API Key 的事件
        logger.log_event(
            "model_output",
            {
                "api_key": "sk-1234567890abcdef",
                "auth": "Bearer token_secret_123"
            }
        )
        
        logger.finalize()
        
        # 验证脱敏
        jsonl_path = Path(self.temp_dir) / f"trace-{logger.session_id}.jsonl"
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            event = json.loads(f.read())
            payload_str = json.dumps(event["payload"])
            assert "sk-***" in payload_str
            assert "Bearer ***" in payload_str
            assert "1234567890abcdef" not in payload_str
            assert "token_secret_123" not in payload_str
    
    def test_stats_computation(self):
        """测试统计数据计算"""
        logger = TraceLogger(output_dir=self.temp_dir)
        
        # 记录会话开始
        logger.log_event("session_start", {"agent_name": "TestAgent"})
        
        # 记录多个步骤
        for step in range(1, 4):
            logger.log_event("tool_call", {"tool_name": "Calculator"}, step=step)
            logger.log_event("tool_result", {"result": str(step * 2)}, step=step)
            logger.log_event(
                "model_output",
                {"usage": {"total_tokens": 100, "cost": 0.001}},
                step=step
            )
        
        # 记录错误
        logger.log_event(
            "error",
            {"error_type": "TIMEOUT", "message": "Tool timeout"},
            step=2
        )
        
        # 记录会话结束
        logger.log_event("session_end", {"duration": 10.5})
        
        # 计算统计
        stats = logger._compute_stats()
        
        assert stats["total_steps"] == 3
        assert stats["total_tokens"] == 300  # 3 * 100
        assert stats["total_cost"] == 0.003  # 3 * 0.001
        assert stats["model_calls"] == 3
        assert stats["tool_calls"]["Calculator"] == 3
        assert len(stats["errors"]) == 1
        assert stats["errors"][0]["type"] == "TIMEOUT"
        
        logger.finalize()
    
    def test_context_manager(self):
        """测试上下文管理器"""
        with TraceLogger(output_dir=self.temp_dir) as logger:
            logger.log_event("session_start", {"agent_name": "TestAgent"})
            logger.log_event("tool_call", {"tool_name": "Calculator"}, step=1)
        
        # 验证文件已生成（自动 finalize）
        jsonl_path = Path(self.temp_dir) / f"trace-{logger.session_id}.jsonl"
        html_path = Path(self.temp_dir) / f"trace-{logger.session_id}.html"
        assert jsonl_path.exists()
        assert html_path.exists()
    
    def test_context_manager_with_exception(self):
        """测试上下文管理器异常处理"""
        try:
            with TraceLogger(output_dir=self.temp_dir) as logger:
                logger.log_event("session_start", {"agent_name": "TestAgent"})
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # 验证异常被记录
        jsonl_path = Path(self.temp_dir) / f"trace-{logger.session_id}.jsonl"
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # 最后一个事件应该是错误
            last_event = json.loads(lines[-1])
            assert last_event["event"] == "error"
            assert last_event["payload"]["error_type"] == "ValueError"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

