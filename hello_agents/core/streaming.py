"""流式输出支持 - SSE (Server-Sent Events) 实现"""

from typing import AsyncIterator, Dict, Any, Optional
from dataclasses import dataclass, asdict
import json
import time
from enum import Enum


class StreamEventType(Enum):
    """流式事件类型"""
    AGENT_START = "agent_start"
    AGENT_FINISH = "agent_finish"
    STEP_START = "step_start"
    STEP_FINISH = "step_finish"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_FINISH = "tool_call_finish"
    LLM_CHUNK = "llm_chunk"  # LLM 流式输出的文本块
    THINKING = "thinking"  # Agent 思考过程
    ERROR = "error"


@dataclass
class StreamEvent:
    """流式事件"""
    type: StreamEventType
    timestamp: float
    agent_name: str
    data: Dict[str, Any]
    
    @classmethod
    def create(cls, event_type: StreamEventType, agent_name: str, **data) -> 'StreamEvent':
        """创建事件"""
        return cls(
            type=event_type,
            timestamp=time.time(),
            agent_name=agent_name,
            data=data
        )
    
    def to_sse(self) -> str:
        """转换为 SSE 格式
        
        SSE 格式：
        event: <event_type>
        data: <json_data>
        
        """
        event_dict = {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "data": self.data
        }
        
        # SSE 格式要求
        lines = [
            f"event: {self.type.value}",
            f"data: {json.dumps(event_dict, ensure_ascii=False)}",
            ""  # 空行表示事件结束
        ]
        return "\n".join(lines) + "\n"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "data": self.data
        }


class StreamBuffer:
    """流式输出缓冲区
    
    用于收集和管理流式事件，支持：
    - 事件缓冲
    - 背压控制
    - 事件过滤
    """
    
    def __init__(self, max_buffer_size: int = 100):
        self.max_buffer_size = max_buffer_size
        self.events: list[StreamEvent] = []
    
    def add(self, event: StreamEvent):
        """添加事件到缓冲区"""
        self.events.append(event)
        
        # 简单的背压控制：超过最大缓冲区大小时丢弃旧事件
        if len(self.events) > self.max_buffer_size:
            self.events.pop(0)
    
    def get_all(self) -> list[StreamEvent]:
        """获取所有事件"""
        return self.events.copy()
    
    def clear(self):
        """清空缓冲区"""
        self.events.clear()
    
    def filter_by_type(self, event_type: StreamEventType) -> list[StreamEvent]:
        """按类型过滤事件"""
        return [e for e in self.events if e.type == event_type]


async def stream_to_sse(
    event_stream: AsyncIterator[StreamEvent],
    include_types: Optional[list[StreamEventType]] = None
) -> AsyncIterator[str]:
    """将事件流转换为 SSE 格式
    
    Args:
        event_stream: 事件流
        include_types: 包含的事件类型（None 表示全部）
    
    Yields:
        SSE 格式的字符串
    """
    async for event in event_stream:
        # 过滤事件类型
        if include_types and event.type not in include_types:
            continue
        
        # 转换为 SSE 格式
        yield event.to_sse()


async def stream_to_json(
    event_stream: AsyncIterator[StreamEvent],
    include_types: Optional[list[StreamEventType]] = None
) -> AsyncIterator[str]:
    """将事件流转换为 JSON Lines 格式
    
    Args:
        event_stream: 事件流
        include_types: 包含的事件类型（None 表示全部）
    
    Yields:
        JSON 字符串（每行一个事件）
    """
    async for event in event_stream:
        # 过滤事件类型
        if include_types and event.type not in include_types:
            continue
        
        # 转换为 JSON
        yield json.dumps(event.to_dict(), ensure_ascii=False) + "\n"

