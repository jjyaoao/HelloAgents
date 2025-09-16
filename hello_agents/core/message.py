"""消息系统"""

from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
import operator

class Message:
    """消息基类"""
    
    def __init__(self, content: str, role: str = "user"):
        self.content = content
        self.role = role
    
    def __str__(self):
        return f"{self.role}: {self.content}"

class BaseAgentState(TypedDict):
    """
    定义了所有Agent共享的基础状态结构。
    在构建具体Agent时，你的自定义State应该包含此结构或直接继承它。
    """
    # `messages` 字段用于存储整个对话历史。
    # `Annotated[..., operator.add]` 是一个关键的LangGraph语法：
    # 它告诉图，当节点返回'messages'时，应将新消息追加(add)到现有列表中，
    # operator.add 使得messages列表在图的流转中是追加(add)而不是覆盖(overwrite)
    messages: Annotated[List[BaseMessage], operator.add]