"""上下文工程模块

为HelloAgents框架提供上下文工程能力：
- ContextBuilder: GSSC流水线（Gather-Select-Structure-Compress）
- Compactor: 对话压缩整合
- NotesManager: 结构化笔记管理
- ContextObserver: 可观测性与指标追踪
"""

from .builder import ContextBuilder, ContextConfig, ContextPacket

__all__ = [
    "ContextBuilder",
    "ContextConfig",
    "ContextPacket",
]

