"""经 Schema 校验、带修订版本的用户画像；身份与写入来源由宿主提供。"""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from hello_agents.storage import guard_schema
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, ConfigDict

from ..context.types import ContextPacket


class ProfileModel(BaseModel):
    """通过子类定义业务字段，拒绝未知字段与隐式类型转换。"""

    model_config = ConfigDict(extra="forbid", strict=True, validate_default=True)


class ProfileConflict(ValueError):
    """调用方再次更新前，必须重新读取最新画像。"""


@dataclass(frozen=True)
class ProfileSnapshot:
    user_id: str
    namespace: str
    revision: int
    data: Dict[str, Any]
    sources: Dict[str, str]
    status: str
    updated_at: str

    def to_context_packet(self, required: bool = True) -> ContextPacket:
        if self.status != "active":
            raise ValueError("Only active profiles can enter context")
        return ContextPacket(
            content=json.dumps(self.data, ensure_ascii=False, sort_keys=True),
            metadata={
                "type": "related_memory",
                "id": f"profile:{self.namespace}",
                "source": dict(self.sources),
                "revision": self.revision,
                "required": required,
            },
        )


class ProfileStore:
    """按用户与应用命名空间跨会话保存画像，写入时比较并交换版本。

    每次写入都保留审计快照。``forget`` 会使画像不再出现在
    当前读取结果中，但不抹除审计历史或已发送的消息。
    Schema 变更需要显式迁移数据，不能静默强制转换。
    """

    def __init__(
        self,
        path: str,
        *,
        user_id: str,
        namespace: str,
        schema: Type[ProfileModel],
        max_bytes: int = 16384,
    ):
        if not all(isinstance(s, str) and s.strip() for s in (user_id, namespace)):
            raise ValueError(
                "user_id and namespace must be nonempty host-provided strings"
            )
        if not isinstance(schema, type) or not issubclass(schema, ProfileModel):
            raise TypeError("schema must subclass ProfileModel")
        if (
            schema.model_config.get("extra") != "forbid"
            or not schema.model_config.get("strict")
            or not schema.model_config.get("validate_default")
        ):
            raise ValueError(
                "Profile schema must preserve strict=True, validate_default=True and extra='forbid'"
            )
        if type(max_bytes) is not int or max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        if str(path) == ":memory:":
            raise ValueError("Use a persistent SQLite file")
        self.path, self.user_id, self.namespace = Path(path), user_id, namespace
        self.schema, self.max_bytes = schema, max_bytes
        self.schema_id = hashlib.sha256(
            json.dumps(schema.model_json_schema(), sort_keys=True).encode()
        ).hexdigest()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS profiles (
                user_id TEXT, namespace TEXT, revision INTEGER, schema_id TEXT,
                data TEXT, sources TEXT, status TEXT, updated_at TEXT,
                PRIMARY KEY(user_id, namespace, revision))"""
            )

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(str(self.path), timeout=10)
        db.row_factory = sqlite3.Row
        try:
            guard_schema(db, "profiles")
            with db:
                yield db
        finally:
            db.close()

    def _latest(self, db):
        return db.execute(
            "SELECT * FROM profiles WHERE user_id=? AND namespace=? "
            "ORDER BY revision DESC LIMIT 1",
            (self.user_id, self.namespace),
        ).fetchone()

    def _snapshot(self, row):
        if row["schema_id"] != self.schema_id:
            raise ValueError(
                "Profile schema changed; migrate the stored profile explicitly"
            )
        return ProfileSnapshot(
            self.user_id,
            self.namespace,
            row["revision"],
            json.loads(row["data"]),
            json.loads(row["sources"]),
            row["status"],
            row["updated_at"],
        )

    def get(self, *, include_inactive: bool = False) -> Optional[ProfileSnapshot]:
        with self._connect() as db:
            row = self._latest(db)
        snapshot = self._snapshot(row) if row else None
        return (
            snapshot
            if snapshot and (include_inactive or snapshot.status == "active")
            else None
        )

    def history(self, limit: int = 20):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM profiles WHERE user_id=? AND namespace=? "
                "ORDER BY revision DESC LIMIT ?",
                (self.user_id, self.namespace, limit),
            ).fetchall()
        return [self._snapshot(row) for row in rows]

    def _write(self, data, source, expected_revision, *, patch=False, forget=False):
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source must identify the host's evidence for this update")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError(
                "expected_revision must be a nonnegative integer; 0 creates"
            )
        if not isinstance(data, dict):
            raise TypeError("Profile data must be an object")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._latest(db)
            old = self._snapshot(row) if row else None
            if (old.revision if old else 0) != expected_revision:
                raise ProfileConflict("Profile changed; reread before updating")
            if patch and (old is None or old.status != "active"):
                raise ValueError("Create an active profile with put before patching")
            # 持久化 JSON 对日期、枚举和元组的编码不同于其
            # 严格的 Python 类型表示；校验局部更新前先恢复字段类型。
            restored = (
                self.schema.model_validate_json(row["data"], strict=True).model_dump(
                    mode="python"
                )
                if patch
                else {}
            )
            merged = (restored | data) if patch else dict(data)
            if not forget:
                merged = self.schema.model_validate(merged, strict=True).model_dump(
                    mode="json"
                )
            encoded = json.dumps(merged, ensure_ascii=False, allow_nan=False)
            sources = dict(old.sources) if patch else {}
            sources.update({key: source for key in merged if not patch or key in data})
            # 由 Schema 生成的默认值也保留写入来源。
            for key in merged:
                sources.setdefault(key, source)
            if forget:
                sources = {"__forget__": source}
            raw_sources = json.dumps(sources, ensure_ascii=False)
            if len((encoded + raw_sources).encode("utf-8")) > self.max_bytes:
                raise ValueError(
                    "Profile exceeds max_bytes; store large episodes separately"
                )
            now = datetime.now(timezone.utc).isoformat()
            db.execute(
                "INSERT INTO profiles VALUES(?,?,?,?,?,?,?,?)",
                (
                    self.user_id,
                    self.namespace,
                    expected_revision + 1,
                    self.schema_id,
                    encoded,
                    raw_sources,
                    "forgotten" if forget else "active",
                    now,
                ),
            )
            return self._snapshot(self._latest(db))

    def put(self, data: Dict[str, Any], *, source: str, expected_revision: int):
        """替换完整画像；修订号为 0 时创建首份快照。"""
        return self._write(data, source, expected_revision)

    def patch(self, changes: Dict[str, Any], *, source: str, expected_revision: int):
        """原子替换指定的顶层字段；嵌套对象整体替换。"""
        return self._write(changes, source, expected_revision, patch=True)

    def forget(self, *, source: str, expected_revision: int):
        return self._write({}, source, expected_revision, forget=True)

    def export_history(self):
        """原样导出已存快照，包括旧版应用 Schema 的标识。"""
        with self._connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM profiles WHERE user_id=? AND namespace=? ORDER BY revision",
                (self.user_id, self.namespace))]

    def purge_history(self, *, expected_revision: int):
        """删除画像内容与历史，仅保留空数据及防止旧版本覆盖的版本标记。"""
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValueError("expected_revision must be positive")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._latest(db)
            if row is None or row['revision'] != expected_revision:
                raise ProfileConflict("Profile changed; reread before purging")
            count = db.execute("DELETE FROM profiles WHERE user_id=? AND namespace=?",
                               (self.user_id, self.namespace)).rowcount
            db.execute("INSERT INTO profiles VALUES(?,?,?,?,?,?,?,?)", (
                self.user_id, self.namespace, expected_revision+1, self.schema_id,
                '{}', '{}', 'forgotten', datetime.now(timezone.utc).isoformat()))
            return count


class ProfileContextProvider:
    """每次调用前读取当前结构化偏好，确保修订后的内容及时生效。"""

    def __init__(self, store: ProfileStore, *, required: bool = True):
        self.store, self.required = store, required

    def get_context(self, query: str):
        snapshot = self.store.get()
        return [snapshot.to_context_packet(self.required)] if snapshot else []
