"""Persist an indexing job, retry an interrupted import, and resume from progress."""

import argparse
import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from hello_agents.background import JobQueue, JobWorker
from hello_agents.retrieval import RAGStore


DOCUMENTS = [
    ("transport", "交通安排：以地铁为主，预留换乘时间。"),
    ("museum", "展馆安排：先核对预约状态，再确定入馆时间。"),
    ("rain", "雨天安排：用室内展览替换湖边步行。"),
]


async def run(root):
    queue_path = str(root / "jobs.sqlite")
    producer = JobQueue(queue_path, namespace="travel-index")
    submitted = producer.submit(
        "import_rules",
        {"dataset": "travel-rules-v1"},
        idempotency_key="travel-rules-v1",
        max_attempts=3,
    )
    # A new process can open the same queue. The handler is registered by trusted code.
    queue = JobQueue(queue_path, namespace="travel-index")
    store = RAGStore(str(root / "rules.sqlite"))

    def import_rules(payload, context):
        if payload != {"dataset": "travel-rules-v1"}:
            raise ValueError("Unknown dataset")
        offset = (context.progress or {}).get("imported", 0)
        for position in range(offset, len(DOCUMENTS)):
            context.checkpoint()
            name, text = DOCUMENTS[position]
            # Immutable document versions make repeated imports idempotent, including
            # interruption between this write and report_progress().
            store.add_document(text, f"fixture://{name}", document_id=name, version="1")
            context.report_progress({"imported": position + 1, "total": len(DOCUMENTS)})
            if context.attempt == 1 and position == 0:
                raise RuntimeError(
                    "Injected interruption after first persisted document"
                )
        return {"documents": len(DOCUMENTS), "revision": store.revision}

    worker = JobWorker(
        queue, {"import_rules": import_rules}, concurrency=1, retry_delay=0.01
    )
    while queue.get(submitted.job_id).status in {"queued", "running"}:
        await worker.run_once()
        await asyncio.sleep(0.02)
    finished = queue.get(submitted.job_id)
    assert finished.status == "succeeded", finished.error
    assert finished.attempts == 2
    assert len(store.snapshot()[1]) == len(DOCUMENTS)
    assert store.search("雨天")[0].document_id == "rain"
    result = finished.to_dict()
    (root / "background-report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="hello-jobs-") as temporary:
        root = args.workspace or Path(temporary)
        root.mkdir(parents=True, exist_ok=True)
        asyncio.run(run(root))


if __name__ == "__main__":
    main()
