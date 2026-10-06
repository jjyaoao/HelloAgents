"""SQLite 记忆存储；声明与推断由 kind 区分，不自动认定内容为事实。"""

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from hello_agents.storage import guard_schema
from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4

from ..context.types import ContextPacket
from ..context.text import lexical_terms


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    user_id: str
    task_id: str
    content: str
    source: str
    kind: str
    status: str
    created_at: str
    updated_at: str
    supersedes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_context_packet(self, required: bool = False) -> ContextPacket:
        if self.status != "active":
            raise ValueError("只有有效记忆可以转换为上下文包")
        return ContextPacket(
            content=self.content,
            metadata={
                "type": "related_memory",
                "id": self.memory_id,
                "source": self.source,
                "kind": self.kind,
                "status": self.status,
                "required": required,
                "updated_at": self.updated_at,
            },
        )


class MemoryStore:
    """宿主创建一个实例绑定一个用户和任务；所有操作都带相同范围过滤。"""

    KINDS = {"preference", "fact", "episode", "inference", "procedure"}

    def __init__(self, path: str, user_id: str, task_id: str):
        if str(path) == ":memory:":
            raise ValueError("请提供持久化文件路径，不支持 :memory:")
        if not all(isinstance(v, str) and v.strip() for v in (user_id, task_id)):
            raise ValueError("user_id 和 task_id 必须由宿主提供非空值")
        self.path = Path(path)
        self.user_id = user_id
        self.task_id = task_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                    task_id TEXT NOT NULL, content TEXT NOT NULL, source TEXT NOT NULL,
                    kind TEXT NOT NULL, status TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    supersedes TEXT);
                CREATE INDEX IF NOT EXISTS memory_scope
                    ON memories(user_id,task_id,status);
                CREATE TABLE IF NOT EXISTS memory_namespaces (
                    user_id TEXT NOT NULL, task_id TEXT NOT NULL,
                    namespace TEXT NOT NULL, revision INTEGER NOT NULL,
                    PRIMARY KEY(user_id,task_id));
            """
            )
            db.execute(
                "INSERT OR IGNORE INTO memory_namespaces VALUES(?,?,?,0)",
                (user_id, task_id, uuid4().hex),
            )

    @property
    def namespace(self) -> str:
        with self._connect() as db:
            return db.execute(
                "SELECT namespace FROM memory_namespaces WHERE user_id=? AND task_id=?",
                (self.user_id, self.task_id),
            ).fetchone()[0]

    @property
    def revision(self) -> int:
        with self._connect() as db:
            return db.execute(
                "SELECT revision FROM memory_namespaces WHERE user_id=? AND task_id=?",
                (self.user_id, self.task_id),
            ).fetchone()[0]

    def _advance_revision(self, db):
        db.execute(
            "UPDATE memory_namespaces SET revision=revision+1 WHERE user_id=? AND task_id=?",
            (self.user_id, self.task_id),
        )

    def snapshot(self):
        """在同一 SQLite 快照中读取指定作用域的修订号与有效记录。"""
        with self._connect() as db:
            db.execute("BEGIN")
            revision = db.execute(
                "SELECT revision FROM memory_namespaces WHERE user_id=? AND task_id=?",
                (self.user_id, self.task_id),
            ).fetchone()[0]
            rows = db.execute(
                "SELECT * FROM memories WHERE user_id=? AND task_id=? AND status='active' ORDER BY memory_id",
                (self.user_id, self.task_id),
            ).fetchall()
        return revision, [MemoryRecord(**dict(row)) for row in rows]

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(str(self.path), timeout=10)
        db.row_factory = sqlite3.Row
        try:
            guard_schema(db, "memory")
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _validate(content: str, source: str, kind: str) -> None:
        if not all(isinstance(v, str) and v.strip() for v in (content, source)):
            raise ValueError("content 和 source 必须是非空字符串")
        if not isinstance(kind, str) or kind not in MemoryStore.KINDS:
            raise ValueError(f"kind 必须是 {sorted(MemoryStore.KINDS)} 之一")

    def _insert(
        self,
        db: sqlite3.Connection,
        content: str,
        source: str,
        kind: str,
        supersedes: Optional[str] = None,
    ) -> MemoryRecord:
        now = datetime.now(timezone.utc).isoformat()
        record = MemoryRecord(
            uuid4().hex,
            self.user_id,
            self.task_id,
            content,
            source,
            kind,
            "active",
            now,
            now,
            supersedes,
        )
        db.execute(
            "INSERT INTO memories VALUES(?,?,?,?,?,?,?,?,?,?)",
            tuple(asdict(record).values()),
        )
        self._advance_revision(db)
        return record

    def add(self, content: str, source: str, kind: str = "preference") -> MemoryRecord:
        """保存一条有来源的记录；source 是声明来源，不等于已经验证。"""
        self._validate(content, source, kind)
        with self._connect() as db:
            return self._insert(db, content, source, kind)

    def _get(self, db: sqlite3.Connection, memory_id: str) -> MemoryRecord:
        if not isinstance(memory_id, str) or not memory_id.strip():
            raise ValueError("memory_id 必须是非空字符串")
        row = db.execute(
            "SELECT * FROM memories WHERE memory_id=? AND user_id=? AND task_id=?",
            (memory_id, self.user_id, self.task_id),
        ).fetchone()
        if row is None:
            raise KeyError(memory_id)
        return MemoryRecord(**dict(row))

    def get(self, memory_id: str, include_inactive: bool = False) -> MemoryRecord:
        with self._connect() as db:
            record = self._get(db, memory_id)
        if record.status != "active" and not include_inactive:
            raise KeyError(memory_id)
        return record

    def search(self, query: str = "", limit: int = 10) -> List[MemoryRecord]:
        """仅返回当前范围的有效记录；空查询按更新时间倒序读取。"""
        if not isinstance(query, str):
            raise ValueError("query 必须是字符串")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit 必须是 1 到 100 的整数")
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM memories WHERE user_id=? AND task_id=? AND status='active' "
                "ORDER BY updated_at DESC,memory_id",
                (self.user_id, self.task_id),
            ).fetchall()
        records = [MemoryRecord(**dict(r)) for r in rows]
        terms = set(lexical_terms(query))
        if query.strip():
            scored = [(len(terms & set(lexical_terms(r.content))), r) for r in records]
            records = [
                r for score, r in sorted(scored, key=lambda x: -x[0]) if score > 0
            ]
        return records[:limit]

    def revise(self, memory_id: str, content: str, source: str) -> MemoryRecord:
        """原子地标记旧记录为 superseded 并追加替代记录；拒绝并发覆盖旧版本。"""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = self._get(db, memory_id)
            self._validate(content, source, old.kind)
            if old.status != "active":
                raise ValueError("只能修订有效记录，请先重新读取")
            db.execute(
                "UPDATE memories SET status='superseded',updated_at=? "
                "WHERE memory_id=? AND user_id=? AND task_id=?",
                (
                    datetime.now(timezone.utc).isoformat(),
                    memory_id,
                    self.user_id,
                    self.task_id,
                ),
            )
            return self._insert(db, content, source, old.kind, supersedes=memory_id)

    def export_records(self):
        """导出当前用户与任务作用域的全部记录，包括已撤回的历史。"""
        with self._connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM memories WHERE user_id=? AND task_id=? ORDER BY created_at,memory_id",
                (self.user_id, self.task_id))]

    def purge(self, *, expected_revision: int):
        """删除当前作用域的记录，保留版本标记，并使派生索引失效。

        操作前先停止写入，再单独同步或清理向量索引。这里只执行
        SQL 删除，不保证安全擦除磁盘页、日志或备份中的内容。
        """
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError("expected_revision must be nonnegative")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            revision = db.execute("SELECT revision FROM memory_namespaces WHERE user_id=? AND task_id=?",
                                  (self.user_id, self.task_id)).fetchone()[0]
            if revision != expected_revision:
                raise ValueError("Memory changed; reread before purging")
            count = db.execute("DELETE FROM memories WHERE user_id=? AND task_id=?",
                               (self.user_id, self.task_id)).rowcount
            self._advance_revision(db)
            return count

    def retract(self, memory_id: str) -> MemoryRecord:
        """撤回有效记录，保留历史；重复撤回同一条记录保持幂等。"""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = self._get(db, memory_id)
            if old.status == "superseded":
                raise ValueError("记录已被修订，请撤回当前版本")
            if old.status != "retracted":
                db.execute(
                    "UPDATE memories SET status='retracted',updated_at=? "
                    "WHERE memory_id=? AND user_id=? AND task_id=?",
                    (
                        datetime.now(timezone.utc).isoformat(),
                        memory_id,
                        self.user_id,
                        self.task_id,
                    ),
                )
                self._advance_revision(db)
            return self._get(db, memory_id)
