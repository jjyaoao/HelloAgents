"""Agent实现模块 - HelloAgents原生Agent范式"""

from .simple_agent import SimpleAgent
from .react_agent import ReActAgent
from .reflection_agent import ReflectionAgent
from .plan_solve_agent import PlanSolveAgent

# 子代理机制（第06章）
from .factory import create_agent, default_subagent_factory

# 向后兼容别名
PlanAndSolveAgent = PlanSolveAgent

__all__ = [
    "SimpleAgent",
    "ReActAgent",
    "ReflectionAgent",
    "PlanSolveAgent",
    "PlanAndSolveAgent",  # 向后兼容

    # 子代理工厂函数
    "create_agent",
    "default_subagent_factory",
]
