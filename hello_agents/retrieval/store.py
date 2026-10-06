"""SQLite 文档存储与 BM25 关键词检索，无模型或向量服务依赖。"""

from collections import Counter
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import hashlib
import math
from pathlib import Path
import sqlite3
from hello_agents.storage import guard_schema
import uuid
from typing import Any, Dict, Iterator, List, Optional

from ..context.types import ContextPacket
from ..context.text import lexical_terms


@dataclass(frozen=True)
class RetrievalResult:
    """字符区间为 Python 字符串的 [start, end)，相对于导入的完整原文。"""

    chunk_id: str
    document_id: str
    source: str
    version: str
    content: str
    start: int
    end: int
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_context_packet(self) -> ContextPacket:
        return ContextPacket(
            content=self.content,
            metadata={
                "type": "retrieval",
                "id": self.chunk_id,
                "source": self.source,
                "version": self.version,
                "start": self.start,
                "end": self.end,
            },
        )


@dataclass(frozen=True)
class DocumentResult:
    """不可变版本的完整原文；active 表示它是否仍参与当前检索。"""

    document_id: str
    source: str
    version: str
    content: str
    active: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_context_packet(self) -> ContextPacket:
        return ContextPacket(
            self.content,
            metadata={
                "type": "retrieval",
                "id": f"{self.document_id}@{self.version}",
                "source": self.source,
                "version": self.version,
                "active": self.active,
            },
        )


class RAGStore:
    """持久化文本及版本，检索当前版本，允许按片段标识回读旧版本。

    每次操作创建并关闭连接，支持从不同线程或新进程重新打开。
    此实现逐次扫描本地片段计算 BM25，适用于小型教学资料库。
    """

    def __init__(self, path: str):
        if str(path) == ":memory:":
            raise ValueError("请提供持久化文件路径，不支持 :memory:")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS rag_documents (
                    document_id TEXT NOT NULL, version TEXT NOT NULL,
                    source TEXT NOT NULL, content TEXT NOT NULL,
                    digest TEXT NOT NULL, active INTEGER NOT NULL,
                    PRIMARY KEY(document_id, version));
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
                    version TEXT NOT NULL, start INTEGER NOT NULL,
                    end INTEGER NOT NULL, content TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS rag_chunk_document
                    ON rag_chunks(document_id, version);
                CREATE TABLE IF NOT EXISTS rag_metadata (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """
            )
            db.execute(
                "INSERT OR IGNORE INTO rag_metadata VALUES('namespace',?)",
                (str(uuid.uuid4()),),
            )
            db.execute("INSERT OR IGNORE INTO rag_metadata VALUES('revision','0')")

    @property
    def namespace(self) -> str:
        """持久化资料库标识，供外部索引隔离不同资料库。"""
        with self._connect() as db:
            return db.execute(
                "SELECT value FROM rag_metadata WHERE key='namespace'"
            ).fetchone()[0]

    @property
    def revision(self) -> int:
        """当前检索集合的修订号；新增版本或撤下文档后递增。"""
        with self._connect() as db:
            return int(
                db.execute(
                    "SELECT value FROM rag_metadata WHERE key='revision'"
                ).fetchone()[0]
            )

    @staticmethod
    def _advance_revision(db: sqlite3.Connection) -> None:
        db.execute(
            "UPDATE rag_metadata SET value=CAST(value AS INTEGER)+1 WHERE key='revision'"
        )

    def snapshot(self) -> tuple[int, List[RetrievalResult]]:
        """在同一读事务中取得修订号和全部当前片段，用于构建外部索引。"""
        with self._connect() as db:
            db.execute("BEGIN")
            revision = int(
                db.execute(
                    "SELECT value FROM rag_metadata WHERE key='revision'"
                ).fetchone()[0]
            )
            rows = db.execute(
                """SELECT c.chunk_id,c.document_id,d.source,c.version,c.content,c.start,c.end
                FROM rag_chunks c JOIN rag_documents d
                ON c.document_id=d.document_id AND c.version=d.version
                WHERE d.active=1 ORDER BY c.chunk_id"""
            ).fetchall()
        return revision, [self._result(row) for row in rows]

    def deactivate_document(self, document_id: str) -> bool:
        """撤下文档的当前版本，保留历史原文以便审计回读。"""
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("document_id 必须是非空字符串")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute(
                "UPDATE rag_documents SET active=0 WHERE document_id=? AND active=1",
                (document_id,),
            ).rowcount
            if changed:
                self._advance_revision(db)
        return bool(changed)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(str(self.path), timeout=10)
        db.row_factory = sqlite3.Row
        try:
            guard_schema(db, "rag")
            with db:
                yield db
        finally:
            db.close()

    def add_document(
        self,
        text: str,
        source: str,
        version: str = "1",
        document_id: Optional[str] = None,
        chunk_size: int = 600,
        overlap: int = 80,
    ) -> str:
        """导入原文；同标识同版本只接受相同原文，新版本替代检索中的旧版本。

        Args:
            text: 完整原文，保存时不做空白归一化。
            source: 可核对的来源，如 URL 或宿主定义的资料标识。
            version: 宿主提供的版本标识，不按字符串大小推断时间先后。
            document_id: 稳定文档标识，默认由 source 的 SHA-256 生成。
            chunk_size: 按 Python 字符数划分的片段长度。
            overlap: 相邻片段重叠字符数。
        """
        if not all(isinstance(v, str) and v.strip() for v in (text, source, version)):
            raise ValueError("text、source、version 必须是非空字符串")
        if (
            type(chunk_size) is not int
            or type(overlap) is not int
            or chunk_size <= 0
            or not 0 <= overlap < chunk_size
        ):
            raise ValueError("需要 chunk_size > 0 且 0 <= overlap < chunk_size")
        if document_id is None:
            document_id = hashlib.sha256(source.encode()).hexdigest()[:24]
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("document_id 必须是非空字符串")
        digest = hashlib.sha256(text.encode()).hexdigest()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT digest,source FROM rag_documents WHERE document_id=? AND version=?",
                (document_id, version),
            ).fetchone()
            if old:
                if old["digest"] != digest or old["source"] != source:
                    raise ValueError("同一文档版本的原文或来源不可变，请使用新版本")
                return document_id
            db.execute(
                "UPDATE rag_documents SET active=0 WHERE document_id=?", (document_id,)
            )
            db.execute(
                "INSERT INTO rag_documents VALUES(?,?,?,?,?,1)",
                (document_id, version, source, text, digest),
            )
            for start in range(0, len(text), chunk_size - overlap):
                end = min(start + chunk_size, len(text))
                chunk_id = hashlib.sha256(
                    f"{document_id}\0{version}\0{start}\0{end}".encode()
                ).hexdigest()[:32]
                db.execute(
                    "INSERT INTO rag_chunks VALUES(?,?,?,?,?,?)",
                    (chunk_id, document_id, version, start, end, text[start:end]),
                )
                if end == len(text):
                    break
            self._advance_revision(db)
        return document_id

    @staticmethod
    def _result(row: sqlite3.Row, score: float = 0.0) -> RetrievalResult:
        return RetrievalResult(**dict(row), score=score)

    def search(self, query: str, limit: int = 5) -> List[RetrievalResult]:
        """对当前版本进行 BM25 排序；无词项重叠时返回空列表。"""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query 必须是非空字符串")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit 必须是 1 到 100 的整数")
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT c.chunk_id,c.document_id,d.source,c.version,c.content,c.start,c.end
                FROM rag_chunks c JOIN rag_documents d
                ON c.document_id=d.document_id AND c.version=d.version
                WHERE d.active=1 ORDER BY c.chunk_id
            """
            ).fetchall()
        if not rows:
            return []
        counters = [Counter(lexical_terms(row["content"])) for row in rows]
        lengths = [sum(counts.values()) for counts in counters]
        average = sum(lengths) / len(rows) or 1
        query_terms = set(lexical_terms(query))
        frequencies = {term: sum(term in c for c in counters) for term in query_terms}
        ranked = []
        for row, counts, length in zip(rows, counters, lengths):
            score = 0.0
            for term in query_terms:
                tf = counts.get(term, 0)
                if tf:
                    df = frequencies[term]
                    idf = math.log(1 + (len(rows) - df + 0.5) / (df + 0.5))
                    score += (
                        idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * length / average))
                    )
            if score > 0:
                ranked.append(self._result(row, score))
        return sorted(ranked, key=lambda r: (-r.score, r.chunk_id))[:limit]

    def read_chunk(self, chunk_id: str) -> RetrievalResult:
        """按稳定标识回读确切版本的片段，缺失时抛出 KeyError。"""
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            raise ValueError("chunk_id 必须是非空字符串")
        with self._connect() as db:
            row = db.execute(
                """
                SELECT c.chunk_id,c.document_id,d.source,c.version,c.content,c.start,c.end
                FROM rag_chunks c JOIN rag_documents d
                ON c.document_id=d.document_id AND c.version=d.version
                WHERE c.chunk_id=?
            """,
                (chunk_id,),
            ).fetchone()
        if row is None:
            raise KeyError(chunk_id)
        return self._result(row)

    def read_document(
        self, document_id: str, version: Optional[str] = None
    ) -> DocumentResult:
        """回读完整原文。省略 version 时读当前版本；指定时绝不跳到新版。"""
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError("document_id 必须是非空字符串")
        if version is not None and (
            not isinstance(version, str) or not version.strip()
        ):
            raise ValueError("version 必须是非空字符串或 None")
        with self._connect() as db:
            sql = "SELECT document_id,source,version,content,active FROM rag_documents WHERE document_id=?"
            params = [document_id]
            if version is None:
                sql += " AND active=1"
            else:
                sql += " AND version=?"
                params.append(version)
            row = db.execute(sql, params).fetchone()
        if row is None:
            raise KeyError((document_id, version))
        return DocumentResult(**{**dict(row), "active": bool(row["active"])})
