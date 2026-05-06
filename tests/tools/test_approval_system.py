"""TerminalTool 审批系统测试代码

本文件包含 ApprovalManager 和 SecureTerminalTool 的完整测试用例。

运行方式：
    python -m pytest tests/test_approval_system.py -v

或直接运行：
    python tests/test_approval_system.py
"""

import unittest
import threading
import time
import os
import tempfile
import shutil
import platform
from pathlib import Path

from hello_agents.tools.builtin.approval_manager import (
    ApprovalManager,
    AsyncApprovalManager,
    ApprovalStatus,
    RiskLevel,
)

from hello_agents.tools.builtin.secure_terminal_tool import (
    SecureTerminalTool,
    create_with_approval,
)


IS_WINDOWS = platform.system().lower() == "windows"


class TestApprovalManager(unittest.TestCase):
    """ApprovalManager 单元测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, "audit.log")
        self.manager = ApprovalManager(
            default_timeout=60,
            audit_log_path=self.log_file,
        )

    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_request_approval(self):
        """测试发起审批请求"""
        request_id = self.manager.request_approval(
            agent_id="test_agent",
            command="ls -la",
            risk_level=RiskLevel.LOW,
            context={"workspace": "/tmp"},
        )

        self.assertIsNotNone(request_id)
        self.assertEqual(len(request_id), 8)

        status = self.manager.get_status(request_id)
        self.assertIsNotNone(status)
        self.assertEqual(status.agent_id, "test_agent")
        self.assertEqual(status.command, "ls -la")
        self.assertEqual(status.risk_level, RiskLevel.LOW)
        self.assertEqual(status.status, ApprovalStatus.PENDING)

    def test_approve_request(self):
        """测试批准请求"""
        request_id = self.manager.request_approval(
            agent_id="test_agent",
            command="python -c 'print(1)'",
            risk_level=RiskLevel.MEDIUM,
        )

        result = self.manager.approve(request_id, approver="admin")
        self.assertTrue(result)

        status = self.manager.get_status(request_id)
        self.assertEqual(status.status, ApprovalStatus.APPROVED)
        self.assertEqual(status.approved_by, "admin")

    def test_reject_request(self):
        """测试拒绝请求"""
        request_id = self.manager.request_approval(
            agent_id="test_agent",
            command="rm -rf /",
            risk_level=RiskLevel.CRITICAL,
        )

        result = self.manager.reject(
            request_id, reason="危险操作，不允许执行", rejector="admin"
        )
        self.assertTrue(result)

        status = self.manager.get_status(request_id)
        self.assertEqual(status.status, ApprovalStatus.REJECTED)
        self.assertEqual(status.rejected_by, "admin")
        self.assertEqual(status.rejection_reason, "危险操作，不允许执行")

    def test_cancel_request(self):
        """测试取消请求"""
        request_id = self.manager.request_approval(
            agent_id="test_agent",
            command="ls",
            risk_level=RiskLevel.LOW,
        )

        result = self.manager.cancel(request_id)
        self.assertTrue(result)

        status = self.manager.get_status(request_id)
        self.assertEqual(status.status, ApprovalStatus.CANCELLED)

    def test_list_pending(self):
        """测试列出待审批请求"""
        for i in range(3):
            self.manager.request_approval(
                agent_id=f"agent_{i}",
                command=f"ls {i}",
                risk_level=RiskLevel.LOW,
            )

        self.manager.request_approval(
            agent_id="test_agent",
            command="python script.py",
            risk_level=RiskLevel.MEDIUM,
        )

        pending = self.manager.list_pending()
        self.assertEqual(len(pending), 4)

        self.manager.approve(pending[0].id)
        pending = self.manager.list_pending()
        self.assertEqual(len(pending), 3)

    def test_check_timeout(self):
        """测试超时检查"""
        manager = ApprovalManager(default_timeout=1)

        request_id = manager.request_approval(
            agent_id="test_agent",
            command="ls",
            risk_level=RiskLevel.LOW,
        )

        time.sleep(1.5)

        timed_out = manager.check_timeout()
        self.assertIn(request_id, timed_out)

        status = manager.get_status(request_id)
        self.assertEqual(status.status, ApprovalStatus.TIMEOUT)

    def test_callback(self):
        """测试回调机制"""
        callback_called = []

        def callback(request):
            callback_called.append(request.id)

        self.manager.add_callback(callback)

        request_id = self.manager.request_approval(
            agent_id="test_agent",
            command="ls",
            risk_level=RiskLevel.LOW,
        )

        self.assertEqual(len(callback_called), 1)
        self.assertEqual(callback_called[0], request_id)

        self.manager.remove_callback(callback)

        self.manager.request_approval(
            agent_id="test_agent",
            command="ls",
            risk_level=RiskLevel.LOW,
        )

        self.assertEqual(len(callback_called), 1)

    def test_audit_log(self):
        """测试审计日志"""
        request_id = self.manager.request_approval(
            agent_id="test_agent",
            command="ls",
            risk_level=RiskLevel.LOW,
        )

        self.manager.approve(request_id, approver="admin")

        logs = self.manager.get_audit_logs()
        self.assertGreaterEqual(len(logs), 2)

        event_types = [log.event_type for log in logs]
        self.assertIn("approval_requested", event_types)
        self.assertIn("approval_approved", event_types)

    def test_statistics(self):
        """测试统计信息"""
        self.manager.request_approval(
            agent_id="agent_1",
            command="ls",
            risk_level=RiskLevel.LOW,
        )
        self.manager.request_approval(
            agent_id="agent_2",
            command="cat file.txt",
            risk_level=RiskLevel.MEDIUM,
        )

        request_id = self.manager.request_approval(
            agent_id="agent_3",
            command="rm file",
            risk_level=RiskLevel.CRITICAL,
        )

        self.manager.approve(request_id)

        stats = self.manager.get_statistics()
        self.assertEqual(stats["total_requests"], 3)
        self.assertEqual(stats["approved"], 1)
        self.assertEqual(stats["pending"], 2)

    def test_risk_summary(self):
        """测试风险摘要生成"""
        request_id = self.manager.request_approval(
            agent_id="test_agent",
            command="rm -rf /",
            risk_level=RiskLevel.CRITICAL,
        )

        status = self.manager.get_status(request_id)
        self.assertIn("递归删除", status.risk_summary)


class TestAsyncApprovalManager(unittest.TestCase):
    """异步审批管理器测试"""

    def test_async_wait_for_decision(self):
        """测试异步等待决策"""
        manager = AsyncApprovalManager(default_timeout=10)

        request_id, event = manager.request_approval_async(
            agent_id="test_agent",
            command="ls",
            risk_level=RiskLevel.LOW,
        )

        self.assertFalse(event.is_set())

        def approve_later():
            time.sleep(0.5)
            manager.approve(request_id, approver="admin")

        thread = threading.Thread(target=approve_later)
        thread.start()

        status = manager.wait_for_decision(request_id, timeout=5)
        self.assertEqual(status, ApprovalStatus.APPROVED)

        thread.join()


class TestSecureTerminalTool(unittest.TestCase):
    """SecureTerminalTool 单元测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        Path(self.temp_dir, "test.txt").write_text("hello world")
        Path(self.temp_dir, ".env").write_text("SECRET=123")
        Path(self.temp_dir, "subdir").mkdir()
        Path(self.temp_dir, "subdir", "config.json").write_text('{"key": "value"}')

        self.manager = ApprovalManager()
        self.terminal = SecureTerminalTool(
            workspace=self.temp_dir,
            approval_manager=self.manager,
            agent_id="test_agent",
        )

        self.list_cmd = "dir" if IS_WINDOWS else "ls"

    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_low_risk_command(self):
        """测试低风险命令直接执行"""
        result = self.terminal.run({"command": self.list_cmd})
        self.assertNotIn("⏳", result)
        self.assertNotIn("等待审批", result)

    def test_medium_risk_command(self):
        """测试中风险命令需要审批"""
        result = self.terminal.run({"command": "python -c 'print(1)'"})
        self.assertIn("⏳", result)

    def test_high_risk_path_traversal(self):
        """测试高风险路径遍历"""
        if IS_WINDOWS:
            result = self.terminal.run({"command": "type ..\\test.txt"})
        else:
            result = self.terminal.run({"command": "cat ../test.txt"})
        self.assertIn("⏳", result)
        self.assertIn("HIGH", result)

    def test_critical_dangerous_command(self):
        """测试极高风险危险命令拦截"""
        if IS_WINDOWS:
            command = 'powershell -c "Remove-Item -Path C:\\Windows\\System32\\* -Recurse -Force"'
        else:
            command = "rm -rf /"

        risk_level = self.terminal.get_risk_level(command)
        self.assertEqual(risk_level, RiskLevel.CRITICAL)

        result = self.terminal.run({"command": command})
        self.assertTrue(
            "危险" in result
            or "审批" in result
            or "审批请求已提交" in result
            or "等待审批" in result
        )

    def test_sensitive_file_warning(self):
        """测试敏感文件警告"""
        if IS_WINDOWS:
            result = self.terminal.run({"command": "type .env"})
        else:
            result = self.terminal.run({"command": "cat .env"})
        self.assertIn("⏳", result)

    def test_execute_approved(self):
        """测试执行已批准的请求"""
        request_id = self.manager.request_approval(
            agent_id="test_agent",
            command=self.list_cmd,
            risk_level=RiskLevel.LOW,
        )

        self.manager.approve(request_id)

        result = self.terminal.execute_approved(request_id)
        self.assertIsNotNone(result)

    def test_get_risk_level(self):
        """测试获取风险等级"""
        self.assertEqual(self.terminal.get_risk_level(self.list_cmd), RiskLevel.LOW)
        self.assertEqual(
            self.terminal.get_risk_level("python -c 'print(1)'"), RiskLevel.MEDIUM
        )
        if IS_WINDOWS:
            self.assertEqual(
                self.terminal.get_risk_level("type ..\\file.txt"), RiskLevel.HIGH
            )
        else:
            self.assertEqual(
                self.terminal.get_risk_level("cat ../file.txt"), RiskLevel.HIGH
            )

    def test_preview_command(self):
        """测试预览命令信息"""
        preview = self.terminal.preview_command(self.list_cmd)

        self.assertEqual(preview["risk_level"], "low")
        self.assertFalse(preview["requires_approval"])

        if IS_WINDOWS:
            preview = self.terminal.preview_command("type ..\\.env")
        else:
            preview = self.terminal.preview_command("cat ../.env")
        self.assertEqual(preview["risk_level"], "high")
        self.assertTrue(preview["requires_approval"])

    def test_path_validation(self):
        """测试路径验证"""
        if IS_WINDOWS:
            cd_cmd = "cd subdir"
        else:
            cd_cmd = "cd subdir"

        result = self.terminal.run({"command": cd_cmd})
        if IS_WINDOWS:
            self.assertTrue(
                "subdir" in result or "✅" in result or "当前目录" in result
            )
        else:
            self.assertIn("✅", result)

    def test_callback_integration(self):
        """测试回调集成"""
        received_requests = []

        def on_request(request):
            received_requests.append(request.id)

        self.manager.add_callback(on_request)

        self.terminal.run({"command": "python -c 'print(1)'"})

        self.assertEqual(len(received_requests), 1)

    def test_factory_function(self):
        """测试工厂函数"""
        terminal = create_with_approval(
            workspace=self.temp_dir,
            approval_manager=self.manager,
            agent_id="factory_test",
        )

        self.assertIsInstance(terminal, SecureTerminalTool)
        self.assertEqual(terminal.agent_id, "factory_test")


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        Path(self.temp_dir, "data.csv").write_text("a,b,c\n1,2,3")

        self.manager = ApprovalManager()
        self.terminal = SecureTerminalTool(
            workspace=self.temp_dir,
            approval_manager=self.manager,
            agent_id="integration_test",
        )

    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_approval_workflow(self):
        """测试完整审批工作流"""
        command = "python -c 'import os; print(os.listdir())'"
        result = self.terminal.run({"command": command})
        self.assertIn("⏳", result)
        self.assertIn("request_id:", result)

    def test_rejection_workflow(self):
        """测试拒绝工作流"""
        if IS_WINDOWS:
            command = "cmd /c del data.csv"
        else:
            command = "rm -rf data.csv"
        result = self.terminal.run({"command": command})
        self.assertTrue("❌" in result or "不允许" in result or "审批" in result)

    def test_statistics_integration(self):
        """测试统计集成"""
        self.terminal.run({"command": "python -c 'print(1)'"})
        if IS_WINDOWS:
            self.terminal.run({"command": "type .env"})
        else:
            self.terminal.run({"command": "cat .env"})

        for request in self.manager.list_pending():
            self.manager.approve(request.id)

        stats = self.manager.get_statistics()
        self.assertGreater(stats["approved"], 0)

    def test_audit_trail(self):
        """测试审计追踪"""
        self.terminal.run({"command": "python -c 'print(1)'"})
        if IS_WINDOWS:
            self.terminal.run({"command": "type .env"})
        else:
            self.terminal.run({"command": "cat .env"})

        for request in self.manager.list_pending():
            self.manager.approve(request.id)

        logs = self.manager.get_audit_logs()
        event_types = [log.event_type for log in logs]

        self.assertIn("approval_requested", event_types)
        self.assertIn("approval_approved", event_types)


class TestEdgeCases(unittest.TestCase):
    """边界情况测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = ApprovalManager()
        self.terminal = SecureTerminalTool(
            workspace=self.temp_dir,
            approval_manager=self.manager,
        )

    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_empty_command(self):
        """测试空命令"""
        result = self.terminal.run({"command": ""})
        self.assertIn("❌", result)

    def test_invalid_command(self):
        """测试无效命令"""
        result = self.terminal.run({"command": "invalid_command_xyz"})
        self.assertIn("❌", result)

    def test_nonexistent_file(self):
        """测试不存在的文件"""
        if IS_WINDOWS:
            result = self.terminal.run({"command": "type nonexistent.txt"})
        else:
            result = self.terminal.run({"command": "cat nonexistent.txt"})
        self.assertNotIn("审批请求已提交", result)

    def test_double_approval(self):
        """测试重复批准"""
        request_id = self.manager.request_approval(
            agent_id="test",
            command="ls",
            risk_level=RiskLevel.LOW,
        )

        self.assertTrue(self.manager.approve(request_id))
        self.assertFalse(self.manager.approve(request_id))

    def test_approval_after_timeout(self):
        """测试超时后批准"""
        manager = ApprovalManager(default_timeout=1)
        terminal = SecureTerminalTool(
            workspace=self.temp_dir,
            approval_manager=manager,
        )

        request_id = manager.request_approval(
            agent_id="test",
            command="ls",
            risk_level=RiskLevel.LOW,
        )

        time.sleep(1.5)
        manager.check_timeout()

        result = terminal.execute_approved(request_id)
        self.assertIn("尚未批准", result)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestApprovalManager))
    suite.addTests(loader.loadTestsFromTestCase(TestAsyncApprovalManager))
    suite.addTests(loader.loadTestsFromTestCase(TestSecureTerminalTool))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
