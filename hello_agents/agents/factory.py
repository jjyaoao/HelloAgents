"""Agent 工厂函数

用于创建不同类型的 Agent 实例，支持子代理机制。
"""

from typing import Optional, TYPE_CHECKING
from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry


def create_agent(
    agent_type: str,
    name: str,
    llm: HelloAgentsLLM,
    tool_registry: Optional['ToolRegistry'] = None,
    config: Optional[Config] = None,
    system_prompt: Optional[str] = None
) -> Agent:
    """创建 Agent 实例
    
    Args:
        agent_type: Agent 类型，支持：
            - "react": ReActAgent（推理-行动循环）
            - "reflection": ReflectionAgent（反思型）
            - "plan": PlanAndSolveAgent（规划-执行）
            - "simple": SimpleAgent（简单对话）
        name: Agent 名称
        llm: LLM 实例
        tool_registry: 工具注册表（可选）
        config: 配置对象（可选）
        system_prompt: 系统提示词（可选）
        
    Returns:
        Agent 实例
        
    Raises:
        ValueError: 不支持的 agent_type
    """
    agent_type = agent_type.lower()
    
    if agent_type == "react":
        from .react_agent import ReActAgent
        return ReActAgent(
            name=name,
            llm=llm,
            tool_registry=tool_registry,
            config=config,
            system_prompt=system_prompt
        )
    
    elif agent_type == "reflection":
        from .reflection_agent import ReflectionAgent
        return ReflectionAgent(
            name=name,
            llm=llm,
            tool_registry=tool_registry,
            config=config,
            system_prompt=system_prompt
        )
    
    elif agent_type == "plan":
        from .plan_solve_agent import PlanSolveAgent
        return PlanSolveAgent(
            name=name,
            llm=llm,
            tool_registry=tool_registry,
            config=config,
            system_prompt=system_prompt
        )
    
    elif agent_type == "simple":
        from .simple_agent import SimpleAgent
        return SimpleAgent(
            name=name,
            llm=llm,
            config=config,
            system_prompt=system_prompt
        )
    
    else:
        raise ValueError(
            f"不支持的 agent_type: {agent_type}。"
            f"支持的类型: react, reflection, plan, simple"
        )


def default_subagent_factory(
    agent_type: str,
    llm: HelloAgentsLLM,
    tool_registry: Optional['ToolRegistry'] = None,
    config: Optional[Config] = None
) -> Agent:
    """默认子代理工厂函数
    
    框架提供的默认实现，用户可以自定义替换。
    
    Args:
        agent_type: Agent 类型
        llm: LLM 实例
        tool_registry: 工具注册表（可选）
        config: 配置对象（可选）
        
    Returns:
        配置好的子代理实例
    """
    config = config or Config()
    
    # 子代理名称
    name = f"subagent-{agent_type}"
    
    # 根据类型选择系统提示词
    system_prompt = _get_system_prompt_for_type(agent_type)
    
    # 创建子代理
    subagent = create_agent(
        agent_type=agent_type,
        name=name,
        llm=llm,
        tool_registry=tool_registry,
        config=config,
        system_prompt=system_prompt
    )
    
    # 配置子代理特定参数
    if hasattr(subagent, 'max_steps'):
        subagent.max_steps = config.subagent_max_steps
    
    return subagent


def _get_system_prompt_for_type(agent_type: str) -> str:
    """获取类型特定的系统提示词
    
    Args:
        agent_type: Agent 类型
        
    Returns:
        系统提示词
    """
    prompts = {
        "react": """你是一个高效的任务执行专家。

目标：快速完成指定的子任务。

规则：
- 使用可用工具高效完成任务
- 保持输出简洁明了
- 在规定步数内完成
""",
        "reflection": """你是一个反思型专家。

目标：深入分析问题并提供高质量的解决方案。

规则：
- 先给出初步方案
- 反思并改进方案
- 输出最终优化结果
""",
        "plan": """你是一个任务规划专家。

目标：将复杂任务分解为可执行的步骤。

规则：
- 分析任务需求
- 制定详细的执行计划
- 标注步骤依赖关系
""",
        "simple": """你是一个简洁高效的助手。

目标：直接回答问题或完成任务。

规则：
- 保持回答简洁
- 直接给出结果
- 避免冗余信息
"""
    }
    
    return prompts.get(agent_type.lower(), prompts["simple"])

