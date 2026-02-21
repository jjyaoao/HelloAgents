"""消息系统"""

from typing import Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel

MessageRole = Literal["user", "assistant", "system", "tool", "summary"]

class Message(BaseModel):
    """消息类"""

    content: str
    role: MessageRole
    timestamp: datetime = None
    metadata: Optional[Dict[str, Any]] = None

    def __init__(self, content: str, role: MessageRole, **kwargs):
        super().__init__(
            content=content,
            role=role,
            timestamp=kwargs.get('timestamp', datetime.now()),
            metadata=kwargs.get('metadata', {})
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（OpenAI API格式）"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建消息对象"""
        timestamp = data.get("timestamp")
        if timestamp and isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return cls(
            content=data["content"],
            role=data["role"],
            timestamp=timestamp,
            metadata=data.get("metadata")
        )

    def to_text(self) -> str:
        """格式化为文本（用于上下文构建）"""
        return f"[{self.role}] {self.content}"

    def __str__(self) -> str:
        return f"[{self.role}] {self.content}"
