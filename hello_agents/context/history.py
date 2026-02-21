"""HistoryManager - 历史消息管理器

职责：
- 消息追加（只追加，不编辑，缓存友好）
- 历史压缩（生成 summary + 保留最近轮次）
- 会话序列化/反序列化
- 轮次边界检测
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from ..core.message import Message


class HistoryManager:
    """历史管理器
    
    特性：
    - 只追加，不编辑（缓存友好）
    - 自动压缩历史（summary + 保留最近轮次）
    - 支持会话保存/加载
    
    用法示例：
    ```python
    manager = HistoryManager(min_retain_rounds=10)
    
    # 追加消息
    manager.append(Message("hello", "user"))
    manager.append(Message("hi", "assistant"))
    
    # 获取历史
    history = manager.get_history()
    
    # 压缩历史
    manager.compress("这是前面对话的摘要")
    
    # 序列化
    data = manager.to_dict()
    
    # 反序列化
    manager.load_from_dict(data)
    ```
    """
    
    def __init__(
        self,
        min_retain_rounds: int = 10,
        compression_threshold: float = 0.8
    ):
        """初始化历史管理器
        
        Args:
            min_retain_rounds: 压缩时保留的最小完整轮次数
            compression_threshold: 压缩阈值（暂未使用，预留）
        """
        self._history: List[Message] = []
        self.min_retain_rounds = min_retain_rounds
        self.compression_threshold = compression_threshold
    
    def append(self, message: Message) -> None:
        """追加消息（只追加，不编辑）
        
        Args:
            message: 要追加的消息
        """
        self._history.append(message)
    
    def get_history(self) -> List[Message]:
        """获取历史副本
        
        Returns:
            历史消息列表的副本
        """
        return self._history.copy()
    
    def clear(self) -> None:
        """清空历史"""
        self._history.clear()
    
    def estimate_rounds(self) -> int:
        """预估完整轮次数
        
        一轮定义：1 user 消息 + N 条 assistant/tool/summary 消息
        
        Returns:
            完整轮次数
        """
        rounds = 0
        i = 0
        while i < len(self._history):
            if self._history[i].role == "user":
                rounds += 1
                # 跳过这一轮的后续消息
                i += 1
                while i < len(self._history) and self._history[i].role != "user":
                    i += 1
            else:
                i += 1
        return rounds
    
    def find_round_boundaries(self) -> List[int]:
        """查找每轮的起始索引
        
        Returns:
            每轮起始索引列表，例如 [0, 3, 7, 10]
        """
        boundaries = []
        for i, msg in enumerate(self._history):
            if msg.role == "user":
                boundaries.append(i)
        return boundaries
    
    def compress(self, summary: str) -> None:
        """压缩历史
        
        将旧历史替换为 summary 消息，保留最近 N 轮完整对话
        
        Args:
            summary: 历史摘要文本
        """
        # 检查是否有足够的轮次需要压缩
        rounds = self.estimate_rounds()
        if rounds <= self.min_retain_rounds:
            return
        
        # 找到所有轮次边界
        boundaries = self.find_round_boundaries()
        
        # 计算要保留的起始位置（保留最近 min_retain_rounds 轮）
        if len(boundaries) > self.min_retain_rounds:
            keep_from_index = boundaries[-self.min_retain_rounds]
        else:
            # 不足最小轮次，不压缩
            return
        
        # 生成 summary 消息
        summary_msg = Message(
            content=f"## Archived Session Summary\n{summary}",
            role="summary",
            metadata={"compressed_at": datetime.now().isoformat()}
        )
        
        # 替换历史：summary + 保留的最近轮次
        self._history = [summary_msg] + self._history[keep_from_index:]
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（用于会话保存）
        
        Returns:
            包含历史和元数据的字典
        """
        return {
            "history": [msg.to_dict() for msg in self._history],
            "created_at": datetime.now().isoformat(),
            "rounds": self.estimate_rounds()
        }
    
    def load_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典加载（用于会话恢复）
        
        Args:
            data: 序列化的历史数据
        """
        self._history = [
            Message.from_dict(msg_data)
            for msg_data in data.get("history", [])
        ]

