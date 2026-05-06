"""记忆归档系统

将长期不用但可能有价值的记忆转移到冷存储，需要时再恢复。
支持：
- 自动归档策略（基于访问时间、重要性等）
- 多种冷存储后端（SQLite文件存储）
- 归档索引加速恢复
- 与四种记忆类型无缝集成
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json
import os
import logging
import sqlite3

from .base import BaseMemory, MemoryItem

logger = logging.getLogger(__name__)


class ArchiveStatus(str, Enum):
    """记忆归档状态"""

    ACTIVE = "active"
    ARCHIVED = "archived"
    RESTORED = "restored"


class ArchivePolicy:
    """归档策略配置"""

    def __init__(
        self,
        archive_after_days: int = 90,
        min_importance_to_keep: float = 0.4,
        min_access_count: int = 2,
        max_archive_size: int = 10000,
        auto_archive_enabled: bool = True,
        archive_check_interval_hours: int = 24,
    ):
        self.archive_after_days = archive_after_days
        self.min_importance_to_keep = min_importance_to_keep
        self.min_access_count = min_access_count
        self.max_archive_size = max_archive_size
        self.auto_archive_enabled = auto_archive_enabled
        self.archive_check_interval_hours = archive_check_interval_hours


class ColdStorage:
    """冷存储后端 - 使用SQLite存储归档数据"""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(storage_path), exist_ok=True) if os.path.dirname(
            storage_path
        ) else None
        self._init_database()

    def _init_database(self):
        """初始化归档数据库"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archived_memories (
                memory_id TEXT PRIMARY KEY,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                importance REAL NOT NULL,
                metadata TEXT,
                archived_at INTEGER NOT NULL,
                last_access_time INTEGER,
                access_count INTEGER DEFAULT 0,
                archive_status TEXT DEFAULT 'archived'
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_archive_memory_type ON archived_memories(memory_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_archive_archived_at ON archived_memories(archived_at)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_archive_content ON archived_memories(content)
        """)
        conn.commit()
        conn.close()

    def store(
        self,
        memory: MemoryItem,
        archived_at: datetime,
        last_access_time: datetime = None,
        access_count: int = 0,
    ) -> bool:
        """存储归档记忆"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO archived_memories 
                (memory_id, memory_type, content, user_id, timestamp, 
                 importance, metadata, archived_at, last_access_time, access_count, archive_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    memory.id,
                    memory.memory_type,
                    memory.content,
                    memory.user_id,
                    int(memory.timestamp.timestamp()),
                    memory.importance,
                    json.dumps(memory.metadata, ensure_ascii=False),
                    int(archived_at.timestamp()),
                    int(last_access_time.timestamp()) if last_access_time else None,
                    access_count,
                    ArchiveStatus.ARCHIVED.value,
                ),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"存储归档记忆失败: {e}")
            return False

    def retrieve(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """检索归档记忆"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM archived_memories WHERE memory_id = ?
        """,
            (memory_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_memory(row)
        return None

    def search(
        self, query: str, memory_type: str = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """搜索归档记忆"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()

        sql = "SELECT * FROM archived_memories WHERE content LIKE ?"
        params = [f"%{query}%"]

        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)

        sql += " ORDER BY importance DESC, archived_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_memory(row) for row in rows]

    def get_all_by_type(
        self, memory_type: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """按类型获取所有归档记忆"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM archived_memories 
            WHERE memory_type = ? 
            ORDER BY archived_at DESC LIMIT ?
        """,
            (memory_type, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_memory(row) for row in rows]

    def update_access(self, memory_id: str) -> bool:
        """更新访问信息"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE archived_memories 
                SET access_count = access_count + 1, 
                    last_access_time = ?,
                    archive_status = ?
                WHERE memory_id = ?
            """,
                (
                    int(datetime.now().timestamp()),
                    ArchiveStatus.RESTORED.value,
                    memory_id,
                ),
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"更新归档访问信息失败: {e}")
            return False

    def delete(self, memory_id: str) -> bool:
        """删除归档记忆"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM archived_memories WHERE memory_id = ?", (memory_id,)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"删除归档记忆失败: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取归档统计"""
        conn = sqlite3.connect(self.storage_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM archived_memories")
        total = cursor.fetchone()[0]
        cursor.execute(
            "SELECT memory_type, COUNT(*) FROM archived_memories GROUP BY memory_type"
        )
        by_type = dict(cursor.fetchall())
        cursor.execute("SELECT AVG(importance) FROM archived_memories")
        avg_importance = cursor.fetchone()[0] or 0.0
        conn.close()

        return {
            "total_archived": total,
            "by_type": by_type,
            "avg_importance": avg_importance,
            "storage_path": self.storage_path,
        }

    def clear_all(self) -> bool:
        """清空所有归档"""
        try:
            conn = sqlite3.connect(self.storage_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM archived_memories")
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"清空归档失败: {e}")
            return False

    def _row_to_memory(self, row: tuple) -> Dict[str, Any]:
        """行转记忆字典"""
        return {
            "memory_id": row[0],
            "memory_type": row[1],
            "content": row[2],
            "user_id": row[3],
            "timestamp": datetime.fromtimestamp(row[4]),
            "importance": row[5],
            "metadata": json.loads(row[6]) if row[6] else {},
            "archived_at": datetime.fromtimestamp(row[7]),
            "last_access_time": datetime.fromtimestamp(row[8]) if row[8] else None,
            "access_count": row[9],
            "archive_status": row[10],
        }


class ArchiveManager:
    """记忆归档管理器

    职责：
    - 评估哪些记忆需要归档
    - 执行归档操作（热存储 -> 冷存储）
    - 执行恢复操作（冷存储 -> 热存储）
    - 管理归档索引
    - 触发自动归档任务
    """

    def __init__(
        self,
        archive_path: str = "./memory_data/archive.db",
        policy: ArchivePolicy = None,
    ):
        self.archive_path = archive_path
        self.policy = policy or ArchivePolicy()
        self.cold_storage = ColdStorage(archive_path)
        self.last_archive_check = None

    def evaluate_archive_candidates(
        self, memory_instance: BaseMemory
    ) -> List[Dict[str, Any]]:
        """评估哪些记忆应该被归档

        Args:
            memory_instance: 记忆实例

        Returns:
            候选归档的记忆列表
        """
        candidates = []
        now = datetime.now()

        for memory in memory_instance.get_all():
            score = self._calculate_archive_score(memory, now)

            should_archive = (
                score < self.policy.min_importance_to_keep
                and self._days_since_access(memory) >= self.policy.archive_after_days
            )

            if should_archive:
                candidates.append(
                    {
                        "memory": memory,
                        "archive_score": score,
                        "days_since_access": self._days_since_access(memory),
                    }
                )

        candidates.sort(key=lambda x: x["archive_score"])
        return candidates

    def _calculate_archive_score(self, memory: MemoryItem, now: datetime) -> float:
        """计算归档评分（重要性 - 衰减）"""
        last_access = memory.metadata.get("last_access_time", memory.timestamp)
        if isinstance(last_access, str):
            last_access = datetime.fromisoformat(last_access)

        days_inactive = (now - last_access).days

        importance = memory.importance
        inactivity_penalty = min(1.0, days_inactive / 365.0)

        score = importance * (1.0 - inactivity_penalty * 0.5)
        return max(0.0, min(1.0, score))

    def _days_since_access(self, memory: MemoryItem) -> int:
        """计算距离上次访问的天数"""
        last_access = memory.metadata.get("last_access_time", memory.timestamp)
        if isinstance(last_access, str):
            last_access = datetime.fromisoformat(last_access)

        return (datetime.now() - last_access).days

    def archive(
        self,
        memory: MemoryItem,
        last_access_time: datetime = None,
        access_count: int = 0,
    ) -> bool:
        """归档单条记忆"""
        return self.cold_storage.store(
            memory=memory,
            archived_at=datetime.now(),
            last_access_time=last_access_time,
            access_count=access_count,
        )

    def archive_batch(
        self,
        memory_instance: BaseMemory,
        memory_ids: List[str] = None,
        max_count: int = None,
    ) -> int:
        """批量归档记忆

        Args:
            memory_instance: 记忆实例
            memory_ids: 指定要归档的记忆ID列表，None则自动评估
            max_count: 最大归档数量

        Returns:
            归档成功的记忆数量
        """
        archived_count = 0

        if memory_ids is None:
            candidates = self.evaluate_archive_candidates(memory_instance)
            memory_ids = [c["memory"].id for c in candidates]

        if max_count:
            memory_ids = memory_ids[:max_count]

        total_size = self.cold_storage.get_stats()["total_archived"]

        for memory_id in memory_ids:
            if total_size + archived_count >= self.policy.max_archive_size:
                logger.warning(f"归档存储已满 ({self.policy.max_archive_size})")
                break

            memory = self._find_memory_in_instance(memory_instance, memory_id)
            if memory:
                last_access = memory.metadata.get("last_access_time")
                access_count = memory.metadata.get("access_count", 0)

                if self.archive(memory, last_access, access_count):
                    memory_instance.remove(memory_id)
                    archived_count += 1

        logger.info(f"批量归档完成: {archived_count} 条记忆")
        return archived_count

    def _find_memory_in_instance(
        self, memory_instance: BaseMemory, memory_id: str
    ) -> Optional[MemoryItem]:
        """在记忆实例中查找记忆"""
        for memory in memory_instance.get_all():
            if memory.id == memory_id:
                return memory
        return None

    def restore(
        self, memory_id: str, memory_instance: BaseMemory
    ) -> Optional[MemoryItem]:
        """恢复归档记忆到热存储

        Args:
            memory_id: 记忆ID
            memory_instance: 目标记忆实例

        Returns:
            恢复的记忆项，失败返回None
        """
        archived = self.cold_storage.retrieve(memory_id)
        if not archived:
            logger.warning(f"归档中未找到记忆: {memory_id}")
            return None

        memory_item = MemoryItem(
            id=archived["memory_id"],
            content=archived["content"],
            memory_type=archived["memory_type"],
            user_id=archived["user_id"],
            timestamp=archived["timestamp"],
            importance=archived["importance"],
            metadata={
                **archived["metadata"],
                "restored_from_archive": True,
                "archived_at": archived["archived_at"].isoformat(),
                "original_access_count": archived["access_count"],
            },
        )

        try:
            memory_instance.add(memory_item)
            self.cold_storage.update_access(memory_id)
            logger.info(f"记忆已恢复: {memory_id}")
            return memory_item
        except Exception as e:
            logger.error(f"恢复记忆失败: {e}")
            return None

    def restore_search(
        self,
        query: str,
        memory_instance: BaseMemory,
        memory_type: str = None,
        limit: int = 5,
    ) -> List[MemoryItem]:
        """搜索并恢复归档记忆

        Args:
            query: 搜索查询
            memory_instance: 目标记忆实例
            memory_type: 记忆类型过滤
            limit: 最多恢复数量

        Returns:
            恢复的记忆列表
        """
        archived_results = self.cold_storage.search(
            query=query, memory_type=memory_type, limit=limit
        )

        restored = []
        for archived in archived_results:
            memory = self.restore(archived["memory_id"], memory_instance)
            if memory:
                restored.append(memory)

        return restored

    def auto_archive(self, memory_instances: Dict[str, BaseMemory]) -> Dict[str, int]:
        """自动归档检查和执行

        Args:
            memory_instances: 记忆类型名称到实例的映射

        Returns:
            各类型归档数量统计
        """
        if not self.policy.auto_archive_enabled:
            return {}

        now = datetime.now()
        if self.last_archive_check:
            hours_since = (now - self.last_archive_check).total_seconds() / 3600
            if hours_since < self.policy.archive_check_interval_hours:
                return {}

        self.last_archive_check = now
        results = {}

        for memory_type, instance in memory_instances.items():
            count = self.archive_batch(
                instance, max_count=self.policy.max_archive_size // 4
            )
            if count > 0:
                results[memory_type] = count

        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取归档统计"""
        cold_stats = self.cold_storage.get_stats()

        return {
            "archive_policy": {
                "archive_after_days": self.policy.archive_after_days,
                "min_importance_to_keep": self.policy.min_importance_to_keep,
                "max_archive_size": self.policy.max_archive_size,
                "auto_archive_enabled": self.policy.auto_archive_enabled,
            },
            "cold_storage": cold_stats,
            "last_archive_check": self.last_archive_check.isoformat()
            if self.last_archive_check
            else None,
        }

    def clear_archive(self) -> bool:
        """清空归档存储"""
        return self.cold_storage.clear_all()


def integrate_archive_to_memory(
    memory_instance: BaseMemory, archive_manager: ArchiveManager
) -> None:
    """为记忆实例集成归档功能

    为 BaseMemory 添加归档相关方法。
    这是一个猴子补丁，用于向后兼容。

    Args:
        memory_instance: 记忆实例
        archive_manager: 归档管理器
    """

    def archive_to_cold_storage(self, memory_id: str = None) -> bool:
        """归档记忆到冷存储"""
        if memory_id:
            memory = next((m for m in self.get_all() if m.id == memory_id), None)
            if memory:
                return archive_manager.archive(
                    memory,
                    last_access_time=memory.metadata.get("last_access_time"),
                    access_count=memory.metadata.get("access_count", 0),
                )
        return False

    def restore_from_cold_storage(self, memory_id: str) -> Optional[MemoryItem]:
        """从冷存储恢复记忆"""
        archived = archive_manager.cold_storage.retrieve(memory_id)
        if not archived:
            logger.warning(f"归档中未找到记忆: {memory_id}")
            return None

        memory_item = (
            self.from_archive(archived)
            if hasattr(self, "from_archive")
            else MemoryItem(
                id=archived["memory_id"],
                content=archived["content"],
                memory_type=archived["memory_type"],
                user_id=archived["user_id"],
                timestamp=archived["timestamp"],
                importance=archived["importance"],
                metadata={
                    **archived["metadata"],
                    "restored_from_archive": True,
                    "archived_at": archived["archived_at"].isoformat(),
                },
            )
        )

        try:
            self.add(memory_item)
            archive_manager.cold_storage.update_access(memory_id)
            logger.info(f"记忆已恢复: {memory_id}")
            return memory_item
        except Exception as e:
            logger.error(f"恢复记忆失败: {e}")
            return None

    def search_in_archive(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """在归档中搜索"""
        return archive_manager.cold_storage.search(
            query=query, memory_type=self.memory_type, limit=limit
        )

    memory_instance.archive_to_cold_storage = archive_to_cold_storage.__get__(
        memory_instance, BaseMemory
    )
    memory_instance.restore_from_cold_storage = restore_from_cold_storage.__get__(
        memory_instance, BaseMemory
    )
    memory_instance.search_in_archive = search_in_archive.__get__(
        memory_instance, BaseMemory
    )
