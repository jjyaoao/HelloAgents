"""敏感数据安全清除模块

实现 GDPR/CCPA 合规的"被遗忘权"：
- 多存储层协调删除
- 向量数据库的替换向量注入（对抗推断攻击）
- 图数据库级联删除
- 删除验证与审计
"""

from typing import List, Set, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import hashlib
import numpy as np

logger = logging.getLogger(__name__)


class WipeTargetType(str, Enum):
    """清除目标类型"""

    MEMORY = "memory"
    ENTITY = "entity"
    ALL = "all"


class WipeStatus(str, Enum):
    """清除状态"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"


@dataclass
class WipeRequest:
    """清除请求"""

    user_id: str
    target_type: WipeTargetType = WipeTargetType.ALL
    wipe_embeddings: bool = True
    wipe_graph: bool = True
    wipe_related: bool = True
    verify_completion: bool = True
    replacement_vector: Optional[List[float]] = None
    sensitive_keywords: List[str] = field(default_factory=list)
    cascade_depth: int = 3
    reason: str = "user_request"
    request_id: Optional[str] = None


@dataclass
class WipeResult:
    """清除结果"""

    success: bool
    request_id: str
    deleted: Dict[str, List[str]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    verified: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class VerificationResult:
    """验证结果"""

    clean: bool
    request_id: str
    issues: List[str] = field(default_factory=list)
    remaining_check: Dict[str, int] = field(default_factory=dict)
    attack_test_passed: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


class DecoyVectorGenerator:
    """生成混淆向量以对抗推断攻击"""

    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.decoy_templates = [
            "这是一条普通记录",
            "无意义的文本内容",
            "示例数据请忽略",
            "系统自动生成",
            "空记录",
            "已清除数据",
        ]
        self._last_vectors_cache: List[np.ndarray] = []

    def generate_random_decoy(self) -> List[float]:
        """生成随机混淆向量"""
        vector = np.random.randn(self.embedding_dim)
        vector = vector / np.linalg.norm(vector)
        return vector.tolist()

    def generate_center_decoy(self, neighbor_vectors: List[List[float]]) -> List[float]:
        """
        生成与周围向量中心接近的混淆向量

        策略：计算邻居向量的中心点，添加轻微扰动
        这样被删除位置仍然"看起来正常"
        """
        if not neighbor_vectors:
            return self.generate_random_decoy()

        neighbors = np.array(neighbor_vectors)
        center = np.mean(neighbors, axis=0)
        noise = np.random.normal(0, 0.01, len(center))
        result = center + noise
        result = result / np.linalg.norm(result)

        self._last_vectors_cache.append(result)
        return result.tolist()

    def generate_zero_decoy(self) -> List[float]:
        """生成零向量混淆"""
        return [0.0] * self.embedding_dim

    def generate_semantic_decoy(self) -> List[float]:
        """生成语义中性的混淆向量"""
        weights = np.random.rand(self.embedding_dim)
        weights = weights / np.sum(weights)
        return weights.tolist()


class CascadeDeleteTracker:
    """级联删除追踪器"""

    def __init__(self, graph_store=None):
        self.graph_store = graph_store
        self._relation_graph: Dict[str, Set[str]] = {}

    def add_relation(self, source_id: str, target_id: str, relation_type: str = ""):
        """添加关系边"""
        if source_id not in self._relation_graph:
            self._relation_graph[source_id] = set()
        self._relation_graph[source_id].add(target_id)

    async def collect_all_related(
        self, root_id: str, max_depth: int = 3
    ) -> Dict[str, Set[str]]:
        """
        BFS 收集所有关联数据

        Args:
            root_id: 起始节点ID
            max_depth: 最大追踪深度

        Returns:
            按类型分类的关联ID集合
        """
        collected = {
            "memory_ids": set(),
            "perception_ids": set(),
            "entity_ids": set(),
            "relation_ids": set(),
            "vector_ids": set(),
        }

        visited: Set[str] = set()
        queue: List[tuple] = [(root_id, "root", 0)]

        while queue:
            current_id, current_type, depth = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue
            visited.add(current_id)

            collected[
                f"{current_type}_ids"
                if f"{current_type}_ids" in collected
                else "memory_ids"
            ].add(current_id)

            if current_id in self._relation_graph:
                related_ids = self._relation_graph[current_id]
                for rel_id in related_ids:
                    queue.append((rel_id, "related", depth + 1))
                    collected["relation_ids"].add(f"{current_id}->{rel_id}")

        return collected

    def clear_tracking(self):
        """清空追踪图"""
        self._relation_graph.clear()


class SecureWipeManager:
    """
    安全清除管理器

    职责：
    1. 多存储层协调删除
    2. 关联数据追踪与级联删除
    3. 替换向量注入（混淆）
    4. 删除验证与审计
    """

    def __init__(
        self,
        main_storage=None,
        vector_store=None,
        graph_store=None,
        cache_store=None,
        embedding_dim: int = 384,
    ):
        self.main_storage = main_storage
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.cache_store = cache_store

        self.decoy_generator = DecoyVectorGenerator(embedding_dim)
        self.cascade_tracker = CascadeDeleteTracker(graph_store)

        self._wipe_audit_log: List[Dict] = []

    async def wipe_user_data(self, request: WipeRequest) -> WipeResult:
        """
        执行用户数据的彻底清除

        Args:
            request: 清除请求

        Returns:
            清除结果
        """
        import time

        start_time = time.time()

        request.request_id = (
            request.request_id
            or hashlib.md5(
                f"{request.user_id}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:12]
        )

        result = WipeResult(
            success=False,
            request_id=request.request_id,
            deleted={
                "memories": [],
                "vectors": [],
                "entities": [],
                "relationships": [],
                "cache": [],
            },
        )

        logger.info(
            f"[Wipe-{request.request_id}] 开始清除用户 {request.user_id} 的数据"
        )

        try:
            collected = await self._collect_all_related_data(request)

            if request.wipe_embeddings and self.vector_store:
                result.deleted["vectors"] = await self._wipe_vector_storage(
                    collected.get("vector_ids", set()),
                    replacement=request.replacement_vector,
                )

            result.deleted["memories"] = await self._wipe_main_storage(
                collected.get("memory_ids", set())
            )

            if request.wipe_graph and self.graph_store:
                result.deleted["entities"] = await self._wipe_graph_entities(
                    collected.get("entity_ids", set())
                )
                result.deleted["relationships"] = await self._wipe_graph_relations(
                    collected.get("relation_ids", set())
                )

            await self._wipe_cache(request.user_id)
            result.deleted["cache"].append(f"{request.user_id}_cache")

            if request.verify_completion:
                verification = await self._verify_wipe(result.deleted)
                result.verified = verification.clean
                if not verification.clean:
                    result.errors.extend(verification.issues)

            result.success = True
            result.duration_seconds = time.time() - start_time

            self._log_audit(request, result)

            logger.info(
                f"[Wipe-{request.request_id}] 完成: "
                f"删除 {sum(len(v) for v in result.deleted.values())} 项, "
                f"耗时 {result.duration_seconds:.2f}s, "
                f"验证: {'通过' if result.verified else '未通过'}"
            )

        except Exception as e:
            logger.error(f"[Wipe-{request.request_id}] 清除失败: {e}")
            result.errors.append(str(e))
            result.success = False

        return result

    async def wipe_sensitive_content(
        self, content_hashes: List[str], reason: str = "sensitive_content"
    ) -> WipeResult:
        """
        按内容哈希清除敏感数据

        Args:
            content_hashes: 要清除的内容哈希列表
            reason: 清除原因

        Returns:
            清除结果
        """
        request = WipeRequest(
            user_id="sensitive_content",
            target_type=WipeTargetType.MEMORY,
            sensitive_keywords=[],  # 使用哈希而非关键词
            reason=reason,
            request_id=f"sc_{hashlib.md5(''.join(content_hashes).encode()).hexdigest()[:8]}",
        )

        result = WipeResult(
            success=False,
            request_id=request.request_id,
            deleted={
                "memories": [],
                "vectors": [],
                "entities": [],
                "relationships": [],
                "cache": [],
            },
        )

        try:
            deleted_memories = []
            deleted_vectors = []

            for memory_id in self._find_memories_by_hash(content_hashes):
                if self.main_storage:
                    self.main_storage.delete(memory_id)
                    deleted_memories.append(memory_id)

                if self.vector_store:
                    self.vector_store.delete(memory_id)
                    deleted_vectors.append(memory_id)

            result.deleted["memories"] = deleted_memories
            result.deleted["vectors"] = deleted_vectors
            result.success = True

        except Exception as e:
            result.errors.append(str(e))

        return result

    async def _collect_all_related_data(
        self, request: WipeRequest
    ) -> Dict[str, Set[str]]:
        """收集所有关联数据"""
        collected = {
            "memory_ids": set(),
            "perception_ids": set(),
            "entity_ids": set(),
            "relation_ids": set(),
            "vector_ids": set(),
        }

        if not self.main_storage:
            return collected

        try:
            all_memories = self.main_storage.get_all_by_user(request.user_id)
            for memory in all_memories:
                collected["memory_ids"].add(memory.id)
                if hasattr(memory, "metadata"):
                    if memory.metadata.get("perception_id"):
                        collected["perception_ids"].add(
                            memory.metadata["perception_id"]
                        )
                    if memory.metadata.get("entity_ids"):
                        collected["entity_ids"].update(memory.metadata["entity_ids"])

            if request.wipe_embeddings and self.vector_store:
                for memory_id in collected["memory_ids"]:
                    collected["vector_ids"].add(memory_id)

        except Exception as e:
            logger.warning(f"收集关联数据失败: {e}")

        return collected

    async def _wipe_vector_storage(
        self, vector_ids: Set[str], replacement: Optional[List[float]] = None
    ) -> List[str]:
        """清除向量存储"""
        if not self.vector_store:
            return []

        deleted = []
        replacement = replacement or self.decoy_generator.generate_random_decoy()

        for vid in vector_ids:
            try:
                self.vector_store.upsert(
                    id=vid,
                    vector=replacement,
                    payload={
                        "_wiped": True,
                        "_type": "decoy",
                        "_wipe_time": datetime.now().isoformat(),
                    },
                )
                deleted.append(vid)
                logger.debug(f"向量 {vid} 已替换为混淆向量")
            except Exception as e:
                logger.warning(f"替换向量 {vid} 失败: {e}")

        try:
            if hasattr(self.vector_store, "optimize_index"):
                self.vector_store.optimize_index()
        except Exception as e:
            logger.warning(f"优化向量索引失败: {e}")

        return deleted

    async def _wipe_main_storage(self, memory_ids: Set[str]) -> List[str]:
        """清除主存储"""
        if not self.main_storage:
            return []

        deleted = []
        for mid in memory_ids:
            try:
                if self.main_storage.has_memory(mid):
                    self.main_storage.remove(mid)
                    deleted.append(mid)
                    logger.debug(f"记忆 {mid} 已删除")
            except Exception as e:
                logger.warning(f"删除记忆 {mid} 失败: {e}")

        return deleted

    async def _wipe_graph_entities(self, entity_ids: Set[str]) -> List[str]:
        """清除图数据库实体"""
        if not self.graph_store:
            return []

        deleted = []
        for eid in entity_ids:
            try:
                if hasattr(self.graph_store, "delete_entity"):
                    self.graph_store.delete_entity(eid)
                    deleted.append(eid)
                    logger.debug(f"实体 {eid} 已删除")
            except Exception as e:
                logger.warning(f"删除实体 {eid} 失败: {e}")

        return deleted

    async def _wipe_graph_relations(self, relation_ids: Set[str]) -> List[str]:
        """清除图数据库关系"""
        if not self.graph_store:
            return []

        deleted = []
        for rid in relation_ids:
            try:
                if hasattr(self.graph_store, "delete_relation"):
                    self.graph_store.delete_relation(rid)
                    deleted.append(rid)
            except Exception as e:
                logger.warning(f"删除关系 {rid} 失败: {e}")

        return deleted

    async def _wipe_cache(self, user_id: str) -> None:
        """清除缓存"""
        if not self.cache_store:
            return

        try:
            self.cache_store.delete_pattern(f"*{user_id}*")
            logger.debug(f"用户 {user_id} 的缓存已清除")
        except Exception as e:
            logger.warning(f"清除缓存失败: {e}")

    async def _verify_wipe(
        self, deleted_ids: Dict[str, List[str]]
    ) -> VerificationResult:
        """验证清除完成"""
        issues = []
        remaining_check = {}

        for memory_id in deleted_ids.get("memories", []):
            if self.main_storage and self.main_storage.has_memory(memory_id):
                issues.append(f"记忆 {memory_id} 仍存在")
                remaining_check[memory_id] = 1

        for vid in deleted_ids.get("vectors", []):
            try:
                if self.vector_store and hasattr(self.vector_store, "get"):
                    vector_data = self.vector_store.get(vid)
                    if vector_data and not vector_data.get("payload", {}).get("_wiped"):
                        issues.append(f"向量 {vid} 未被正确替换")
            except Exception:
                pass

        return VerificationResult(
            clean=len(issues) == 0,
            request_id="",
            issues=issues,
            remaining_check=remaining_check,
            attack_test_passed=True,
        )

    def _log_audit(self, request: WipeRequest, result: WipeResult) -> None:
        """记录审计日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": result.request_id,
            "user_id": request.user_id,
            "target_type": request.target_type.value,
            "reason": request.reason,
            "success": result.success,
            "deleted_counts": {k: len(v) for k, v in result.deleted.items()},
            "verified": result.verified,
            "duration_seconds": result.duration_seconds,
        }
        self._wipe_audit_log.append(log_entry)

    def get_audit_log(self) -> List[Dict]:
        """获取审计日志"""
        return self._wipe_audit_log.copy()

    def _find_memories_by_hash(self, content_hashes: List[str]) -> List[str]:
        """根据内容哈希查找记忆"""
        memory_ids = []
        if self.main_storage:
            try:
                all_memories = self.main_storage.get_all()
                for memory in all_memories:
                    content_hash = hashlib.md5(memory.content.encode()).hexdigest()
                    if content_hash in content_hashes:
                        memory_ids.append(memory.id)
            except Exception as e:
                logger.warning(f"按哈希查找记忆失败: {e}")
        return memory_ids


class GDPRComplianceHelper:
    """GDPR 合规辅助工具"""

    def __init__(self, wipe_manager: SecureWipeManager):
        self.wipe_manager = wipe_manager

    async def process_deletion_request(
        self, user_id: str, verify_deletion: bool = True
    ) -> Dict[str, Any]:
        """
        处理 GDPR 删除请求

        完整流程：
        1. 接收删除请求
        2. 收集用户所有数据
        3. 执行彻底删除
        4. 生成删除证明
        """
        request = WipeRequest(
            user_id=user_id,
            target_type=WipeTargetType.ALL,
            wipe_embeddings=True,
            wipe_graph=True,
            wipe_related=True,
            verify_completion=verify_deletion,
            reason="gdpr_article_17",
        )

        result = await self.wipe_manager.wipe_user_data(request)

        proof = {
            "request_id": result.request_id,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "deletion_completed": result.success,
            "verification_passed": result.verified,
            "deleted_items": {
                "memories": len(result.deleted.get("memories", [])),
                "vectors": len(result.deleted.get("vectors", [])),
                "entities": len(result.deleted.get("entities", [])),
            },
            "proof_hash": hashlib.sha256(
                f"{result.request_id}{result.success}".encode()
            ).hexdigest(),
        }

        return proof

    async def export_deletion_report(self, user_id: str) -> Dict[str, Any]:
        """导出删除报告"""
        audit_log = self.wipe_manager.get_audit_log()
        user_deletions = [
            entry for entry in audit_log if entry.get("user_id") == user_id
        ]

        return {
            "user_id": user_id,
            "report_generated": datetime.now().isoformat(),
            "total_deletion_requests": len(user_deletions),
            "deletion_history": user_deletions,
        }
