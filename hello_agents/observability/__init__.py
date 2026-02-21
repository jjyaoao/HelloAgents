"""可观测性模块

提供 TraceLogger 用于记录 Agent 执行轨迹：
- JSONL 格式：机器可读，支持流式分析
- HTML 格式：人类可读，可视化审计界面
"""

from .trace_logger import TraceLogger

__all__ = ["TraceLogger"]

