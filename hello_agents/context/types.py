"""上下文组件的共享数据契约，与存储和 Agent 实现无关。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
from .text import count_tokens


@dataclass
class ContextPacket:
    """上下文信息包"""

    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    relevance_score: float = 0.0  # 0.0-1.0

    def __post_init__(self):
        """自动计算token数"""
        if self.token_count == 0:
            self.token_count = count_tokens(self.content)


@dataclass
class ContextBuildResult:
    messages: List[Dict[str, Any]]
    diagnostics: Dict[str, Any]


class ContextBudgetExceeded(ValueError):
    """受保护消息超预算；diagnostics 提供估计与选择信息。"""

    def __init__(self, message: str, diagnostics: Dict[str, Any]):
        super().__init__(message)
        self.diagnostics = diagnostics
