"""TodoWrite 进度管理工具测试"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from hello_agents.tools.builtin.todowrite_tool import TodoWriteTool, TodoItem, TodoList
from hello_agents.tools.response import ToolResponse, ToolStatus
from hello_agents.tools.errors import ToolErrorCode
from hello_agents import ToolRegistry, ReActAgent, HelloAgentsLLM, Config
from dotenv import load_dotenv
load_dotenv()

class TestTodoDataModel:
    """测试 Todo 数据模型"""

    def test_todo_item_creation(self):
        """测试 TodoItem 创建"""
        now = datetime.now().isoformat()
        item = TodoItem(
            content="实现用户认证",
            status="pending",
            created_at=now
        )

        assert item.content == "实现用户认证"
        assert item.status == "pending"
        assert item.created_at == now
        assert item.updated_at == now  # 自动填充

    def test_todo_item_with_updated_at(self):
        """测试 TodoItem 带更新时间"""
        now = datetime.now().isoformat()
        later = datetime.now().isoformat()
        item = TodoItem(
            content="实现订单处理",
            status="in_progress",
            created_at=now,
            updated_at=later
        )

        assert item.updated_at == later

    def test_todo_list_stats(self):
        """测试 TodoList 统计"""
        now = datetime.now().isoformat()
        todos = TodoList(
            summary="实现电商系统",
            todos=[
                TodoItem("任务1", "completed", now),
                TodoItem("任务2", "completed", now),
                TodoItem("任务3", "in_progress", now),
                TodoItem("任务4", "pending", now),
                TodoItem("任务5", "pending", now),
            ]
        )

        stats = todos.get_stats()
        assert stats["total"] == 5
        assert stats["completed"] == 2
        assert stats["in_progress"] == 1
        assert stats["pending"] == 2

    def test_todo_list_get_in_progress(self):
        """测试获取进行中的任务"""
        now = datetime.now().isoformat()
        todos = TodoList(
            summary="测试",
            todos=[
                TodoItem("任务1", "completed", now),
                TodoItem("任务2", "in_progress", now),
                TodoItem("任务3", "pending", now),
            ]
        )

        in_progress = todos.get_in_progress()
        assert in_progress is not None
        assert in_progress.content == "任务2"
        assert in_progress.status == "in_progress"

    def test_todo_list_get_pending(self):
        """测试获取待处理任务"""
        now = datetime.now().isoformat()
        todos = TodoList(
            summary="测试",
            todos=[
                TodoItem("任务1", "pending", now),
                TodoItem("任务2", "pending", now),
                TodoItem("任务3", "pending", now),
                TodoItem("任务4", "in_progress", now),
            ]
        )

        pending = todos.get_pending(limit=2)
        assert len(pending) == 2
        assert all(t.status == "pending" for t in pending)

    def test_todo_list_get_completed(self):
        """测试获取已完成任务"""
        now = datetime.now().isoformat()
        todos = TodoList(
            summary="测试",
            todos=[
                TodoItem("任务1", "completed", now),
                TodoItem("任务2", "completed", now),
                TodoItem("任务3", "pending", now),
            ]
        )

        completed = todos.get_completed()
        assert len(completed) == 2
        assert all(t.status == "completed" for t in completed)


class TestTodoWriteTool:
    """测试 TodoWriteTool"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    @pytest.fixture
    def tool(self, temp_dir):
        """创建 TodoWriteTool 实例"""
        return TodoWriteTool(
            project_root=temp_dir,
            persistence_dir="todos"
        )

    def test_tool_initialization(self, tool, temp_dir):
        """测试工具初始化"""
        assert tool.name == "TodoWrite"
        assert tool.project_root == Path(temp_dir)
        assert tool.persistence_dir.exists()
        assert tool.current_todos.summary == ""
        assert len(tool.current_todos.todos) == 0

    def test_create_todo_list(self, tool):
        """测试创建任务列表"""
        response = tool.run({
            "summary": "实现用户系统",
            "todos": [
                {"content": "实现用户注册", "status": "completed"},
                {"content": "实现用户登录", "status": "in_progress"},
                {"content": "实现权限管理", "status": "pending"},
            ],
            "action": "create"
        })

        assert isinstance(response, ToolResponse)
        assert response.status == ToolStatus.SUCCESS
        assert "实现用户系统" in tool.current_todos.summary
        assert len(tool.current_todos.todos) == 3

        # 验证 Recap
        assert "[1/3]" in response.text
        assert "进行中: 实现用户登录" in response.text

    def test_validate_single_in_progress_constraint(self, tool):
        """测试单个 in_progress 约束"""
        # 尝试创建多个 in_progress 任务
        response = tool.run({
            "todos": [
                {"content": "任务1", "status": "in_progress"},
                {"content": "任务2", "status": "in_progress"},
            ]
        })

        assert response.status == ToolStatus.ERROR
        assert response.error_info["code"] == ToolErrorCode.INVALID_PARAM
        assert "最多只能有 1 个 in_progress" in response.error_info["message"]

    def test_validate_empty_content(self, tool):
        """测试空内容验证"""
        response = tool.run({
            "todos": [
                {"content": "", "status": "pending"},
            ]
        })

        assert response.status == ToolStatus.ERROR
        assert response.error_info["code"] == ToolErrorCode.INVALID_PARAM
        assert "content 不能为空" in response.error_info["message"]

    def test_validate_invalid_status(self, tool):
        """测试无效状态验证"""
        response = tool.run({
            "todos": [
                {"content": "任务1", "status": "invalid_status"},
            ]
        })

        assert response.status == ToolStatus.ERROR
        assert response.error_info["code"] == ToolErrorCode.INVALID_PARAM
        assert "status 必须是" in response.error_info["message"]

    def test_clear_action(self, tool):
        """测试清空操作"""
        # 先创建任务列表
        tool.run({
            "todos": [
                {"content": "任务1", "status": "pending"},
            ]
        })

        # 清空
        response = tool.run({"action": "clear"})

        assert response.status == ToolStatus.SUCCESS
        assert "已清空" in response.text
        assert len(tool.current_todos.todos) == 0

    def test_recap_generation_all_completed(self, tool):
        """测试 Recap 生成 - 全部完成"""
        response = tool.run({
            "todos": [
                {"content": "任务1", "status": "completed"},
                {"content": "任务2", "status": "completed"},
            ]
        })

        assert "✅" in response.text
        assert "[2/2]" in response.text
        assert "所有任务已完成" in response.text

    def test_recap_generation_with_pending(self, tool):
        """测试 Recap 生成 - 有待处理任务"""
        response = tool.run({
            "todos": [
                {"content": "任务1", "status": "completed"},
                {"content": "任务2", "status": "in_progress"},
                {"content": "任务3", "status": "pending"},
                {"content": "任务4", "status": "pending"},
            ]
        })

        assert "[1/4]" in response.text
        assert "进行中: 任务2" in response.text
        assert "待处理: 任务3; 任务4" in response.text

    def test_recap_generation_many_pending(self, tool):
        """测试 Recap 生成 - 多个待处理任务"""
        todos = [{"content": f"任务{i}", "status": "pending"} for i in range(10)]
        todos[0]["status"] = "in_progress"

        response = tool.run({"todos": todos})

        assert "还有" in response.text  # "还有 N 个..."

    def test_persistence(self, tool):
        """测试持久化"""
        tool.run({
            "summary": "测试持久化",
            "todos": [
                {"content": "任务1", "status": "pending"},
            ]
        })

        # 检查文件是否创建
        files = list(tool.persistence_dir.glob("todoList-*.json"))
        assert len(files) > 0

        # 验证文件内容
        with open(files[0], 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert data["summary"] == "测试持久化"
        assert len(data["todos"]) == 1
        assert data["todos"][0]["content"] == "任务1"
        assert "stats" in data

    def test_load_todos(self, tool, temp_dir):
        """测试加载任务列表"""
        # 创建测试文件
        test_data = {
            "summary": "加载测试",
            "todos": [
                {
                    "content": "任务1",
                    "status": "completed",
                    "created_at": "2025-01-01T00:00:00",
                    "updated_at": "2025-01-01T00:00:00"
                }
            ],
            "created_at": "2025-01-01T00:00:00",
            "stats": {"total": 1, "completed": 1, "in_progress": 0, "pending": 0}
        }

        test_file = Path(temp_dir) / "test_load.json"
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)

        # 加载
        tool.load_todos(str(test_file))

        assert tool.current_todos.summary == "加载测试"
        assert len(tool.current_todos.todos) == 1
        assert tool.current_todos.todos[0].content == "任务1"

    def test_json_string_parameter(self, tool):
        """测试 JSON 字符串参数"""
        # 传入 JSON 字符串而非对象
        response = tool.run({
            "todos": json.dumps([
                {"content": "任务1", "status": "pending"}
            ])
        })

        assert response.status == ToolStatus.SUCCESS
        assert len(tool.current_todos.todos) == 1


class TestAgentIntegration:
    """测试 Agent 集成"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    def test_auto_register_todowrite_tool(self, temp_dir):
        """测试自动注册 TodoWriteTool"""
        config = Config(
            todowrite_enabled=True,
            todowrite_persistence_dir="todos"
        )

        registry = ToolRegistry()
        llm = HelloAgentsLLM()

        # 创建 Agent（应该自动注册 TodoWriteTool）
        agent = ReActAgent(
            name="test_agent",
            llm=llm,
            tool_registry=registry,
            config=config
        )

        # 验证工具已注册
        tool = registry.get_tool("TodoWrite")
        assert tool is not None
        assert isinstance(tool, TodoWriteTool)

    def test_todowrite_disabled(self):
        """测试禁用 TodoWrite"""
        config = Config(todowrite_enabled=False)

        registry = ToolRegistry()
        llm = HelloAgentsLLM()

        agent = ReActAgent(
            name="test_agent",
            llm=llm,
            tool_registry=registry,
            config=config
        )

        # 验证工具未注册
        tool = registry.get_tool("TodoWrite")
        assert tool is None

