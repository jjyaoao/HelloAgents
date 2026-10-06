"""Bounded multi-process queue/recovery check; not a production capacity benchmark."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing
from pathlib import Path
import subprocess
import sys
import tempfile
from time import perf_counter

from hello_agents.background import JobQueue


def consume(arguments):
    path, worker = arguments
    queue = JobQueue(path, namespace="release-check")
    done = []
    while lease := queue.claim(str(worker), lease_seconds=30):
        number = lease.job.payload["number"]
        queue.report_progress(lease, {"processed": 1})
        queue.complete(lease, {"square": number * number})
        done.append(lease.job.job_id)
    return done


def check(directory, jobs, workers):
    path = str(directory / "jobs.db")
    queue = JobQueue(path, namespace="release-check")
    foreign = JobQueue(path, namespace="another-user")
    untouched = foreign.submit("index", {"private": True})
    ids = []
    for number in range(jobs):
        job = queue.submit("index", {"number": number}, idempotency_key=str(number))
        assert queue.submit("index", {"number": number}, idempotency_key=str(number)).job_id == job.job_id
        ids.append(job.job_id)
    # A real process exits after claiming a job, without acknowledging it.
    code = ("import os,sys; from hello_agents.background import JobQueue; "
            "JobQueue(sys.argv[1],namespace='release-check').claim('crashed',lease_seconds=0.001); "
            "os._exit(0)")
    subprocess.run([sys.executable, "-c", code, path], check=True, timeout=30)
    started = perf_counter()
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        consumed = [job_id for batch in pool.map(consume, [(path, i) for i in range(workers)]) for job_id in batch]
    elapsed = perf_counter() - started
    assert len(consumed) == len(set(consumed)) == jobs
    assert set(consumed) == set(ids)
    retries = 0
    for number, job_id in enumerate(ids):
        job = queue.get(job_id)
        assert job.status == "succeeded" and job.result == {"square": number * number}
        assert job.progress == {"processed": 1}
        retries += job.attempts - 1
    assert retries == 1
    assert foreign.get(untouched.job_id).status == "queued"
    return {"jobs": jobs, "workers": workers, "completed_unique": len(consumed),
            "recovered_attempts": retries, "foreign_namespace_untouched": True,
            "worker_elapsed_seconds": elapsed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=200)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path("concurrency-report.json"))
    args = parser.parse_args()
    if not 1 <= args.jobs <= 10000 or not 1 <= args.workers <= 16:
        parser.error("Use 1..10000 jobs and 1..16 workers")
    with tempfile.TemporaryDirectory(prefix="helloagents-concurrency-") as temporary:
        report = check(Path(temporary), args.jobs, args.workers)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
