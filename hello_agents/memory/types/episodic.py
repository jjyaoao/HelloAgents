"""情景记忆实现

按照第8章架构设计的情景记忆，提供：
- 具体交互事件存储
- 时间序列组织
- 上下文丰富的记忆
- 模式识别能力
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

from ..base import BaseMemory, MemoryItem, MemoryConfig

class Episode:
    """情景记忆中的单个情景"""
    
    def __init__(
        self,
        episode_id: str,
        user_id: str,
        session_id: str,
        timestamp: datetime,
        content: str,
        context: Dict[str, Any],
        outcome: Optional[str] = None,
        importance: float = 0.5
    ):
        self.episode_id = episode_id
        self.user_id = user_id
        self.session_id = session_id
        self.timestamp = timestamp
        self.content = content
        self.context = context
        self.outcome = outcome
        self.importance = importance

class EpisodicMemory(BaseMemory):
    """情景记忆实现
    
    特点：
    - 存储具体的交互事件
    - 包含丰富的上下文信息
    - 按时间序列组织
    - 支持模式识别和回溯
    """
    
    def __init__(self, config: MemoryConfig, storage_backend=None):
        super().__init__(config, storage_backend)
        
        # 情景记忆存储
        self.episodes: List[Episode] = []
        self.sessions: Dict[str, List[str]] = {}  # session_id -> episode_ids
        
        # 模式识别缓存
        self.patterns_cache = {}
        self.last_pattern_analysis = None
    
    def add(self, memory_item: MemoryItem) -> str:
        """添加情景记忆"""
        # 从元数据中提取情景信息
        session_id = memory_item.metadata.get("session_id", "default_session")
        context = memory_item.metadata.get("context", {})
        outcome = memory_item.metadata.get("outcome")
        
        # 创建情景
        episode = Episode(
            episode_id=memory_item.id,
            user_id=memory_item.user_id,
            session_id=session_id,
            timestamp=memory_item.timestamp,
            content=memory_item.content,
            context=context,
            outcome=outcome,
            importance=memory_item.importance
        )
        
        # 添加到存储
        self.episodes.append(episode)
        
        # 更新会话索引
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append(episode.episode_id)
        
        # 如果有存储后端，持久化
        if self.storage:
            self._persist_episode(episode)
        
        return memory_item.id
    
    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """检索情景记忆"""
        user_id = kwargs.get("user_id")
        session_id = kwargs.get("session_id")
        time_range = kwargs.get("time_range")
        
        # 过滤情景
        filtered_episodes = self._filter_episodes(user_id, session_id, time_range)
        
        # 计算相关性分数
        scored_episodes = []
        query_lower = query.lower()
        
        for episode in filtered_episodes:
            content_lower = episode.content.lower()
            
            # 简单的字符串包含匹配（对中文更友好）
            content_score = 0.0
            if query_lower in content_lower:
                content_score = 1.0
            else:
                # 尝试词汇级别的匹配
                query_words = set(query_lower.split())
                content_words = set(content_lower.split())
                if query_words and content_words:
                    intersection = query_words.intersection(content_words)
                    union = query_words.union(content_words)
                    content_score = len(intersection) / len(union) if union else 0
            
            # 上下文匹配
            context_score = 0.0
            context_text = json.dumps(episode.context, ensure_ascii=False).lower()
            if query_lower in context_text:
                context_score = 0.5
            
            # 综合分数 - 降低阈值，确保有匹配就返回
            total_score = (content_score * 0.7 + context_score * 0.3) * episode.importance
            
            # 降低阈值，只要有任何匹配就加入结果
            if total_score > 0 or query_lower in content_lower:
                if total_score == 0:  # 如果只是字符串匹配但分数为0，给一个基础分数
                    total_score = 0.1 * episode.importance
                scored_episodes.append((total_score, episode))
        
        # 排序并转换为MemoryItem
        scored_episodes.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, episode in scored_episodes[:limit]:
            memory_item = MemoryItem(
                id=episode.episode_id,
                content=episode.content,
                memory_type="episodic",
                user_id=episode.user_id,
                timestamp=episode.timestamp,
                importance=episode.importance,
                metadata={
                    "session_id": episode.session_id,
                    "context": episode.context,
                    "outcome": episode.outcome,
                    "relevance_score": score
                }
            )
            results.append(memory_item)
        
        return results
    
    def update(
        self,
        memory_id: str,
        content: str = None,
        importance: float = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """更新情景记忆"""
        for episode in self.episodes:
            if episode.episode_id == memory_id:
                if content is not None:
                    episode.content = content
                
                if importance is not None:
                    episode.importance = importance
                
                if metadata is not None:
                    episode.context.update(metadata.get("context", {}))
                    if "outcome" in metadata:
                        episode.outcome = metadata["outcome"]
                
                # 持久化更新
                if self.storage:
                    self._persist_episode(episode)
                
                return True
        return False
    
    def remove(self, memory_id: str) -> bool:
        """删除情景记忆"""
        for i, episode in enumerate(self.episodes):
            if episode.episode_id == memory_id:
                removed_episode = self.episodes.pop(i)
                
                # 从会话索引中删除
                session_id = removed_episode.session_id
                if session_id in self.sessions:
                    self.sessions[session_id].remove(memory_id)
                    if not self.sessions[session_id]:
                        del self.sessions[session_id]
                
                # 从存储后端删除
                if self.storage:
                    self._remove_from_storage(memory_id)
                
                return True
        return False
    
    def has_memory(self, memory_id: str) -> bool:
        """检查记忆是否存在"""
        return any(episode.episode_id == memory_id for episode in self.episodes)
    
    def clear(self):
        """清空所有情景记忆"""
        self.episodes.clear()
        self.sessions.clear()
        self.patterns_cache.clear()

    def get_all(self) -> List[MemoryItem]:
        """获取所有情景记忆（转换为MemoryItem格式）"""
        memory_items = []
        for episode in self.episodes:
            memory_item = MemoryItem(
                id=episode.episode_id,
                content=episode.content,
                memory_type="episodic",
                user_id=episode.user_id,
                timestamp=episode.timestamp,
                importance=episode.importance,
                metadata=episode.metadata
            )
            memory_items.append(memory_item)
        return memory_items
    
    def get_stats(self) -> Dict[str, Any]:
        """获取情景记忆统计信息"""
        return {
            "count": len(self.episodes),
            "sessions_count": len(self.sessions),
            "avg_importance": sum(e.importance for e in self.episodes) / len(self.episodes) if self.episodes else 0.0,
            "time_span_days": self._calculate_time_span(),
            "memory_type": "episodic"
        }
    
    def get_session_episodes(self, session_id: str) -> List[Episode]:
        """获取指定会话的所有情景"""
        if session_id not in self.sessions:
            return []
        
        episode_ids = self.sessions[session_id]
        return [e for e in self.episodes if e.episode_id in episode_ids]
    
    def find_patterns(self, user_id: str = None, min_frequency: int = 2) -> List[Dict[str, Any]]:
        """发现用户行为模式"""
        # 检查缓存
        cache_key = f"{user_id}_{min_frequency}"
        if (cache_key in self.patterns_cache and 
            self.last_pattern_analysis and 
            (datetime.now() - self.last_pattern_analysis).hours < 1):
            return self.patterns_cache[cache_key]
        
        # 过滤情景
        episodes = [e for e in self.episodes if user_id is None or e.user_id == user_id]
        
        # 简单的模式识别：基于内容关键词
        keyword_patterns = {}
        context_patterns = {}
        
        for episode in episodes:
            # 提取关键词
            words = episode.content.lower().split()
            for word in words:
                if len(word) > 3:  # 忽略短词
                    keyword_patterns[word] = keyword_patterns.get(word, 0) + 1
            
            # 提取上下文模式
            for key, value in episode.context.items():
                pattern_key = f"{key}:{value}"
                context_patterns[pattern_key] = context_patterns.get(pattern_key, 0) + 1
        
        # 筛选频繁模式
        patterns = []
        
        for keyword, frequency in keyword_patterns.items():
            if frequency >= min_frequency:
                patterns.append({
                    "type": "keyword",
                    "pattern": keyword,
                    "frequency": frequency,
                    "confidence": frequency / len(episodes)
                })
        
        for context_pattern, frequency in context_patterns.items():
            if frequency >= min_frequency:
                patterns.append({
                    "type": "context",
                    "pattern": context_pattern,
                    "frequency": frequency,
                    "confidence": frequency / len(episodes)
                })
        
        # 按频率排序
        patterns.sort(key=lambda x: x["frequency"], reverse=True)
        
        # 缓存结果
        self.patterns_cache[cache_key] = patterns
        self.last_pattern_analysis = datetime.now()
        
        return patterns
    
    def get_timeline(self, user_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """获取时间线视图"""
        episodes = [e for e in self.episodes if user_id is None or e.user_id == user_id]
        episodes.sort(key=lambda x: x.timestamp, reverse=True)
        
        timeline = []
        for episode in episodes[:limit]:
            timeline.append({
                "episode_id": episode.episode_id,
                "timestamp": episode.timestamp.isoformat(),
                "content": episode.content[:100] + "..." if len(episode.content) > 100 else episode.content,
                "session_id": episode.session_id,
                "importance": episode.importance,
                "outcome": episode.outcome
            })
        
        return timeline
    
    def _filter_episodes(
        self,
        user_id: str = None,
        session_id: str = None,
        time_range: Tuple[datetime, datetime] = None
    ) -> List[Episode]:
        """过滤情景"""
        filtered = self.episodes
        
        if user_id:
            filtered = [e for e in filtered if e.user_id == user_id]
        
        if session_id:
            filtered = [e for e in filtered if e.session_id == session_id]
        
        if time_range:
            start_time, end_time = time_range
            filtered = [e for e in filtered if start_time <= e.timestamp <= end_time]
        
        return filtered
    
    def _calculate_time_span(self) -> float:
        """计算记忆时间跨度（天）"""
        if not self.episodes:
            return 0.0
        
        timestamps = [e.timestamp for e in self.episodes]
        min_time = min(timestamps)
        max_time = max(timestamps)
        
        return (max_time - min_time).days
    
    def _persist_episode(self, episode: Episode):
        """持久化情景到存储后端"""
        if self.storage and hasattr(self.storage, 'add_memory'):
            self.storage.add_memory(
                memory_id=episode.episode_id,
                user_id=episode.user_id,
                content=episode.content,
                memory_type="episodic",
                timestamp=int(episode.timestamp.timestamp()),
                importance=episode.importance,
                properties={
                    "session_id": episode.session_id,
                    "context": episode.context,
                    "outcome": episode.outcome
                }
            )
    
    def _remove_from_storage(self, memory_id: str):
        """从存储后端删除"""
        if self.storage and hasattr(self.storage, 'delete_memory'):
            self.storage.delete_memory(memory_id)
