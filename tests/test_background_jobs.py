import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys

import pytest
import hello_agents
from hello_agents.background import JobQueue, JobWorker, JobConflict, LeaseLost


class Clock:
    value = 1000.0

    def __call__(self):
        return self.value


def test_idempotency_namespace_and_payload_snapshot(tmp_path):
    q = JobQueue(str(tmp_path / "jobs.db"), namespace="alice")
    payload = {"document": "A"}
    job = q.submit("index", payload, idempotency_key="a1")
    payload["document"] = "B"
    assert q.get(job.job_id).payload == {"document": "A"}
    assert (
        q.submit("index", {"document": "A"}, idempotency_key="a1").job_id == job.job_id
    )
    with pytest.raises(JobConflict):
        q.submit("index", payload, idempotency_key="a1")
    other = JobQueue(str(q.path), namespace="bob")
    with pytest.raises(KeyError):
        other.get(job.job_id)
    assert other.claim("worker") is None


def test_atomic_claim_competing_connections(tmp_path):
    q = JobQueue(str(tmp_path / "jobs.db"))
    for i in range(10):
        q.submit("index", {"i": i})

    def claim(i):
        return JobQueue(str(q.path)).claim(str(i))

    with ThreadPoolExecutor(8) as pool:
        leases = list(pool.map(claim, range(16)))
    ids = [lease.job.job_id for lease in leases if lease]
    assert len(ids) == len(set(ids)) == 10


def test_expired_lease_is_fenced_and_retry_budget_is_finite(tmp_path):
    clock = Clock()
    q = JobQueue(str(tmp_path / "jobs.db"), clock=clock)
    job = q.submit("index", {}, max_attempts=2)
    first = q.claim("old", lease_seconds=3)
    q.report_progress(first, {"processed": 4})
    clock.value += 4
    second = q.claim("new", lease_seconds=3)
    assert second.job.job_id == job.job_id and second.job.attempts == 2
    assert second.job.progress == {"processed": 4}
    with pytest.raises(LeaseLost):
        q.report_progress(first, {"processed": 99})
    with pytest.raises(LeaseLost):
        q.complete(first, {"stale": True})
    with pytest.raises(LeaseLost):
        q.heartbeat(first)
    clock.value += 4
    assert q.claim("third") is None
    assert q.get(job.job_id).status == "failed"


def test_cancel_revokes_running_owner_and_backoff(tmp_path):
    clock = Clock()
    q = JobQueue(str(tmp_path / "jobs.db"), clock=clock)
    job = q.submit("index", {})
    lease = q.claim("worker")
    q.fail(lease, "temporary", retry_delay=5)
    assert q.claim("worker") is None
    clock.value += 6
    retry = q.claim("worker")
    q.cancel(job.job_id)
    with pytest.raises(LeaseLost):
        q.complete(retry, "late")
    assert q.get(job.job_id).status == "cancelled"


def test_process_exit_leaves_recoverable_lease(tmp_path):
    q = JobQueue(str(tmp_path / "jobs.db"))
    job = q.submit("index", {})
    package_root = str(Path(hello_agents.__file__).resolve().parents[1])
    script = (
        "import sys,os; sys.path.insert(0,sys.argv[2]); from hello_agents.background import JobQueue; "
        "q=JobQueue(sys.argv[1]); q.claim('crashed',lease_seconds=0.001); os._exit(0)"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(q.path), package_root], timeout=20
    )
    assert result.returncode == 0
    assert q.get(job.job_id).status == "running"
    lease = q.claim("recovered")
    assert lease.job.attempts == 2
    assert q.complete(lease, "resumed").result == "resumed"


@pytest.mark.asyncio
async def test_worker_renews_lease_and_completes(tmp_path, monkeypatch):
    clock = Clock()
    q = JobQueue(str(tmp_path / "jobs.db"), clock=clock)
    job = q.submit("index", {"count": 4})
    loop = asyncio.get_running_loop()
    renewed = asyncio.Event()
    deadlines = []
    heartbeat = q.heartbeat
    lease_seconds = 0.15
    initial_deadline = clock.value + lease_seconds

    def observed_heartbeat(lease, *, lease_seconds):
        # Advance lease time only at a renewal, independently of thread/disk
        # scheduling. Still execute the real SQLite heartbeat and worker loop.
        clock.value += lease_seconds / 3
        heartbeat(lease, lease_seconds=lease_seconds)
        deadlines.append(q.get(job.job_id).lease_until)
        if len(deadlines) >= 4:
            loop.call_soon_threadsafe(renewed.set)

    monkeypatch.setattr(q, "heartbeat", observed_heartbeat)

    async def handler(payload, context):
        await renewed.wait()
        context.checkpoint()
        return {"count": payload["count"]}

    worker = JobWorker(q, {"index": handler}, lease_seconds=lease_seconds)
    assert await asyncio.wait_for(worker.run_once(), timeout=10)
    assert len(deadlines) >= 4
    assert clock.value > initial_deadline
    assert all(a < b for a, b in zip([initial_deadline, *deadlines], deadlines))
    assert q.get(job.job_id).status == "succeeded"
    assert q.get(job.job_id).result == {"count": 4}
    assert not await worker.run_once()


@pytest.mark.asyncio
async def test_worker_late_renewal_cancels_work_and_allows_recovery(
    tmp_path, monkeypatch
):
    clock = Clock()
    q = JobQueue(str(tmp_path / "jobs.db"), clock=clock)
    job = q.submit("index", {"count": 4})
    started = asyncio.Event()
    cancelled = asyncio.Event()
    contexts = []
    expired_leases = []
    heartbeat = q.heartbeat

    async def handler(payload, context):
        contexts.append(context)
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    def late_heartbeat(lease, *, lease_seconds):
        # Model a delayed renewal without relying on a slow CI runner.
        clock.value += lease_seconds + 1
        expired_leases.append(lease)
        heartbeat(lease, lease_seconds=lease_seconds)

    monkeypatch.setattr(q, "heartbeat", late_heartbeat)
    worker = JobWorker(q, {"index": handler}, lease_seconds=0.15)
    assert await asyncio.wait_for(worker.run_once(), timeout=10)
    assert started.is_set() and cancelled.is_set()
    assert len(expired_leases) == 1
    assert q.get(job.job_id).status == "running"
    assert q.get(job.job_id).result is None
    with pytest.raises(LeaseLost):
        contexts[0].checkpoint()
    with pytest.raises(LeaseLost):
        q.complete(expired_leases[0], {"stale": True})

    recovered = q.claim("replacement")
    assert recovered.job.job_id == job.job_id
    assert recovered.job.attempts == 2
    assert q.complete(recovered, {"count": 4}).status == "succeeded"
    with pytest.raises(LeaseLost):
        q.complete(expired_leases[0], {"stale": True})
    assert q.get(job.job_id).result == {"count": 4}


@pytest.mark.asyncio
async def test_worker_bounded_concurrency_and_graceful_stop(tmp_path):
    q = JobQueue(str(tmp_path / "jobs.db"))
    for i in range(6):
        q.submit("index", {"i": i})
    stop = asyncio.Event()
    both_started = asyncio.Event()
    active = peak = completed = 0

    async def handler(payload, context):
        nonlocal active, peak, completed
        active += 1
        peak = max(peak, active)
        if active == 2:
            both_started.set()
        # Require overlapping handlers explicitly; disk/thread scheduling must
        # not decide whether a short wall-clock sleep happens to overlap.
        await both_started.wait()
        active -= 1
        completed += 1
        if completed == 6:
            stop.set()
        return payload

    worker = JobWorker(q, {"index": handler}, concurrency=2)
    await asyncio.wait_for(worker.run(stop), timeout=5)
    assert peak == 2 and len(q.list(status="succeeded")) == 6


@pytest.mark.asyncio
async def test_async_cancellation_cannot_commit(tmp_path):
    q = JobQueue(str(tmp_path / "jobs.db"))
    job = q.submit("index", {})
    started = asyncio.Event()

    async def handler(payload, context):
        started.set()
        await asyncio.sleep(30)

    worker = JobWorker(q, {"index": handler}, lease_seconds=0.15)
    task = asyncio.create_task(worker.run_once())
    await started.wait()
    q.cancel(job.job_id)
    await asyncio.wait_for(task, timeout=3)
    assert q.get(job.job_id).status == "cancelled"


@pytest.mark.asyncio
async def test_worker_failure_retries_and_records_error(tmp_path):
    clock = Clock()
    q = JobQueue(str(tmp_path / "jobs.db"), clock=clock)
    job = q.submit("index", {}, max_attempts=2)

    def fail(payload, context):
        raise ValueError("expected fixture failure")

    worker = JobWorker(q, {"index": fail}, retry_delay=1)
    await worker.run_once()
    assert q.get(job.job_id).status == "queued"
    clock.value += 2
    await worker.run_once()
    assert q.get(job.job_id).status == "failed"
    assert "expected fixture failure" in q.get(job.job_id).error


def test_payload_size_nonfinite_data_and_task_whitelist(tmp_path):
    q = JobQueue(str(tmp_path / "jobs.db"), max_payload_bytes=128)
    with pytest.raises(ValueError):
        q.submit("index", {"value": float("nan")})
    with pytest.raises(ValueError):
        q.submit("index", {"value": "x" * 130})
    job = q.submit("unknown_task", {})
    assert q.claim("worker", tasks=["index"]) is None
    assert q.get(job.job_id).status == "queued"
