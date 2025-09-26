"""记忆检索器

按照第8章架构设计的记忆检索器，提供：
- 多种检索策略（向量检索、关键词检索、混合检索）
- 智能排序和过滤
- 跨记忆类型检索
"""

from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from datetime import datetime
import re
import math

from ..base import MemoryItem, MemoryConfig

class RetrievalStrategy(ABC):
    """检索策略基类"""
    
    @abstractmethod
    def retrieve(
        self,
        query: str,
        memories: List[MemoryItem],
        limit: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """执行检索
        
        Args:
            query: 查询内容
            memories: 记忆列表
            limit: 返回数量限制
            **kwargs: 其他参数
            
        Returns:
            检索结果列表，包含记忆和相关性分数
        """
        pass

class KeywordRetrievalStrategy(RetrievalStrategy):
    """关键词检索策略"""
    
    def __init__(self):
        self.stopwords = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
            "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
            "自己", "这", "那", "什么", "可以", "这个", "那个", "怎么", "为什么", "哪里"
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取，实际应用中可以使用更复杂的NLP技术
        words = re.findall(r'\w+', text.lower())
        keywords = [word for word in words if word not in self.stopwords and len(word) > 1]
        return keywords
    
    def _calculate_keyword_score(self, query_keywords: List[str], content: str) -> float:
        """计算关键词匹配分数"""
        content_lower = content.lower()
        matches = 0
        
        for keyword in query_keywords:
            if keyword in content_lower:
                matches += 1
        
        if not query_keywords:
            return 0.0
        
        return matches / len(query_keywords)
    
    def retrieve(
        self,
        query: str,
        memories: List[MemoryItem],
        limit: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """基于关键词的检索"""
        query_keywords = self._extract_keywords(query)
        
        results = []
        for memory in memories:
            score = self._calculate_keyword_score(query_keywords, memory.content)
            if score > 0:
                results.append({
                    "memory": memory,
                    "score": score,
                    "strategy": "keyword"
                })
        
        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

class VectorRetrievalStrategy(RetrievalStrategy):
    """向量检索策略"""
    
    def __init__(self, embedder=None):
        self.embedder = embedder
    
    def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入向量"""
        if self.embedder:
            return self.embedder.encode(text)
        else:
            # 简单的TF-IDF向量化作为fallback
            return self._simple_tfidf_vector(text)
    
    def _simple_tfidf_vector(self, text: str, dim: int = 100) -> List[float]:
        """简单的TF-IDF向量化"""
        words = re.findall(r'\w+', text.lower())
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 简化的向量表示
        vector = [0.0] * dim
        for i, word in enumerate(list(word_freq.keys())[:dim]):
            vector[i] = word_freq[word] / len(words)
        
        return vector
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(a * a for a in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def retrieve(
        self,
        query: str,
        memories: List[MemoryItem],
        limit: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """基于向量相似度的检索"""
        query_vector = self._get_embedding(query)
        
        results = []
        for memory in memories:
            memory_vector = self._get_embedding(memory.content)
            similarity = self._cosine_similarity(query_vector, memory_vector)
            
            if similarity > 0.1:  # 最小相似度阈值
                results.append({
                    "memory": memory,
                    "score": similarity,
                    "strategy": "vector"
                })
        
        # 按相似度排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

class HybridRetrievalStrategy(RetrievalStrategy):
    """混合检索策略"""
    
    def __init__(self, keyword_weight: float = 0.3, vector_weight: float = 0.7, embedder=None):
        self.keyword_strategy = KeywordRetrievalStrategy()
        self.vector_strategy = VectorRetrievalStrategy(embedder)
        self.keyword_weight = keyword_weight
        self.vector_weight = vector_weight
    
    def retrieve(
        self,
        query: str,
        memories: List[MemoryItem],
        limit: int = 5,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """混合检索策略"""
        # 获取关键词检索结果
        keyword_results = self.keyword_strategy.retrieve(query, memories, limit * 2)
        keyword_scores = {result["memory"].id: result["score"] for result in keyword_results}
        
        # 获取向量检索结果
        vector_results = self.vector_strategy.retrieve(query, memories, limit * 2)
        vector_scores = {result["memory"].id: result["score"] for result in vector_results}
        
        # 合并结果
        all_memory_ids = set(keyword_scores.keys()) | set(vector_scores.keys())
        
        combined_results = []
        for memory_id in all_memory_ids:
            # 找到对应的记忆对象
            memory = None
            for mem in memories:
                if mem.id == memory_id:
                    memory = mem
                    break
            
            if memory:
                keyword_score = keyword_scores.get(memory_id, 0.0)
                vector_score = vector_scores.get(memory_id, 0.0)
                
                # 计算加权分数
                combined_score = (
                    self.keyword_weight * keyword_score +
                    self.vector_weight * vector_score
                )
                
                combined_results.append({
                    "memory": memory,
                    "score": combined_score,
                    "keyword_score": keyword_score,
                    "vector_score": vector_score,
                    "strategy": "hybrid"
                })
        
        # 按综合分数排序
        combined_results.sort(key=lambda x: x["score"], reverse=True)
        return combined_results[:limit]

class MemoryRetriever:
    """记忆检索器
    
    提供多种检索策略和智能过滤功能
    """
    
    def __init__(self, config: MemoryConfig, embedder=None):
        self.config = config
        self.embedder = embedder
        
        # 初始化检索策略
        self.strategies = {
            "keyword": KeywordRetrievalStrategy(),
            "vector": VectorRetrievalStrategy(embedder),
            "hybrid": HybridRetrievalStrategy(embedder=embedder)
        }
        
        self.default_strategy = "hybrid"
    
    def retrieve(
        self,
        query: str,
        memories: List[MemoryItem],
        strategy: str = None,
        limit: int = 5,
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        time_range: Optional[tuple] = None,
        importance_threshold: Optional[float] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """检索相关记忆
        
        Args:
            query: 查询内容
            memories: 记忆列表
            strategy: 检索策略 ("keyword", "vector", "hybrid")
            limit: 返回数量限制
            user_id: 用户ID过滤
            memory_type: 记忆类型过滤
            time_range: 时间范围过滤 (start_time, end_time)
            importance_threshold: 重要性阈值过滤
            **kwargs: 其他参数
            
        Returns:
            检索结果列表
        """
        # 应用过滤条件
        filtered_memories = self._apply_filters(
            memories, user_id, memory_type, time_range, importance_threshold
        )
        
        if not filtered_memories:
            return []
        
        # 选择检索策略
        strategy_name = strategy or self.default_strategy
        retrieval_strategy = self.strategies.get(strategy_name, self.strategies[self.default_strategy])
        
        # 执行检索
        results = retrieval_strategy.retrieve(query, filtered_memories, limit, **kwargs)
        
        # 应用时间衰减
        results = self._apply_time_decay(results)
        
        # 重新排序
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:limit]
    
    def _apply_filters(
        self,
        memories: List[MemoryItem],
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        time_range: Optional[tuple] = None,
        importance_threshold: Optional[float] = None
    ) -> List[MemoryItem]:
        """应用过滤条件"""
        filtered = memories
        
        if user_id:
            filtered = [m for m in filtered if getattr(m, 'user_id', None) == user_id]
        
        if memory_type:
            filtered = [m for m in filtered if m.memory_type == memory_type]
        
        if time_range:
            start_time, end_time = time_range
            filtered = [
                m for m in filtered
                if start_time <= m.timestamp <= end_time
            ]
        
        if importance_threshold is not None:
            filtered = [m for m in filtered if m.importance >= importance_threshold]
        
        return filtered
    
    def _apply_time_decay(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """应用时间衰减"""
        current_time = datetime.now()
        
        for result in results:
            memory = result["memory"]
            time_diff = current_time - memory.timestamp
            days_diff = time_diff.days
            
            # 时间衰减因子
            decay_factor = self.config.decay_factor ** (days_diff / 7)  # 每周衰减
            
            # 应用衰减
            result["score"] *= decay_factor
            result["time_decay_factor"] = decay_factor
        
        return results
    
    def add_strategy(self, name: str, strategy: RetrievalStrategy):
        """添加自定义检索策略"""
        self.strategies[name] = strategy
    
    def set_default_strategy(self, strategy: str):
        """设置默认检索策略"""
        if strategy in self.strategies:
            self.default_strategy = strategy
        else:
            raise ValueError(f"未知的检索策略: {strategy}")
    
    def get_available_strategies(self) -> List[str]:
        """获取可用的检索策略列表"""
        return list(self.strategies.keys())
