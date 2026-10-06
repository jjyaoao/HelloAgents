"""带可回读证据的局部关系遍历，不实现全局 GraphRAG。"""

from collections import deque
from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Dict, List

from ..context.types import ContextPacket
from .store import RAGStore, RetrievalResult


@dataclass(frozen=True)
class RelationResult:
    relation_id: str
    subject: str
    predicate: str
    object: str
    quote: str
    evidence: RetrievalResult
    depth: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_context_packet(self) -> ContextPacket:
        return ContextPacket(
            f"{self.subject} —{self.predicate}→ {self.object}\n来源原句：{self.quote}",
            metadata={
                "type": "relation",
                "id": self.relation_id,
                "source": self.evidence.source,
                "version": self.evidence.version,
                "chunk_id": self.evidence.chunk_id,
                "depth": self.depth,
            },
        )


class RelationStore:
    """在同一 RAGStore 数据库中保存人工/外部抽取的有向关系。

    入库要求 quote 确实存在于指定片段；这只验证来源位置，不证明
    三元组语义正确。宿主应审核关系。检索默认仅返回当前文档版本的边，
    原文更新使旧边立即退出查询，新边仍需重新抽取/导入。
    """

    def __init__(self, documents: RAGStore):
        self.documents = documents
        with documents._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS rag_relations (
                relation_id TEXT PRIMARY KEY, subject TEXT NOT NULL,
                predicate TEXT NOT NULL, object TEXT NOT NULL,
                chunk_id TEXT NOT NULL, quote TEXT NOT NULL)"""
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS relation_subject ON rag_relations(subject)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS relation_object ON rag_relations(object)"
            )

    def add(
        self, subject: str, predicate: str, object: str, chunk_id: str, quote: str
    ) -> str:
        values = (subject, predicate, object, chunk_id, quote)
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise ValueError("关系字段必须是非空字符串")
        evidence = self.documents.read_chunk(chunk_id)
        if quote not in evidence.content:
            raise ValueError("quote 必须是证据片段中的连续原文")
        relation_id = hashlib.sha256(
            json.dumps(values, ensure_ascii=False).encode()
        ).hexdigest()[:32]
        with self.documents._connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO rag_relations VALUES(?,?,?,?,?,?)",
                (relation_id, *values),
            )
        return relation_id

    def neighbors(
        self, entity: str, hops: int = 1, limit: int = 20, direction: str = "both"
    ) -> List[RelationResult]:
        """有界广度优先遍历；entity 为宿主统一过的精确实体标识。

        返回每条边的发现深度和原文证据，不声称返回一条已证明的因果路径。
        """
        if not isinstance(entity, str) or not entity.strip():
            raise ValueError("entity 必须是非空字符串")
        if type(hops) is not int or not 1 <= hops <= 3:
            raise ValueError("hops 必须是 1 到 3 的整数")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit 必须是 1 到 100 的整数")
        if direction not in ("both", "out", "in"):
            raise ValueError("direction 必须是 both、out 或 in")
        queue, visited, edges, results = deque([(entity, 0)]), {entity}, set(), []
        with self.documents._connect() as db:
            while queue and len(results) < limit:
                node, depth = queue.popleft()
                if depth >= hops:
                    continue
                where = {
                    "both": "(r.subject=? OR r.object=?)",
                    "out": "r.subject=?",
                    "in": "r.object=?",
                }[direction]
                params = (node, node) if direction == "both" else (node,)
                rows = db.execute(
                    f"""SELECT r.* FROM rag_relations r
                    JOIN rag_chunks c ON r.chunk_id=c.chunk_id
                    JOIN rag_documents d ON c.document_id=d.document_id AND c.version=d.version
                    WHERE d.active=1 AND {where} ORDER BY r.relation_id""",
                    params,
                ).fetchall()
                for row in rows:
                    if row["relation_id"] in edges:
                        continue
                    edges.add(row["relation_id"])
                    results.append(
                        RelationResult(
                            row["relation_id"],
                            row["subject"],
                            row["predicate"],
                            row["object"],
                            row["quote"],
                            self.documents.read_chunk(row["chunk_id"]),
                            depth + 1,
                        )
                    )
                    other = row["object"] if node == row["subject"] else row["subject"]
                    if other not in visited:
                        visited.add(other)
                        queue.append((other, depth + 1))
                    if len(results) >= limit:
                        break
        return results
