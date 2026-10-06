"""SQLite 任务队列：原子领取、租约续期、完成时的持有权校验与重试。"""

from contextlib import contextmanager
import json
import math
from pathlib import Path
import sqlite3
from hello_agents.storage import guard_schema
import time
from uuid import uuid4

from .types import Job, JobLease, LeaseLost, JobConflict


def _positive(value, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be positive and finite")


class JobQueue:
    """单机多进程持久化队列，采用至少一次投递语义。

    任务函数由工作进程注册，不从任务载荷中反序列化。
    命名空间由宿主选择，不承担终端用户的身份认证。
    """

    STATUSES = {"queued", "running", "succeeded", "failed", "cancelled"}

    def __init__(
        self,
        path: str,
        *,
        namespace: str = "default",
        max_payload_bytes: int = 1048576,
        clock=time.time,
    ):
        if str(path) == ":memory:":
            raise ValueError("Use a persistent SQLite file")
        if not isinstance(namespace, str) or not namespace.strip():
            raise ValueError("namespace must be nonempty")
        if type(max_payload_bytes) is not int or max_payload_bytes <= 0:
            raise ValueError("max_payload_bytes must be positive")
        self.path, self.namespace = Path(path), namespace
        self.max_payload_bytes, self.clock = max_payload_bytes, clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS background_jobs (
                    job_id TEXT PRIMARY KEY, namespace TEXT NOT NULL, task TEXT NOT NULL,
                    payload TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL, available_at REAL NOT NULL,
                    lease_until REAL, worker_id TEXT, lease_token TEXT,
                    result TEXT, error TEXT, idempotency_key TEXT,
                    created_at REAL NOT NULL, updated_at REAL NOT NULL,
                    UNIQUE(namespace,idempotency_key));
                CREATE INDEX IF NOT EXISTS job_ready ON background_jobs(namespace,status,available_at);
            """
            )
            db.execute("BEGIN IMMEDIATE")
            if "progress" not in {
                row[1] for row in db.execute("PRAGMA table_info(background_jobs)")
            }:
                db.execute("ALTER TABLE background_jobs ADD COLUMN progress TEXT")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(str(self.path), timeout=10)
        db.row_factory = sqlite3.Row
        try:
            guard_schema(db, "jobs")
            with db:
                yield db
        finally:
            db.close()

    def _json(self, value):
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
        if len(encoded.encode("utf-8")) > self.max_payload_bytes:
            raise ValueError(
                "Job payload/result too large; store artifacts and pass their identifiers"
            )
        return encoded

    @staticmethod
    def _job(row):
        value = dict(row)
        value["payload"] = json.loads(value["payload"])
        value["result"] = (
            json.loads(value["result"]) if value["result"] is not None else None
        )
        value["progress"] = (
            json.loads(value["progress"]) if value["progress"] is not None else None
        )
        return Job(**value)

    def _get(self, db, job_id):
        row = db.execute(
            "SELECT * FROM background_jobs WHERE namespace=? AND job_id=?",
            (self.namespace, job_id),
        ).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._job(row)

    def get(self, job_id: str):
        with self._connect() as db:
            return self._get(db, job_id)

    def list(self, *, status=None, limit=20):
        if status is not None and status not in self.STATUSES:
            raise ValueError("Unknown job status")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM background_jobs WHERE namespace=? "
                + ("AND status=? " if status else "")
                + "ORDER BY created_at DESC,job_id LIMIT ?",
                (self.namespace, status, limit) if status else (self.namespace, limit),
            ).fetchall()
        return [self._job(row) for row in rows]

    def submit(
        self, task: str, payload: dict, *, idempotency_key=None, max_attempts=3, delay=0
    ):
        if (
            not isinstance(task, str)
            or not task.strip()
            or not isinstance(payload, dict)
        ):
            raise ValueError("task must be nonempty and payload must be an object")
        if idempotency_key is not None and (
            not isinstance(idempotency_key, str) or not idempotency_key
        ):
            raise ValueError("idempotency_key must be nonempty or None")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 100:
            raise ValueError("max_attempts must be 1..100")
        if (
            isinstance(delay, bool)
            or not isinstance(delay, (int, float))
            or not math.isfinite(delay)
            or delay < 0
        ):
            raise ValueError("delay must be nonnegative and finite")
        encoded, now = self._json(payload), self.clock()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if idempotency_key is not None:
                old = db.execute(
                    "SELECT * FROM background_jobs WHERE namespace=? AND idempotency_key=?",
                    (self.namespace, idempotency_key),
                ).fetchone()
                if old:
                    if old["task"] != task or old["payload"] != encoded:
                        raise JobConflict(
                            "Idempotency key identifies a different task or payload"
                        )
                    return self._job(old)
            job_id = uuid4().hex
            db.execute(
                "INSERT INTO background_jobs VALUES(?,?,?,?,?,0,?,?,NULL,NULL,NULL,NULL,NULL,?,?,?,NULL)",
                (
                    job_id,
                    self.namespace,
                    task,
                    encoded,
                    "queued",
                    max_attempts,
                    now + delay,
                    idempotency_key,
                    now,
                    now,
                ),
            )
            return self._get(db, job_id)

    def claim(self, worker_id: str, *, lease_seconds=30, tasks=None):
        _positive(lease_seconds, "lease_seconds")
        if not isinstance(worker_id, str) or not worker_id.strip():
            raise ValueError("worker_id must be nonempty")
        if tasks is not None:
            if isinstance(tasks, str):
                raise TypeError("tasks must be a collection")
            tasks = tuple(tasks)
            if not tasks:
                return None
            if any(not isinstance(t, str) or not t for t in tasks):
                raise ValueError("tasks must contain nonempty strings")
        now = self.clock()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute(
                "UPDATE background_jobs SET status='failed',error='Lease expired after final attempt',"
                "lease_token=NULL,lease_until=NULL,worker_id=NULL,updated_at=? "
                "WHERE namespace=? AND status='running' AND lease_until<=? AND attempts>=max_attempts",
                (now, self.namespace, now),
            )
            query = (
                "SELECT job_id FROM background_jobs WHERE namespace=? AND attempts<max_attempts AND "
                "((status='queued' AND available_at<=?) OR (status='running' AND lease_until<=?))"
            )
            args = [self.namespace, now, now]
            if tasks:
                query += " AND task IN (" + ",".join("?" for _ in tasks) + ")"
                args.extend(tasks)
            row = db.execute(
                query + " ORDER BY available_at,created_at,job_id LIMIT 1", args
            ).fetchone()
            if row is None:
                return None
            token = uuid4().hex
            db.execute(
                "UPDATE background_jobs SET status='running',attempts=attempts+1,worker_id=?,"
                "lease_token=?,lease_until=?,updated_at=? WHERE job_id=? AND namespace=?",
                (worker_id, token, now + lease_seconds, now, row[0], self.namespace),
            )
            return JobLease(self._get(db, row[0]), token)

    def _owned(self, db, lease):
        job = self._get(db, lease.job.job_id)
        if (
            job.status != "running"
            or job.lease_token != lease.token
            or job.lease_until is None
            or job.lease_until <= self.clock()
        ):
            raise LeaseLost("Job was cancelled, expired or claimed by another worker")
        return job

    def check(self, lease):
        with self._connect() as db:
            return self._owned(db, lease)

    def heartbeat(self, lease, *, lease_seconds=30):
        _positive(lease_seconds, "lease_seconds")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._owned(db, lease)
            now = self.clock()
            db.execute(
                "UPDATE background_jobs SET lease_until=?,updated_at=? WHERE job_id=? AND namespace=?",
                (now + lease_seconds, now, job.job_id, self.namespace),
            )

    def complete(self, lease, result=None):
        encoded = self._json(result)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._owned(db, lease)
            db.execute(
                "UPDATE background_jobs SET status='succeeded',result=?,error=NULL,lease_token=NULL,"
                "lease_until=NULL,worker_id=NULL,updated_at=? WHERE job_id=? AND namespace=?",
                (encoded, self.clock(), job.job_id, self.namespace),
            )
            return self._get(db, job.job_id)

    def report_progress(self, lease, progress):
        """仅在当前执行仍持有租约时，保存大小受限的 JSON 进度。"""
        encoded = self._json(progress)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._owned(db, lease)
            db.execute(
                "UPDATE background_jobs SET progress=?,updated_at=? WHERE job_id=? AND namespace=?",
                (encoded, self.clock(), job.job_id, self.namespace),
            )

    def fail(self, lease, error: str, *, retry_delay=1):
        if not isinstance(error, str):
            raise TypeError("error must be str")
        if (
            isinstance(retry_delay, bool)
            or not isinstance(retry_delay, (int, float))
            or not math.isfinite(retry_delay)
            or retry_delay < 0
        ):
            raise ValueError("retry_delay must be finite and nonnegative")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._owned(db, lease)
            now = self.clock()
            status = "queued" if job.attempts < job.max_attempts else "failed"
            db.execute(
                "UPDATE background_jobs SET status=?,error=?,available_at=?,lease_token=NULL,"
                "lease_until=NULL,worker_id=NULL,updated_at=? WHERE job_id=? AND namespace=?",
                (
                    status,
                    error[:2000],
                    now + retry_delay,
                    now,
                    job.job_id,
                    self.namespace,
                ),
            )
            return self._get(db, job.job_id)

    def cancel(self, job_id: str):
        """撤销任务持有权；正在执行的外部操作仍需协作式取消。"""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._get(db, job_id)
            if job.status in {"queued", "running"}:
                db.execute(
                    "UPDATE background_jobs SET status='cancelled',lease_token=NULL,lease_until=NULL,"
                    "worker_id=NULL,updated_at=? WHERE job_id=? AND namespace=?",
                    (self.clock(), job_id, self.namespace),
                )
            return self._get(db, job_id)
