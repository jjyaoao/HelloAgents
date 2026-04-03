"""DevLogTool - 开发日志工具

记录 Agent 的开发决策、问题、解决方案等关键信息。

特性：
- 结构化日志（category + content + metadata）
- 持久化到 memory/devlogs/
- 支持过滤查询（按类别、标签）
- 自动生成摘要
- 基于 ToolResponse 协议
"""

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode


# 支持的日志类别
CATEGORIES = {
    "decision": "架构/技术选型决策",
    "progress": "阶段性进展记录",
    "issue": "遇到的问题",
    "solution": "问题解决方案",
    "refactor": "重构决策",
    "test": "测试相关记录",
    "performance": "性能优化记录"
}

# session_id 允许的字符：字母、数字、连字符、下划线、点号
_SAFE_SESSION_ID_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')


@dataclass
class DevLogEntry:
    """单条开发日志"""
    id: str
    timestamp: str
    category: str
    content: str
    metadata: Dict[str, Any]

    @classmethod
    def create(
        cls,
        category: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'DevLogEntry':
        """创建新的日志条目"""
        return cls(
            id=f"log-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now().isoformat(),
            category=category,
            content=content,
            metadata=metadata or {}
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DevLogEntry':
        """从字典创建"""
        return cls(**data)


@dataclass
class DevLogStore:
    """开发日志存储引擎"""
    session_id: str
    agent_name: str
    created_at: str
    updated_at: str
    entries: List[DevLogEntry]

    @classmethod
    def create(cls, session_id: str, agent_name: str) -> 'DevLogStore':
        """创建新的日志存储"""
        now = datetime.now().isoformat()
        return cls(
            session_id=session_id,
            agent_name=agent_name,
            created_at=now,
            updated_at=now,
            entries=[]
        )

    def append(self, entry: DevLogEntry):
        """追加日志条目"""
        self.entries.append(entry)
        self.updated_at = datetime.now().isoformat()

    def filter_entries(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[DevLogEntry]:
        """过滤日志条目"""
        filtered = self.entries

        # 按类别过滤
        if category:
            filtered = [e for e in filtered if e.category == category]

        # 按标签过滤
        if tags:
            filtered = [
                e for e in filtered
                if any(tag in e.metadata.get("tags", []) for tag in tags)
            ]

        # 限制数量（返回最新的 N 条）
        if limit and limit > 0:
            filtered = filtered[-limit:]

        return filtered

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_entries": len(self.entries),
            "by_category": {}
        }

        for entry in self.entries:
            cat = entry.category
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

        return stats

    def generate_summary(self, limit: int = 10) -> str:
        """生成摘要"""
        if not self.entries:
            return "📝 暂无开发日志"

        stats = self.get_stats()
        total = stats["total_entries"]
        recent = self.entries[-limit:]

        summary_parts = [f"📝 共 {total} 条日志"]

        # 按类别统计
        cat_summary = ", ".join([
            f"{cat}({count})"
            for cat, count in stats["by_category"].items()
        ])
        summary_parts.append(f"分类: {cat_summary}")

        # 最近日志
        if recent:
            recent_summary = "; ".join([
                f"[{e.category}] {e.content[:30]}..."
                if len(e.content) > 30 else f"[{e.category}] {e.content}"
                for e in recent[-3:]  # 只显示最近 3 条
            ])
            summary_parts.append(f"最近: {recent_summary}")

        return ". ".join(summary_parts)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "entries": [e.to_dict() for e in self.entries],
            "stats": self.get_stats()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DevLogStore':
        """从字典创建"""
        entries = [DevLogEntry.from_dict(e) for e in data.get("entries", [])]
        return cls(
            session_id=data["session_id"],
            agent_name=data["agent_name"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            entries=entries
        )


class DevLogTool(Tool):
    """开发日志工具

    特性：
    - 记录开发决策、问题、解决方案
    - 支持多种类别（decision/progress/issue/solution/refactor/test/performance）
    - 持久化到 memory/devlogs/
    - 支持过滤查询和摘要生成

    使用场景：
    - 记录架构决策和技术选型理由
    - 记录遇到的问题和解决方案
    - 记录重构决策和性能优化
    - 跨会话知识积累

    操作：
    - append: 追加日志
    - read: 读取日志（支持过滤）
    - summary: 生成摘要
    - clear: 清空日志
    """

    @staticmethod
    def _validate_session_id(session_id: str) -> str:
        """验证 session_id 不包含路径遍历字符。

        只允许字母、数字、连字符、下划线和点号（不允许连续的点号 '..'）。
        这可以防止通过 session_id 构造恶意文件名导致任意路径读写。

        Args:
            session_id: 待验证的会话 ID

        Returns:
            经过验证的 session_id（原值）

        Raises:
            ValueError: 如果 session_id 包含不安全字符
        """
        if not session_id or not _SAFE_SESSION_ID_RE.match(session_id):
            raise ValueError(
                f"Invalid session_id: {session_id!r}. "
                "session_id may only contain alphanumeric characters, "
                "hyphens, underscores and dots."
            )
        if '..' in session_id:
            raise ValueError(
                f"Invalid session_id: {session_id!r}. "
                "session_id must not contain '..'."
            )
        return session_id

    def __init__(
        self,
        session_id: str,
        agent_name: str = "Agent",
        project_root: str = ".",
        persistence_dir: str = "memory/devlogs"
    ):
        """初始化 DevLogTool

        Args:
            session_id: 会话 ID
            agent_name: Agent 名称
            project_root: 项目根目录
            persistence_dir: 持久化目录（相对于 project_root）

        Raises:
            ValueError: 如果 session_id 包含不安全字符（路径遍历等）
        """
        super().__init__(
            name="DevLog",
            description=f"""记录开发过程中的关键决策和问题。

支持的类别：
{chr(10).join([f'- {k}: {v}' for k, v in CATEGORIES.items()])}

操作：
- append: 追加日志（需要 category, content, metadata）
- read: 读取日志（可选 category, tags, limit）
- summary: 生成摘要
- clear: 清空日志

示例：
{{
  "action": "append",
  "category": "decision",
  "content": "选择使用 Redis 作为缓存层",
  "metadata": {{"tags": ["architecture", "cache"]}}
}}""",
            expandable=False
        )
        self.session_id = self._validate_session_id(session_id)
        self.agent_name = agent_name
        self.project_root = Path(project_root)
        self.persistence_dir = self.project_root / persistence_dir

        # 确保目录存在
        self.persistence_dir.mkdir(parents=True, exist_ok=True)

        # 当前日志存储
        self.store = DevLogStore.create(session_id, agent_name)

        # 尝试加载已有日志
        self._load_if_exists()

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="操作类型：append（追加）、read（读取）、summary（摘要）、clear（清空）",
                required=True,
                enum=["append", "read", "summary", "clear"]
            ),
            ToolParameter(
                name="category",
                type="string",
                description=f"日志类别（append 时必填）：{', '.join(CATEGORIES.keys())}",
                required=False,
                enum=list(CATEGORIES.keys())
            ),
            ToolParameter(
                name="content",
                type="string",
                description="日志内容（append 时必填）",
                required=False
            ),
            ToolParameter(
                name="metadata",
                type="object",
                description="元数据（可选），如 {\"tags\": [\"cache\"], \"step\": 3, \"related_tool\": \"WriteTool\"}",
                required=False
            ),
            ToolParameter(
                name="filter",
                type="object",
                description="过滤条件（read 时可选），如 {\"category\": \"decision\", \"tags\": [\"architecture\"], \"limit\": 10}",
                required=False
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行操作"""
        try:
            action = parameters.get("action")

            if action == "append":
                return self._handle_append(parameters)
            elif action == "read":
                return self._handle_read(parameters)
            elif action == "summary":
                return self._handle_summary()
            elif action == "clear":
                return self._handle_clear()
            else:
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAMETERS,
                    message=f"未知操作：{action}"
                )

        except Exception as e:
            return ToolResponse.error(
                code=ToolErrorCode.INTERNAL_ERROR,
                message=f"DevLog 操作失败：{str(e)}"
            )

    def _handle_append(self, parameters: Dict[str, Any]) -> ToolResponse:
        """处理追加操作"""
        category = parameters.get("category")
        content = parameters.get("content")

        # 参数校验
        if not category:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="追加日志时必须指定 category"
            )

        if category not in CATEGORIES:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message=f"无效的类别：{category}，支持的类别：{', '.join(CATEGORIES.keys())}"
            )

        if not content:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="追加日志时必须指定 content"
            )

        # 创建日志条目
        metadata = parameters.get("metadata", {})
        entry = DevLogEntry.create(category, content, metadata)

        # 追加到存储
        self.store.append(entry)

        # 持久化
        self._persist()

        # 返回成功响应
        return ToolResponse.success(
            text=f"✅ 日志已记录 [{category}]: {content[:50]}{'...' if len(content) > 50 else ''}",
            data={
                "log_id": entry.id,
                "timestamp": entry.timestamp,
                "category": entry.category
            },
            stats=self.store.get_stats()
        )

    def _handle_read(self, parameters: Dict[str, Any]) -> ToolResponse:
        """处理读取操作"""
        filter_params = parameters.get("filter", {})

        category = filter_params.get("category")
        tags = filter_params.get("tags")
        limit = filter_params.get("limit")

        # 过滤日志
        entries = self.store.filter_entries(category, tags, limit)

        if not entries:
            return ToolResponse.success(
                text="📝 未找到匹配的日志",
                data={"entries": []},
                stats={"matched": 0}
            )

        # 格式化输出
        lines = [f"📝 找到 {len(entries)} 条日志：\n"]
        for entry in entries:
            lines.append(f"[{entry.category}] {entry.timestamp}")
            lines.append(f"  {entry.content}")
            if entry.metadata:
                lines.append(f"  元数据: {json.dumps(entry.metadata, ensure_ascii=False)}")
            lines.append("")

        return ToolResponse.success(
            text="\n".join(lines),
            data={"entries": [e.to_dict() for e in entries]},
            stats={"matched": len(entries)}
        )

    def _handle_summary(self) -> ToolResponse:
        """处理摘要操作"""
        summary = self.store.generate_summary()

        return ToolResponse.success(
            text=summary,
            data=self.store.get_stats()
        )

    def _handle_clear(self) -> ToolResponse:
        """处理清空操作"""
        old_count = len(self.store.entries)
        self.store.entries = []
        self.store.updated_at = datetime.now().isoformat()

        # 持久化
        self._persist()

        return ToolResponse.success(
            text=f"✅ 已清空 {old_count} 条日志",
            data={"cleared_count": old_count}
        )

    def _persist(self):
        """持久化到文件"""
        filename = f"devlog-{self.session_id}.json"
        filepath = self.persistence_dir / filename

        # 原子写入
        temp_path = filepath.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(self.store.to_dict(), f, indent=2, ensure_ascii=False)

        temp_path.replace(filepath)

    def _load_if_exists(self):
        """加载已有日志（如果存在）"""
        filename = f"devlog-{self.session_id}.json"
        filepath = self.persistence_dir / filename

        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.store = DevLogStore.from_dict(data)
            except Exception:
                # 加载失败，使用新的存储
                pass
