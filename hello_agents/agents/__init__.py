"""Agent实现模块 - HelloAgents原生Agent范式"""

from .simple_agent import SimpleAgent
from .react_agent import ReActAgent
from .reflection_agent import ReflectionAgent
from .plan_solve_agent import PlanAndSolveAgent

# 保持向后兼容性
try:
    from .tool_agent import ToolAgent
    from .conversational import ConversationalAgent
    __all__ = [
        "SimpleAgent",
        "ReActAgent",
        "ReflectionAgent",
        "PlanAndSolveAgent",
        "ToolAgent",
        "ConversationalAgent"
    ]
except ImportError:
    __all__ = [
        "SimpleAgent",
        "ReActAgent",
        "ReflectionAgent",
        "PlanAndSolveAgent"
    ]