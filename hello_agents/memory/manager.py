"""记忆管理器 - 记忆核心层的统一管理接口"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging
import os

from .base import MemoryItem, MemoryConfig
from .types.working import WorkingMemory
from .types.episodic import EpisodicMemory
from .types.semantic import SemanticMemory
from .types.perceptual import PerceptualMemory
from .archive import ArchiveManager, ArchivePolicy, integrate_archive_to_memory
# 存储和检索功能已被各记忆类型内部实现替代

logger = logging.getLogger(__name__)


class MemoryManager:
    """记忆管理器 - 统一的记忆操作接口

    负责：
    - 记忆生命周期管理
    - 记忆优先级和重要性评估
    - 记忆遗忘和清理机制
    - 记忆归档与恢复
    - 多类型记忆的协调管理
    """

    def __init__(
        self,
        config: Optional[MemoryConfig] = None,
        user_id: str = "default_user",
        enable_working: bool = True,
        enable_episodic: bool = True,
        enable_semantic: bool = True,
        enable_perceptual: bool = False,
        archive_policy: ArchivePolicy = None,
        enable_archive: bool = True,
    ):
        self.config = config or MemoryConfig()
        self.user_id = user_id

        # 存储和检索功能已移至各记忆类型内部实现

        # 初始化各类型记忆
        self.memory_types = {}

        if enable_working:
            self.memory_types["working"] = WorkingMemory(self.config)

        if enable_episodic:
            self.memory_types["episodic"] = EpisodicMemory(self.config)

        if enable_semantic:
            self.memory_types["semantic"] = SemanticMemory(self.config)

        if enable_perceptual:
            self.memory_types["perceptual"] = PerceptualMemory(self.config)

        # 初始化归档管理器
        self.archive_manager = None
        if enable_archive:
            archive_path = getattr(
                self.config,
                "archive_path",
                os.path.join(self.config.storage_path, "archive.db"),
            )
            self.archive_manager = ArchiveManager(
                archive_path=archive_path, policy=archive_policy
            )
            # 为每种记忆类型集成归档功能
            for memory_type, instance in self.memory_types.items():
                integrate_archive_to_memory(instance, self.archive_manager)

        logger.info(
            f"MemoryManager初始化完成，启用记忆类型: {list(self.memory_types.keys())}, "
            f"归档系统: {'启用' if enable_archive else '禁用'}"
        )

    def add_memory(
        self,
        content: str,
        memory_type: str = "working",
        importance: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_classify: bool = True,
    ) -> str:
        """添加记忆

        Args:
            content: 记忆内容
            memory_type: 记忆类型
            importance: 重要性分数 (0-1)
            metadata: 元数据
            auto_classify: 是否自动分类到合适的记忆类型

        Returns:
            记忆ID
        """
        # 自动分类记忆类型
        if auto_classify:
            memory_type = self._classify_memory_type(content, metadata)

        # 计算重要性
        if importance is None:
            importance = self._calculate_importance(content, metadata)

        # 创建记忆项
        memory_item = MemoryItem(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            user_id=self.user_id,
            timestamp=datetime.now(),
            importance=importance,
            metadata=metadata or {},
        )

        # 添加到对应的记忆类型
        if memory_type in self.memory_types:
            memory_id = self.memory_types[memory_type].add(memory_item)
            logger.debug(f"添加记忆到 {memory_type}: {memory_id}")
            return memory_id
        else:
            raise ValueError(f"不支持的记忆类型: {memory_type}")

    def retrieve_memories(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
        min_importance: float = 0.0,
        time_range: Optional[tuple] = None,
    ) -> List[MemoryItem]:
        """检索记忆

        Args:
            query: 查询内容
            memory_types: 要检索的记忆类型列表
            limit: 返回数量限制
            min_importance: 最小重要性阈值
            time_range: 时间范围 (start_time, end_time)

        Returns:
            检索到的记忆列表
        """
        if memory_types is None:
            memory_types = list(self.memory_types.keys())

        # 从各个记忆类型中检索
        all_results = []
        per_type_limit = max(1, limit // len(memory_types))

        for memory_type in memory_types:
            if memory_type in self.memory_types:
                memory_instance = self.memory_types[memory_type]
                try:
                    # 使用各个记忆类型自己的检索方法
                    type_results = memory_instance.retrieve(
                        query=query,
                        limit=per_type_limit,
                        min_importance=min_importance,
                        user_id=self.user_id,
                    )
                    all_results.extend(type_results)
                except Exception as e:
                    logger.warning(f"检索 {memory_type} 记忆时出错: {e}")
                    continue

        # 按重要性和相关性排序
        all_results.sort(key=lambda x: x.importance, reverse=True)
        return all_results[:limit]

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        importance: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """更新记忆

        Args:
            memory_id: 记忆ID
            content: 新内容
            importance: 新重要性
            metadata: 新元数据

        Returns:
            是否更新成功
        """
        # 查找记忆所在的类型
        for memory_type, memory_instance in self.memory_types.items():
            if memory_instance.has_memory(memory_id):
                return memory_instance.update(memory_id, content, importance, metadata)

        logger.warning(f"未找到记忆: {memory_id}")
        return False

    def remove_memory(self, memory_id: str) -> bool:
        """删除记忆

        Args:
            memory_id: 记忆ID

        Returns:
            是否删除成功
        """
        for memory_type, memory_instance in self.memory_types.items():
            if memory_instance.has_memory(memory_id):
                return memory_instance.remove(memory_id)

        logger.warning(f"未找到记忆: {memory_id}")
        return False

    def forget_memories(
        self,
        strategy: str = "importance_based",
        threshold: float = 0.1,
        max_age_days: int = 30,
        smart_weights: dict = None,
    ) -> int:
        """记忆遗忘机制

        Args:
            strategy: 遗忘策略 ("importance_based", "time_based", "capacity_based")
            threshold: 遗忘阈值
            max_age_days: 最大保存天数
            smart_weights: 智能遗忘策略的权重配置，
            例如 {"importance": 0.5, "access": 0.3, "recency": 0.2}

        Returns:
            遗忘的记忆数量
        """
        total_forgotten = 0

        for memory_type, memory_instance in self.memory_types.items():
            if not hasattr(memory_instance, "forget"):
                continue

            if strategy == "smart":
                forgotten = memory_instance.smart_forget(
                    threshold=threshold, weights=smart_weights
                )
            else:
                forgotten = memory_instance.forget(
                    strategy=strategy, threshold=threshold, max_age_days=max_age_days
                )

            total_forgotten += forgotten

        logger.info(f"记忆遗忘完成: {total_forgotten} 条记忆")
        return total_forgotten

    def consolidate_memories(
        self,
        from_type: str = "working",
        to_type: str = "episodic",
        importance_threshold: float = 0.7,
    ) -> int:
        """记忆整合 - 将重要的短期记忆转换为长期记忆

        Args:
            from_type: 源记忆类型
            to_type: 目标记忆类型
            importance_threshold: 重要性阈值

        Returns:
            整合的记忆数量
        """
        if from_type not in self.memory_types or to_type not in self.memory_types:
            logger.warning(f"记忆类型不存在: {from_type} -> {to_type}")
            return 0

        # 获取高重要性的源记忆
        source_memory = self.memory_types[from_type]
        target_memory = self.memory_types[to_type]

        # 获取需要整合的记忆
        all_memories = source_memory.get_all()
        candidates = [m for m in all_memories if m.importance >= importance_threshold]

        consolidated_count = 0
        for memory in candidates:
            # 移动到目标记忆类型
            if source_memory.remove(memory.id):
                memory.memory_type = to_type
                memory.importance *= 1.1  # 提升重要性
                target_memory.add(memory)
                consolidated_count += 1

        logger.info(
            f"记忆整合完成: {consolidated_count} 条记忆从 {from_type} 转移到 {to_type}"
        )
        return consolidated_count

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        stats = {
            "user_id": self.user_id,
            "enabled_types": list(self.memory_types.keys()),
            "total_memories": 0,
            "memories_by_type": {},
            "config": {
                "max_capacity": self.config.max_capacity,
                "importance_threshold": self.config.importance_threshold,
                "decay_factor": self.config.decay_factor,
            },
        }

        for memory_type, memory_instance in self.memory_types.items():
            type_stats = memory_instance.get_stats()
            stats["memories_by_type"][memory_type] = type_stats
            # 使用count字段（活跃记忆数），而不是total_count（包含已遗忘的）
            stats["total_memories"] += type_stats.get("count", 0)

        return stats

    def clear_all_memories(self):
        """清空所有记忆"""
        for memory_type, memory_instance in self.memory_types.items():
            memory_instance.clear()
        logger.info("所有记忆已清空")

    def _classify_memory_type(
        self, content: str, metadata: Optional[Dict[str, Any]]
    ) -> str:
        """自动分类记忆类型"""
        if metadata and metadata.get("type"):
            return metadata["type"]

        # 简单的分类逻辑，可以扩展为更复杂的分类器
        if self._is_episodic_content(content):
            return "episodic"
        elif self._is_semantic_content(content):
            return "semantic"
        else:
            return "working"

    def _is_episodic_content(self, content: str) -> bool:
        """判断是否为情景记忆内容"""
        episodic_keywords = ["昨天", "今天", "明天", "上次", "记得", "发生", "经历"]
        return any(keyword in content for keyword in episodic_keywords)

    def _is_semantic_content(self, content: str) -> bool:
        """判断是否为语义记忆内容"""
        semantic_keywords = ["定义", "概念", "规则", "知识", "原理", "方法"]
        return any(keyword in content for keyword in semantic_keywords)

    def _calculate_importance(
        self, content: str, metadata: Optional[Dict[str, Any]]
    ) -> float:
        """计算记忆重要性"""
        importance = 0.5  # 基础重要性

        # 基于内容长度
        if len(content) > 100:
            importance += 0.1

        # 基于关键词
        important_keywords = ["重要", "关键", "必须", "注意", "警告", "错误"]
        if any(keyword in content for keyword in important_keywords):
            importance += 0.2

        # 基于元数据
        if metadata:
            if metadata.get("priority") == "high":
                importance += 0.3
            elif metadata.get("priority") == "low":
                importance -= 0.2

        return max(0.0, min(1.0, importance))

    def __str__(self) -> str:
        stats = self.get_memory_stats()
        return f"MemoryManager(user={self.user_id}, total={stats['total_memories']})"

    def archive_memories(
        self,
        memory_type: str = None,
        memory_ids: List[str] = None,
        max_count: int = None,
    ) -> int:
        """归档记忆到冷存储

        Args:
            memory_type: 记忆类型，None则归档所有类型
            memory_ids: 指定要归档的记忆ID列表
            max_count: 最大归档数量

        Returns:
            归档成功的记忆数量
        """
        if not self.archive_manager:
            logger.warning("归档系统未启用")
            return 0

        total_archived = 0

        types_to_archive = (
            [memory_type] if memory_type else list(self.memory_types.keys())
        )

        for mt in types_to_archive:
            if mt not in self.memory_types:
                continue
            count = self.archive_manager.archive_batch(
                self.memory_types[mt], memory_ids=memory_ids, max_count=max_count
            )
            total_archived += count

        return total_archived

    def restore_memories(
        self, memory_ids: List[str], target_type: str = None
    ) -> List[MemoryItem]:
        """恢复归档记忆

        Args:
            memory_ids: 要恢复的记忆ID列表
            target_type: 恢复到的目标记忆类型，None则使用原始类型

        Returns:
            恢复成功的记忆列表
        """
        if not self.archive_manager:
            logger.warning("归档系统未启用")
            return []

        restored = []

        for memory_id in memory_ids:
            archived = self.archive_manager.cold_storage.retrieve(memory_id)
            if not archived:
                continue

            target = target_type or archived["memory_type"]
            if target not in self.memory_types:
                logger.warning(f"目标记忆类型不存在: {target}")
                continue

            memory = self.archive_manager.restore(memory_id, self.memory_types[target])
            if memory:
                restored.append(memory)

        return restored

    def restore_search(
        self, query: str, memory_type: str = None, limit: int = 5
    ) -> List[MemoryItem]:
        """搜索并恢复归档记忆

        Args:
            query: 搜索查询
            memory_type: 记忆类型过滤
            limit: 最多恢复数量

        Returns:
            恢复的记忆列表
        """
        if not self.archive_manager:
            logger.warning("归档系统未启用")
            return []

        target_instance = None
        if memory_type and memory_type in self.memory_types:
            target_instance = self.memory_types[memory_type]
        elif self.memory_types:
            target_instance = list(self.memory_types.values())[0]

        if not target_instance:
            return []

        return self.archive_manager.restore_search(
            query=query,
            memory_instance=target_instance,
            memory_type=memory_type,
            limit=limit,
        )

    def search_archived(
        self, query: str, memory_type: str = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索归档记忆（不恢复）

        Args:
            query: 搜索查询
            memory_type: 记忆类型过滤
            limit: 返回数量限制

        Returns:
            归档记忆列表
        """
        if not self.archive_manager:
            logger.warning("归档系统未启用")
            return []

        return self.archive_manager.cold_storage.search(
            query=query, memory_type=memory_type, limit=limit
        )

    def run_auto_archive(self) -> Dict[str, int]:
        """执行自动归档检查

        Returns:
            各类型归档数量统计
        """
        if not self.archive_manager:
            return {}

        return self.archive_manager.auto_archive(self.memory_types)

    def get_archive_stats(self) -> Dict[str, Any]:
        """获取归档统计信息"""
        if not self.archive_manager:
            return {"enabled": False}

        return self.archive_manager.get_stats()
