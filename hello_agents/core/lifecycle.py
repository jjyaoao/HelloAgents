"""Agent 异步生命周期事件系统

提供事件驱动的 Agent 执行流程，支持：
- 生命周期钩子（on_start, on_step, on_finish, on_error）
- 流式事件输出（SSE/WebSocket 场景）
- 异步执行与并行优化
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable, Awaitable
from enum import Enum
import time


class EventType(Enum):
    """Agent 生命周期事件类型"""
    
    # Agent 级别事件
    AGENT_START = "agent_start"           # Agent 开始执行
    AGENT_FINISH = "agent_finish"         # Agent 执行完成
    AGENT_ERROR = "agent_error"           # Agent 执行错误
    
    # 步骤级别事件
    STEP_START = "step_start"             # 推理步骤开始
    STEP_FINISH = "step_finish"           # 推理步骤完成
    
    # LLM 调用事件
    LLM_START = "llm_start"               # LLM 调用开始
    LLM_CHUNK = "llm_chunk"               # LLM 流式输出片段
    LLM_FINISH = "llm_finish"             # LLM 调用完成
    
    # 工具调用事件
    TOOL_CALL = "tool_call"               # 工具调用开始
    TOOL_RESULT = "tool_result"           # 工具调用结果
    TOOL_ERROR = "tool_error"             # 工具调用错误
    
    # 特殊事件
    THINKING = "thinking"                 # 推理过程（o1/deepseek-reasoner）
    REFLECTION = "reflection"             # 反思过程
    PLAN = "plan"                         # 计划生成


@dataclass
class AgentEvent:
    """Agent 生命周期事件
    
    所有事件的基础数据结构，包含：
    - type: 事件类型
    - timestamp: 时间戳
    - agent_name: Agent 名称
    - data: 事件数据（灵活扩展）
    """
    
    type: EventType
    timestamp: float
    agent_name: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        event_type: EventType,
        agent_name: str,
        **data
    ) -> 'AgentEvent':
        """创建事件的便捷方法
        
        Args:
            event_type: 事件类型
            agent_name: Agent 名称
            **data: 事件数据（键值对）
            
        Returns:
            AgentEvent 实例
            
        Example:
            >>> event = AgentEvent.create(
            ...     EventType.TOOL_CALL,
            ...     "my_agent",
            ...     tool_name="search",
            ...     tool_args={"query": "hello"}
            ... )
        """
        return cls(
            type=event_type,
            timestamp=time.time(),
            agent_name=agent_name,
            data=data
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）
        
        Returns:
            字典表示
        """
        return {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "data": self.data
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"[{self.type.value}] {self.agent_name} @ {self.timestamp:.2f}: {self.data}"


# 类型别名：生命周期钩子
LifecycleHook = Optional[Callable[[AgentEvent], Awaitable[None]]]


@dataclass
class ExecutionContext:
    """Agent 执行上下文
    
    在异步执行过程中传递的上下文信息，包含：
    - 输入文本
    - 当前步骤
    - 累计 token 数
    - 自定义元数据
    """
    
    input_text: str
    current_step: int = 0
    total_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def increment_step(self):
        """步骤计数器 +1"""
        self.current_step += 1
    
    def add_tokens(self, tokens: int):
        """累加 token 数"""
        self.total_tokens += tokens
    
    def set_metadata(self, key: str, value: Any):
        """设置元数据"""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self.metadata.get(key, default)

