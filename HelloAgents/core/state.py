# core/state.py

from typing import TypedDict, Annotated, List
from langchain_core.messages import BaseMessage
import operator

# 可以定义 Agent 状态结构，当前仅简单包含对话消息列表。
# 你可以根据需要扩展这个状态结构，添加更多字段，如工具响应状态、中间计算结果等。
class BaseAgentState(TypedDict):
    """
    定义了所有 Agent 共享的基础状态结构。
    在构建具体 Agent 时，你的自定义 State 应该包含此结构或直接继承它。
    """
    # `messages` 字段用于存储整个对话历史。
    # `Annotated[..., operator.add]` 是一个关键的 LangGraph 语法：
    # 它告诉图，当节点返回 'messages' 时，应将新消息追加(add)到现有列表中，
    # operator.add 使得 messages 列表在图的流转中是追加(add)而不是覆盖(overwrite)
    messages: Annotated[List[BaseMessage], operator.add]