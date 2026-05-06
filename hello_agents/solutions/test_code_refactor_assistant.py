"""CodeRefactorAssistant 测试代码
测试智能代码重构助手的各个组件：
- ApprovalPolicy: 审批策略
- CodeAnalyzer: 代码分析器
- RefactorTaskExecutor: 任务执行器
- CodeRefactorAssistant: 重构助手主类
"""

import unittest
import tempfile
import shutil
from pathlib import Path

# 导入被测试模块
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv

load_dotenv()
from hello_agents.solutions.code_refactor_assistant import (
    ApprovalPolicy,
    TaskResult,
    CodeAnalyzer,
    RefactorTaskExecutor,
    CodeRefactorAssistant,
)


class TestApprovalPolicy(unittest.TestCase):
    """测试审批策略"""

    def test_needs_approval_delete_file(self):
        """删除文件操作需要审批"""
        policy = ApprovalPolicy()
        task = {"type": "delete_file", "description": "删除测试文件"}
        self.assertTrue(policy.needs_approval(task))

    def test_needs_approval_rename(self):
        """重命名操作需要审批"""
        policy = ApprovalPolicy()
        task = {"type": "rename_refactor", "description": "重命名变量"}
        self.assertTrue(policy.needs_approval(task))

    def test_auto_approve_test_environment(self):
        """测试环境自动批准"""
        policy = ApprovalPolicy(auto_approve_test=True)
        task = {
            "type": "delete_file",
            "environment": "test",
            "description": "删除测试文件",
        }
        self.assertFalse(policy.needs_approval(task))

    def test_auto_approve_dry_run(self):
        """模拟运行自动批准"""
        policy = ApprovalPolicy(auto_approve_dry_run=True)
        task = {"type": "delete_file", "dry_run": True, "description": "模拟删除"}
        self.assertFalse(policy.needs_approval(task))

    def test_no_approval_required_for_safe_task(self):
        """安全任务不需要审批"""
        policy = ApprovalPolicy()
        task = {"type": "analyze", "description": "分析代码"}
        self.assertFalse(policy.needs_approval(task))


class TestTaskResult(unittest.TestCase):
    """测试任务结果"""

    def test_success_result(self):
        """成功结果"""
        result = TaskResult(
            status="success", message="任务执行成功", details={"files_modified": 3}
        )
        self.assertEqual(result.status, "success")
        self.assertIn("成功", result.message)
        self.assertFalse(result.approval_required)

    def test_pending_approval_result(self):
        """待审批结果"""
        result = TaskResult(
            status="pending_approval", message="需要用户审批", approval_required=True
        )
        self.assertTrue(result.approval_required)
        self.assertIn("审批", result.message)

    def test_to_dict(self):
        """转换为字典"""
        result = TaskResult(status="failed", message="执行失败")
        result_dict = result.to_dict()
        self.assertIn("status", result_dict)
        self.assertIn("message", result_dict)
        self.assertIn("timestamp", result_dict)

    def test_str_representation(self):
        """字符串表示"""
        result = TaskResult(status="success", message="完成")
        result_str = str(result)
        self.assertIn("✅", result_str)
        self.assertIn("SUCCESS", result_str)


class TestCodeAnalyzer(unittest.TestCase):
    """测试代码分析器"""

    def setUp(self):
        """设置测试环境"""
        # 创建临时项目目录
        self.test_dir = tempfile.mkdtemp()
        # 创建一些测试文件
        self.project_dir = Path(self.test_dir) / "project"
        self.project_dir.mkdir()
        # 创建测试Python文件
        (self.project_dir / "main.py").write_text("""
import os
import sys
from typing import List, Dict
def main():
    print("Hello World")
class Foo:
    def bar(self):
        pass
""")
        (self.project_dir / "utils.py").write_text("""
# TODO: 实现这个模块
from typing import Optional
def helper(x):
    return x * 2
""")
        # 配置TerminalTool
        from hello_agents.tools.builtin.terminal_tool import TerminalTool

        self.terminal = TerminalTool(workspace=str(self.project_dir))
        self.analyzer = CodeAnalyzer(self.terminal)

    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)

    def test_analyze_structure(self):
        """分析代码结构"""
        results = self.analyzer.analyze_structure()
        self.assertIn("file_count", results)
        self.assertIn("total_lines", results)
        self.assertGreater(results["file_count"], 0)

    def test_detect_code_smells(self):
        """检测代码气味"""
        smells = self.analyzer.detect_code_smells()
        # 应该检测到TODO注释
        todo_smells = [s for s in smells if s["type"] == "todo_comment"]
        self.assertGreater(len(todo_smells), 0)

    def test_analyze_dependencies(self):
        """分析依赖关系"""
        deps = self.analyzer.analyze_dependencies()
        self.assertIn("total_imports", deps)
        self.assertGreater(deps["total_imports"], 0)


class TestRefactorTaskExecutor(unittest.TestCase):
    """测试任务执行器"""

    def setUp(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        self.workspace_dir = Path(self.test_dir) / "workspace"
        self.workspace_dir.mkdir()
        # 创建项目目录
        self.project_dir = Path(self.test_dir) / "project"
        self.project_dir.mkdir()
        # 导入工具
        from hello_agents.tools.builtin.terminal_tool import TerminalTool
        from hello_agents.tools.builtin.note_tool import NoteTool

        self.terminal = TerminalTool(workspace=str(self.project_dir))
        self.note = NoteTool(workspace=str(self.workspace_dir))
        self.policy = ApprovalPolicy()
        self.executor = RefactorTaskExecutor(self.terminal, self.note, self.policy)

    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)

    def test_execute_create_backup(self):
        """执行创建备份"""
        task = {
            "type": "create_backup",
            "description": "创建备份",
            "file_pattern": "*.py",
            "backup_dir": "./backups",
        }
        result = self.executor.execute_task(task)
        self.assertEqual(result.status, "success")
        self.assertIn("备份", result.message)

    def test_execute_rename_without_params(self):
        """执行重命名缺少参数"""
        task = {"type": "rename", "description": "重命名"}
        result = self.executor.execute_task(task)
        self.assertEqual(result.status, "failed")
        self.assertIn("缺少", result.message)

    def test_execute_unknown_type(self):
        """执行未知任务类型"""
        task = {"type": "unknown_type", "description": "未知任务"}
        result = self.executor.execute_task(task)
        self.assertEqual(result.status, "failed")
        self.assertIn("未知", result.message)

    def test_get_state(self):
        """获取执行状态"""
        state = self.executor.get_state()
        self.assertIn("task_state", state)
        self.assertIn("history_count", state)


class TestCodeRefactorAssistant(unittest.TestCase):
    """测试重构助手主类"""

    def setUp(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        # 创建项目目录
        self.project_dir = Path(self.test_dir) / "project"
        self.project_dir.mkdir()
        # 创建测试文件
        (self.project_dir / "main.py").write_text("""
from typing import List
def hello():
    print("Hello")
""")
        # 创建工作区
        self.workspace_dir = Path(self.test_dir) / "workspace"
        self.workspace_dir.mkdir()

    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """测试初始化"""
        assistant = CodeRefactorAssistant(
            project_path=str(self.project_dir), workspace=str(self.workspace_dir)
        )
        self.assertTrue(assistant.project_dir.exists())
        self.assertTrue(assistant.workspace.exists())
        self.assertIsNotNone(assistant.terminal)
        self.assertIsNotNone(assistant.note)

    def test_analyze_empty_project(self):
        """分析空项目"""
        assistant = CodeRefactorAssistant(
            project_path=str(self.project_dir), workspace=str(self.workspace_dir)
        )
        report = assistant.analyze()
        self.assertIsNotNone(report)
        self.assertIn("分析报告", report)

    def test_create_plan(self):
        """创建重构计划"""
        assistant = CodeRefactorAssistant(
            project_path=str(self.project_dir), workspace=str(self.workspace_dir)
        )
        plan_id = assistant.create_plan(focus_areas=["models"], max_risk="low")
        # 应该创建笔记
        self.assertIsNotNone(plan_id)

    def test_execute_plan_without_plan(self):
        """执行不存在的计划"""
        assistant = CodeRefactorAssistant(
            project_path=str(self.project_dir), workspace=str(self.workspace_dir)
        )
        result = assistant.execute_plan(plan_id="nonexistent")
        self.assertIn("❌", result)

    def test_save_and_restore_checkpoint(self):
        """保存和恢复断点"""
        assistant = CodeRefactorAssistant(
            project_path=str(self.project_dir), workspace=str(self.workspace_dir)
        )
        # 先分析
        assistant.analyze()
        # 再创建计划
        assistant.create_plan(max_risk="low")
        # 保存断点
        checkpoint_id = assistant._save_checkpoint()
        self.assertIsNotNone(checkpoint_id)
        # 恢复断点
        restore_result = assistant.restore_checkpoint(checkpoint_id)
        self.assertIn("✅", restore_result)

    def test_get_progress(self):
        """获取进度"""
        assistant = CodeRefactorAssistant(
            project_path=str(self.project_dir), workspace=str(self.workspace_dir)
        )
        progress = assistant.get_progress()
        self.assertIsNotNone(progress)
        self.assertIn("重构进度", progress)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        """设置测试环境"""
        self.test_dir = tempfile.mkdtemp()
        # 创建项目目录
        self.project_dir = Path(self.test_dir) / "project"
        self.project_dir.mkdir()
        # 创建测试Python项目
        (self.project_dir / "models.py").write_text("""
from typing import List, Optional
class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email    
    def get_name(self):
        return self.name
class Product:
    def __init__(self, name: str, price: float):
        self.name = name
        self.price = price
""")
        (self.project_dir / "services.py").write_text("""
# TODO: 重构这个文件
from .models import User, Product
def create_user(name, email):
    return User(name, email)
""")
        # 创建工作区
        self.workspace_dir = Path(self.test_dir) / "workspace"
        self.workspace_dir.mkdir()

    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.test_dir)

    def test_full_refactor_flow(self):
        """完整重构流程"""
        assistant = CodeRefactorAssistant(
            project_path=str(self.project_dir), workspace=str(self.workspace_dir)
        )
        # 1. 分析代码库
        report = assistant.analyze()
        self.assertIsNotNone(report)
        self.assertIn("分析报告", report)
        # 2. 创建计划
        plan_id = assistant.create_plan(focus_areas=["models"], max_risk="low")
        self.assertIsNotNone(plan_id)
        # 3. 执行计划
        result = assistant.execute_plan(plan_id=plan_id, auto_approve=True)
        self.assertIsNotNone(result)
        # 4. 查看进度
        progress = assistant.get_progress()
        self.assertIn("重构进度", progress)


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
