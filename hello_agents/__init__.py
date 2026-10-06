"""
HelloAgents - 灵活、可扩展的多智能体框架

基于OpenAI原生API构建，提供简洁高效的智能体开发体验。
"""

import logging
from ._python_version import show_recommendation as _show_recommendation

_show_recommendation()
logging.getLogger(__name__).addHandler(logging.NullHandler())

from .version import __version__, __author__, __email__, __description__

# 核心组件
from .core.llm import HelloAgentsLLM
from .core.config import Config
from .core.message import Message
from .core.exceptions import HelloAgentsException

# Agent实现
from .agents.simple_agent import SimpleAgent
from .agents.react_agent import ReActAgent
from .agents.reflection_agent import ReflectionAgent
from .agents.plan_solve_agent import PlanSolveAgent

# 工具系统
from .tools.registry import ToolRegistry, global_registry
from .tools.builtin.calculator import CalculatorTool, calculate

from .core.components import AgentComponents, DEFAULT_COMPONENT

__all__ = [
    "AgentComponents",
    "DEFAULT_COMPONENT",
    # 版本信息
    "__version__",
    "__author__",
    "__email__",
    "__description__",

    # 核心组件
    "HelloAgentsLLM",
    "Config",
    "Message",
    "HelloAgentsException",

    # Agent范式
    "SimpleAgent",
    "ReActAgent",
    "ReflectionAgent",
    "PlanSolveAgent",

    # 工具系统
    "ToolRegistry",
    "global_registry",
    "CalculatorTool",
    "calculate",
]

from .core.budget import RunBudget, BudgetExceeded
__all__ += ["RunBudget", "BudgetExceeded"]
