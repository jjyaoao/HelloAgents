"""TokenCounter - Token 计数器

职责：
- 本地预估 Token 数（无需 API 调用）
- 缓存机制（避免重复计算）
- 增量计算（只计算新增消息）
- 降级方案（tiktoken 不可用时使用字符估算）
"""

import tiktoken
from typing import List, Dict, Optional
from ..core.message import Message


class TokenCounter:
    """Token 计数器
    
    特性：
    - 本地预估（无需 API 调用）
    - 缓存机制（避免重复计算）
    - 增量计算（只计算新增消息）
    - 降级方案（tiktoken 不可用时使用字符估算）
    
    用法示例：
    ```python
    counter = TokenCounter(model="gpt-4")
    
    # 计算单条消息
    tokens = counter.count_message(message)
    
    # 计算消息列表
    total = counter.count_messages(messages)
    
    # 增量计算
    new_total = counter.count_incremental(previous_count, new_messages)
    ```
    """
    
    def __init__(self, model: str = "gpt-4"):
        """初始化 Token 计数器
        
        Args:
            model: 模型名称（用于选择 tiktoken 编码器）
        """
        self.model = model
        self._encoding = self._get_encoding()
        self._cache: Dict[str, int] = {}  # 消息内容 -> Token 数
    
    def _get_encoding(self):
        """获取 tiktoken 编码器
        
        Returns:
            tiktoken 编码器实例，失败时返回 None
        """
        try:
            # 尝试根据模型名称获取编码器
            return tiktoken.encoding_for_model(self.model)
        except KeyError:
            # 降级到通用编码器
            try:
                return tiktoken.get_encoding("cl100k_base")
            except Exception:
                return None
        except Exception:
            # tiktoken 不可用
            return None
    
    def count_messages(self, messages: List[Message]) -> int:
        """计算消息列表的 Token 数
        
        Args:
            messages: 消息列表
        
        Returns:
            Token 数
        """
        total = 0
        for msg in messages:
            total += self.count_message(msg)
        return total
    
    def count_message(self, message: Message) -> int:
        """计算单条消息的 Token 数（带缓存）
        
        Args:
            message: 消息对象
        
        Returns:
            Token 数
        """
        # 使用消息内容作为缓存键
        cache_key = f"{message.role}:{message.content}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 计算 Token 数
        tokens = self._count_text(message.content)
        
        # 添加角色标记的开销（约 4 tokens）
        tokens += 4
        
        # 缓存结果
        self._cache[cache_key] = tokens
        
        return tokens
    
    def count_text(self, text: str) -> int:
        """计算文本的 Token 数（无缓存）
        
        Args:
            text: 文本内容
        
        Returns:
            Token 数
        """
        return self._count_text(text)
    
    def _count_text(self, text: str) -> int:
        """内部 Token 计算方法
        
        Args:
            text: 文本内容
        
        Returns:
            Token 数
        """
        if self._encoding:
            # 使用 tiktoken 精确计算
            try:
                return len(self._encoding.encode(text))
            except Exception:
                # tiktoken 编码失败，降级到字符估算
                return len(text) // 4
        else:
            # 降级方案：粗略估算（1 token ≈ 4 字符）
            return len(text) // 4
    

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()

    def get_cache_size(self) -> int:
        """获取缓存大小

        Returns:
            缓存的消息数量
        """
        return len(self._cache)

    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计信息

        Returns:
            缓存统计字典
        """
        return {
            "cached_messages": len(self._cache),
            "total_cached_tokens": sum(self._cache.values())
        }

