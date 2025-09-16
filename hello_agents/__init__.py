"""
HelloAgents - 灵活、可扩展的多智能体框架

这是一个基于Python的多智能体框架，旨在帮助开发者快速构建、测试和部署
基于大型语言模型（LLM）的智能体应用。
"""

from .version import __version__

# 核心导出，用户友好的API
from .core.agent import Agent
from .core.llm import HelloAgentsLLM
from .core.message import Message
from .core.config import Config

# 常用Agent类型
from .agents.simple import SimpleAgent
from .agents.tool_agent import ToolAgent
from .agents.conversational import ConversationalAgent

# 工具系统
from .tools.base import Tool
from .tools.registry import ToolRegistry

# 记忆系统
from .memory.working import WorkingMemory
from .memory.vector import VectorMemory

# 编排系统
from .orchestration.sequential import SequentialOrchestrator
from .orchestration.parallel import ParallelOrchestrator

__all__ = [
    "__version__",
    # 核心组件
    "Agent", "HelloAgentsLLM", "Message", "Config",
    # Agent类型
    "SimpleAgent", "ToolAgent", "ConversationalAgent", 
    # 工具系统
    "Tool", "ToolRegistry",
    # 记忆系统
    "WorkingMemory", "VectorMemory",
    # 编排系统
    "SequentialOrchestrator", "ParallelOrchestrator"
]