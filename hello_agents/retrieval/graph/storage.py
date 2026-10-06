"""保存不可变的已发布索引版本，以及可复用的成功模型响应。"""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from hello_agents.storage import guard_schema

from .types import GraphBuildConflict, GraphIntegrityError


class GraphStorage:
    def __init__(self, path, namespace):
        if str(path) == ":memory:":
            raise ValueError("GraphRAG requires a persistent path")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.assets = self.path.parent / (self.path.name + ".assets")
        with self.connect() as db:
            db.executescript(
                """
            CREATE TABLE IF NOT EXISTS graph_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS graph_cache(key TEXT PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS graph_generations(id TEXT PRIMARY KEY,revision INTEGER NOT NULL,
                config_id TEXT NOT NULL,payload TEXT NOT NULL);
            """
            )
            db.execute(
                "INSERT OR IGNORE INTO graph_metadata VALUES('namespace',?)",
                (namespace,),
            )
            if (
                db.execute(
                    "SELECT value FROM graph_metadata WHERE key='namespace'"
                ).fetchone()[0]
                != namespace
            ):
                raise GraphIntegrityError(
                    "Graph index belongs to a different canonical RAGStore"
                )

    @contextmanager
    def connect(self):
        db = sqlite3.connect(str(self.path), timeout=30)
        db.row_factory = sqlite3.Row
        try:
            guard_schema(db, "graph")
            with db:
                yield db
        finally:
            db.close()

    def get_cache(self, key):
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM graph_cache WHERE key=?", (key,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def prune(self, *, clear_cache=False):
        """删除数据库中的非活跃索引版本；执行前应停止图索引构建任务。

        保留当前活跃版本。外部资源与备份由
        宿主管理，本方法不会递归删除这些内容。
        """
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            active = db.execute("SELECT value FROM graph_metadata WHERE key='active'").fetchone()
            count = db.execute('DELETE FROM graph_generations WHERE id != ?', (active[0],)).rowcount if active else db.execute('DELETE FROM graph_generations').rowcount
            cached = db.execute('DELETE FROM graph_cache').rowcount if clear_cache else 0
            return {'generations_removed': count, 'cache_entries_removed': cached}

    def put_cache(self, key, payload):
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO graph_cache VALUES(?,?)",
                (key, json.dumps(payload, ensure_ascii=False, allow_nan=False)),
            )

    def active(self):
        with self.connect() as db:
            row = db.execute(
                "SELECT g.* FROM graph_generations g JOIN graph_metadata m ON g.id=m.value WHERE m.key='active'"
            ).fetchone()
        return dict(row) if row else None

    def publish(self, generation, revision, config_id, payload, *, expected_generation):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT value FROM graph_metadata WHERE key='active'"
            ).fetchone()
            if (old[0] if old else None) != expected_generation:
                raise GraphBuildConflict(
                    "Another build was published; retry to reuse the completed caches"
                )
            db.execute(
                "INSERT INTO graph_generations VALUES(?,?,?,?)",
                (
                    generation,
                    revision,
                    config_id,
                    json.dumps(payload, ensure_ascii=False, allow_nan=False),
                ),
            )
            db.execute(
                "INSERT INTO graph_metadata VALUES('active',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (generation,),
            )
