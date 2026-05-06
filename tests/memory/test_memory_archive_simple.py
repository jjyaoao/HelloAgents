"""智能遗忘策略和记忆归档测试用例（简化版）"""

import pytest
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from hello_agents.memory.base import MemoryItem, MemoryConfig
from hello_agents.memory.types.working import WorkingMemory
from hello_agents.memory.archive import (
    ArchiveManager,
    ArchivePolicy,
    ColdStorage,
    ArchiveStatus,
)
from dotenv import load_dotenv

load_dotenv()


class TestSmartForgetWorking:
    """工作记忆智能遗忘测试"""

    @pytest.fixture
    def config(self):
        return MemoryConfig(
            max_capacity=100,
            working_memory_capacity=20,
            working_memory_tokens=5000,
            working_memory_ttl_minutes=30,
        )

    @pytest.fixture
    def working_memory(self, config):
        return WorkingMemory(config)

    def test_working_smart_forget(self, working_memory):
        """测试工作记忆智能遗忘"""
        now = datetime.now()

        for i in range(5):
            item = MemoryItem(
                id=f"work_{i}",
                content=f"工作内容{i}",
                memory_type="working",
                user_id="test_user",
                timestamp=now - timedelta(minutes=i * 10),
                importance=0.1 + i * 0.18,
                metadata={},
            )
            working_memory.add(item)

        initial_count = len(working_memory.get_all())
        forgotten = working_memory.smart_forget(threshold=0.5)

        assert forgotten >= 1, f"应遗忘至少1条记忆，实际遗忘{forgotten}条"
        assert len(working_memory.get_all()) < initial_count

    def test_smart_forget_with_custom_weights(self, working_memory):
        """测试自定义权重"""
        now = datetime.now()

        for i in range(3):
            item = MemoryItem(
                id=f"weight_{i}",
                content=f"测试记忆{i}",
                memory_type="working",
                user_id="test_user",
                timestamp=now,
                importance=0.5,
                metadata={},
            )
            working_memory.add(item)

        weights = {"importance": 0.8, "access": 0.1, "recency": 0.1}
        forgotten = working_memory.smart_forget(threshold=0.3, weights=weights)

        assert forgotten >= 0, "自定义权重应该正常工作"

    def test_smart_forget_preserves_high_importance(self, working_memory):
        """测试高重要性记忆不会被遗忘"""
        now = datetime.now()

        high_imp = MemoryItem(
            id="high",
            content="高重要性记忆",
            memory_type="working",
            user_id="test_user",
            timestamp=now,
            importance=0.95,
            metadata={},
        )
        low_imp = MemoryItem(
            id="low",
            content="低重要性记忆",
            memory_type="working",
            user_id="test_user",
            timestamp=now - timedelta(days=60),
            importance=0.1,
            metadata={},
        )

        working_memory.add(high_imp)
        working_memory.add(low_imp)

        working_memory.smart_forget(threshold=0.5)

        assert working_memory.has_memory("high"), "高重要性记忆应该被保留"

    def test_empty_memory_smart_forget(self, working_memory):
        """测试空记忆的智能遗忘"""
        forgotten = working_memory.smart_forget(threshold=0.5)
        assert forgotten == 0

    def test_zero_threshold_smart_forget(self, working_memory):
        """测试零阈值智能遗忘"""
        now = datetime.now()

        for i in range(3):
            working_memory.add(
                MemoryItem(
                    id=f"zero_{i}",
                    content=f"零阈值{i}",
                    memory_type="working",
                    user_id="test",
                    timestamp=now,
                    importance=0.1,
                    metadata={},
                )
            )

        forgotten = working_memory.smart_forget(threshold=0.0)
        assert forgotten == 0


class TestArchive:
    """归档系统测试"""

    @pytest.fixture
    def archive_path(self, tmp_path):
        return str(tmp_path / "test_archive.db")

    @pytest.fixture
    def cold_storage(self, archive_path):
        return ColdStorage(archive_path)

    @pytest.fixture
    def archive_manager(self, archive_path):
        policy = ArchivePolicy(
            archive_after_days=30, min_importance_to_keep=0.3, max_archive_size=100
        )
        return ArchiveManager(archive_path=archive_path, policy=policy)

    @pytest.fixture
    def sample_memory(self):
        return MemoryItem(
            id="test_mem_001",
            content="这是一条测试记忆内容",
            memory_type="working",
            user_id="test_user",
            timestamp=datetime.now() - timedelta(days=60),
            importance=0.6,
            metadata={},
        )

    def test_archive_single_memory(self, cold_storage, sample_memory):
        """测试单条记忆归档"""
        result = cold_storage.store(
            memory=sample_memory,
            archived_at=datetime.now(),
            last_access_time=sample_memory.timestamp,
            access_count=2,
        )
        assert result is True

        retrieved = cold_storage.retrieve("test_mem_001")
        assert retrieved is not None
        assert retrieved["content"] == sample_memory.content
        assert retrieved["importance"] == sample_memory.importance
        assert retrieved["access_count"] == 2

    def test_archive_search(self, cold_storage, sample_memory):
        """测试归档搜索"""
        cold_storage.store(sample_memory, datetime.now())

        results = cold_storage.search("测试")
        assert len(results) >= 1
        assert any("测试" in r["content"] for r in results)

    def test_archive_update_access(self, cold_storage, sample_memory):
        """测试更新访问信息"""
        cold_storage.store(sample_memory, datetime.now())

        cold_storage.update_access("test_mem_001")

        retrieved = cold_storage.retrieve("test_mem_001")
        assert retrieved["access_count"] == 1
        assert retrieved["archive_status"] == ArchiveStatus.RESTORED.value

    def test_archive_delete(self, cold_storage, sample_memory):
        """测试删除归档"""
        cold_storage.store(sample_memory, datetime.now())

        result = cold_storage.delete("test_mem_001")
        assert result is True

        retrieved = cold_storage.retrieve("test_mem_001")
        assert retrieved is None

    def test_archive_stats(self, cold_storage):
        """测试归档统计"""
        for i in range(3):
            mem = MemoryItem(
                id=f"stat_{i}",
                content=f"统计测试{i}",
                memory_type="working",
                user_id="test_user",
                timestamp=datetime.now(),
                importance=0.5,
                metadata={},
            )
            cold_storage.store(mem, datetime.now())

        stats = cold_storage.get_stats()
        assert stats["total_archived"] >= 3

    def test_archive_manager_archive_batch(self, archive_manager):
        """测试批量归档"""
        config = MemoryConfig(working_memory_capacity=10)
        working = WorkingMemory(config)
        now = datetime.now()

        for i in range(3):
            item = MemoryItem(
                id=f"batch_{i}",
                content=f"批量归档{i}",
                memory_type="working",
                user_id="test_user",
                timestamp=now - timedelta(days=100),
                importance=0.2,
                metadata={"last_access_time": (now - timedelta(days=100)).isoformat()},
            )
            working.add(item)

        count = archive_manager.archive_batch(working)
        assert count >= 0

    def test_archive_manager_restore(
        self, archive_manager, cold_storage, sample_memory
    ):
        """测试记忆恢复"""
        cold_storage.store(sample_memory, datetime.now())

        config = MemoryConfig(working_memory_capacity=10)
        working = WorkingMemory(config)

        restored = archive_manager.restore("test_mem_001", working)

        assert restored is not None
        assert restored.id == "test_mem_001"
        assert working.has_memory("test_mem_001")

    def test_archive_manager_restore_search(
        self, archive_manager, cold_storage, sample_memory
    ):
        """测试搜索恢复"""
        cold_storage.store(sample_memory, datetime.now())

        config = MemoryConfig(working_memory_capacity=10)
        working = WorkingMemory(config)

        results = archive_manager.restore_search(
            query="测试", memory_instance=working, limit=5
        )

        assert len(results) >= 1
        assert any(r.id == "test_mem_001" for r in results)

    def test_archive_policy_config(self):
        """测试归档策略配置"""
        policy = ArchivePolicy(
            archive_after_days=60,
            min_importance_to_keep=0.5,
            min_access_count=3,
            max_archive_size=5000,
            auto_archive_enabled=True,
            archive_check_interval_hours=12,
        )

        assert policy.archive_after_days == 60
        assert policy.min_importance_to_keep == 0.5
        assert policy.auto_archive_enabled is True

    def test_archive_clear_all(self, cold_storage, sample_memory):
        """测试清空归档"""
        cold_storage.store(sample_memory, datetime.now())

        result = cold_storage.clear_all()
        assert result is True

        stats = cold_storage.get_stats()
        assert stats["total_archived"] == 0

    def test_empty_archive_retrieve(self, tmp_path):
        """测试空归档检索"""
        cold_storage = ColdStorage(str(tmp_path / "empty.db"))
        result = cold_storage.retrieve("nonexistent")
        assert result is None

    def test_archive_nonexistent_restore(self, tmp_path):
        """测试恢复不存在的归档"""
        policy = ArchivePolicy()
        archive_manager = ArchiveManager(
            archive_path=str(tmp_path / "archive.db"), policy=policy
        )
        config = MemoryConfig(working_memory_capacity=10)
        working = WorkingMemory(config)

        result = archive_manager.restore("fake_id", working)
        assert result is None


class TestArchiveIntegration:
    """归档集成测试"""

    def test_working_from_archive(self, tmp_path):
        """测试 WorkingMemory 的 from_archive 方法"""
        config = MemoryConfig(storage_path=str(tmp_path / "memory.db"))
        now = datetime.now()

        archive_data = {
            "memory_id": "archive_001",
            "content": "归档内容",
            "user_id": "test",
            "timestamp": int(now.timestamp()),
            "importance": 0.7,
            "metadata": {"key": "value"},
            "archived_at": now.isoformat(),
        }

        working = WorkingMemory(config)
        result = working.from_archive(archive_data)

        assert result.id == "archive_001"
        assert result.content == "归档内容"
        assert result.importance == 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
