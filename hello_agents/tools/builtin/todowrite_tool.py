"""TodoWrite 进度管理工具

提供任务列表管理能力，强制单线程专注，避免任务切换。

特性：
- 声明式覆盖（每次提交完整列表）
- 单线程强制（最多 1 个 in_progress）
- 自动 Recap 生成
- 持久化到 memory/todos/

使用示例：
```python
from hello_agents import ToolRegistry
from hello_agents.tools.builtin import TodoWriteTool

registry = ToolRegistry()
registry.register_tool(TodoWriteTool(project_root="./"))
```
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import json
import os

from ..base import Tool, ToolParameter
from ..response import ToolResponse
from ..errors import ToolErrorCode


@dataclass
class TodoItem:
    """待办事项"""
    content: str  # 任务内容
    status: str  # "pending" | "in_progress" | "completed"
    created_at: str  # 创建时间
    updated_at: str = ""  # 更新时间

    def __post_init__(self):
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class TodoList:
    """待办列表"""
    summary: str  # 总体摘要
    todos: List[TodoItem] = field(default_factory=list)

    def get_in_progress(self) -> Optional[TodoItem]:
        """获取当前进行的任务"""
        for todo in self.todos:
            if todo.status == "in_progress":
                return todo
        return None

    def get_pending(self, limit: int = 5) -> List[TodoItem]:
        """获取待处理任务"""
        return [
            todo for todo in self.todos
            if todo.status == "pending"
        ][:limit]

    def get_completed(self) -> List[TodoItem]:
        """获取已完成任务"""
        return [
            todo for todo in self.todos
            if todo.status == "completed"
        ]

    def get_stats(self) -> dict:
        """获取统计信息"""
        total = len(self.todos)
        completed = sum(1 for t in self.todos if t.status == "completed")
        in_progress = sum(1 for t in self.todos if t.status == "in_progress")
        pending = total - completed - in_progress

        return {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending
        }


class TodoWriteTool(Tool):
    """待办事项工具
    
    特性：
    - 声明式覆盖（每次提交完整列表）
    - 单线程强制（最多 1 个 in_progress）
    - 自动 Recap 生成
    - 持久化到文件
    """

    def __init__(
        self,
        project_root: str = ".",
        persistence_dir: str = "memory/todos"
    ):
        """初始化 TodoWriteTool
        
        Args:
            project_root: 项目根目录
            persistence_dir: 持久化目录（相对于 project_root）
        """
        super().__init__(
            name="TodoWrite",
            description="""管理任务列表，保持单线程专注。

特性：
- 每次提交完整列表（声明式）
- 最多 1 个任务标记为 in_progress
- 自动生成 Recap 保持上下文精简
- 自动保存到 memory/todos/

使用场景：
- 开始复杂任务时创建任务列表
- 跟踪进度，避免遗漏
- 多轮对话中保持状态

参数：
- summary: 总体任务描述（可选）
- todos: 待办事项列表（JSON 数组）
- action: 操作类型（create/update/clear，默认 create）""",
            expandable=False
        )
        self.project_root = Path(project_root)
        self.persistence_dir = self.project_root / persistence_dir
        
        # 确保目录存在
        self.persistence_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前 Todo 列表
        self.current_todos = TodoList(summary="")

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="summary",
                type="string",
                description="总体任务描述（简短，1-2 句话）",
                required=False,
                default=""
            ),
            ToolParameter(
                name="todos",
                type="array",
                description="""待办事项列表（JSON 数组）

格式：[
  {"content": "任务1", "status": "pending"},
  {"content": "任务2", "status": "in_progress"},
  {"content": "任务3", "status": "completed"}
]

规则：
- status 只能是：pending, in_progress, completed
- 最多 1 个任务可以标记为 in_progress
- 每次提交完整列表（声明式）""",
                required=False,
                default=[],
                items={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "任务内容"
                        },
                        "status": {
                            "type": "string",
                            "description": "任务状态",
                            "enum": ["pending", "in_progress", "completed"]
                        },
                        "created_at": {
                            "type": "string",
                            "description": "创建时间（ISO 8601，可选）"
                        },
                        "updated_at": {
                            "type": "string",
                            "description": "更新时间（ISO 8601，可选）"
                        }
                    },
                    "required": ["content", "status"]
                }
            ),
            ToolParameter(
                name="action",
                type="string",
                description="操作类型：create|update|clear（默认 create）",
                required=False,
                default="create",
                enum=["create", "update", "clear"]
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行工具

        Args:
            parameters: 工具参数
                - summary: 总体描述
                - todos: 待办列表
                - action: 操作类型

        Returns:
            ToolResponse: 标准化响应
        """
        action = parameters.get("action", "create")

        try:
            if action == "clear":
                # 清空任务列表
                self.current_todos = TodoList(summary="")
                recap = "✅ 任务列表已清空"

                return ToolResponse.success(
                    text=recap,
                    data={
                        "action": action,
                        "summary": "",
                        "stats": {"total": 0, "completed": 0, "in_progress": 0, "pending": 0}
                    }
                )

            # 获取 todos 参数
            todos_data = parameters.get("todos", [])

            # 如果是字符串，尝试解析为 JSON
            if isinstance(todos_data, str):
                try:
                    todos_data = json.loads(todos_data)
                except json.JSONDecodeError as e:
                    return ToolResponse.error(
                        code=ToolErrorCode.INVALID_PARAM,
                        message=f"todos JSON 格式错误：{str(e)}"
                    )

            # 验证约束
            validation = self._validate_todos(todos_data)
            if not validation["valid"]:
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message=validation["message"]
                )

            # 创建 TodoItem 对象
            now = datetime.now().isoformat()
            todos = [
                TodoItem(
                    content=item["content"],
                    status=item["status"],
                    created_at=item.get("created_at", now),
                    updated_at=now
                )
                for item in todos_data
            ]

            # 创建 TodoList
            summary = parameters.get("summary", "")
            self.current_todos = TodoList(summary=summary, todos=todos)

            # 生成 Recap
            recap = self._generate_recap()

            # 持久化
            self._persist_todos()

            return ToolResponse.success(
                text=recap,
                data={
                    "action": action,
                    "summary": self.current_todos.summary,
                    "stats": self.current_todos.get_stats()
                }
            )

        except Exception as e:
            return ToolResponse.error(
                code=ToolErrorCode.INTERNAL_ERROR,
                message=f"处理任务列表失败：{str(e)}"
            )

    def _validate_todos(self, todos_data: list) -> dict:
        """验证 todos 约束

        Returns:
            {"valid": bool, "message": str}
        """
        if not isinstance(todos_data, list):
            return {
                "valid": False,
                "message": "todos 必须是数组"
            }

        in_progress_count = sum(1 for t in todos_data if t.get("status") == "in_progress")

        if in_progress_count > 1:
            return {
                "valid": False,
                "message": f"最多只能有 1 个 in_progress 任务，当前有 {in_progress_count} 个"
            }

        for i, todo in enumerate(todos_data):
            if not isinstance(todo, dict):
                return {
                    "valid": False,
                    "message": f"第 {i+1} 个任务必须是对象"
                }

            content = todo.get("content", "")
            status = todo.get("status", "")

            if not content.strip():
                return {
                    "valid": False,
                    "message": f"第 {i+1} 个任务的 content 不能为空"
                }

            if status not in ["pending", "in_progress", "completed"]:
                return {
                    "valid": False,
                    "message": f"第 {i+1} 个任务的 status 必须是 pending/in_progress/completed"
                }

        return {"valid": True, "message": ""}

    def _generate_recap(self) -> str:
        """生成 Recap 文本

        格式：[2/5] In progress: xxx. Pending: yyy; zzz.
        """
        stats = self.current_todos.get_stats()

        if stats['total'] == 0:
            return "📋 [0/0] 无活动任务"

        recap_parts = [f"📋 [{stats['completed']}/{stats['total']}]"]

        in_progress = self.current_todos.get_in_progress()
        if in_progress:
            recap_parts.append(f"进行中: {in_progress.content}")

        pending = self.current_todos.get_pending(limit=3)
        if pending:
            pending_texts = [t.content for t in pending]
            recap_parts.append(f"待处理: {'; '.join(pending_texts)}")

        if stats['pending'] > 3:
            recap_parts.append(f"还有 {stats['pending'] - 3} 个...")

        if stats['completed'] == stats['total'] and stats['total'] > 0:
            return f"✅ [{stats['completed']}/{stats['total']}] 所有任务已完成！"

        return ". ".join(recap_parts)

    def _persist_todos(self):
        """持久化到文件（原子写入）"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"todoList-{timestamp}.json"
        filepath = self.persistence_dir / filename

        # 创建可序列化的数据
        data = {
            "summary": self.current_todos.summary,
            "todos": [
                {
                    "content": t.content,
                    "status": t.status,
                    "created_at": t.created_at,
                    "updated_at": t.updated_at
                }
                for t in self.current_todos.todos
            ],
            "created_at": datetime.now().isoformat(),
            "stats": self.current_todos.get_stats()
        }

        # 原子写入
        temp_path = filepath.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        temp_path.replace(filepath)

    def load_todos(self, filepath: str):
        """从文件加载任务列表

        Args:
            filepath: 任务列表文件路径
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        todos = [
            TodoItem(
                content=t["content"],
                status=t["status"],
                created_at=t["created_at"],
                updated_at=t.get("updated_at", t["created_at"])
            )
            for t in data["todos"]
        ]

        self.current_todos = TodoList(
            summary=data.get("summary", ""),
            todos=todos
        )
