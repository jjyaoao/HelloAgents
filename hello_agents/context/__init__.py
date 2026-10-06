"""上下文工程模块

为HelloAgents框架提供上下文工程能力：
- ContextBuilder: 候选选择、消息组装与预算诊断
- HistoryManager: 历史管理与压缩
- ObservationTruncator: 工具输出截断
- TokenCounter: Token 计数器（缓存 + 增量计算）
- ContextProvider: 可替换的候选资料收集协议
- ContextBuildResult: 消息与本地预算诊断
"""

from .builder import ContextBuilder, ContextConfig, ContextPacket, ContextBuildResult, ContextBudgetExceeded
from .history import HistoryManager
from .truncator import ObservationTruncator
from .token_counter import TokenCounter
from .providers import ContextAssembler, ContextProvider, RetrievalContextProvider, MemoryContextProvider

__all__ = [
    "ContextAssembler",
    "ContextProvider",
    "RetrievalContextProvider",
    "MemoryContextProvider",
    "ContextBuilder",
    "ContextBuildResult",
    "ContextBudgetExceeded",
    "ContextConfig",
    "ContextPacket",
    "HistoryManager",
    "ObservationTruncator",
    "TokenCounter",
]

