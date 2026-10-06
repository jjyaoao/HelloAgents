"""Real embedding recall, correction and withdrawal; optional live Agent Loop."""

import argparse
import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from hello_agents import SimpleAgent, ToolRegistry
from hello_agents.background import JobQueue, JobWorker
from hello_agents.memory import MemoryStore, SemanticMemorySearch
from hello_agents.retrieval import FastEmbedProvider, IndexStaleError
from hello_agents.tools.builtin import MemoryTool
from hello_agents.tools.permissions import AllowlistPolicy
from examples._support import demo_llm


async def run(root, embedding, live=False):
    # A fresh scope per experiment keeps repeat runs independent in a persistent workspace.
    queue = JobQueue(str(root / "jobs.sqlite"))
    import uuid

    scope = uuid.uuid4().hex
    store = MemoryStore(str(root / "memory.sqlite"), user_id="alice", task_id=scope)
    old = store.add("膝盖不舒服，每天步行最多八公里。", "user:initial", "preference")
    store.add("喜欢历史展览和古建筑。", "user:interests", "preference")
    store.add("上次旅行坐地铁到达酒店。", "session:previous", "episode")
    store.add("餐饮预算每天二百元。", "user:budget", "preference")
    store.add("优先预订可免费取消的房间。", "user:hotel", "preference")
    other = MemoryStore(str(root / "memory.sqlite"), user_id="bob", task_id=scope)
    other.add("每天可以走二十公里。", "user:bob", "preference")
    with SemanticMemorySearch(store, embedding, path=str(root / "vectors")) as recall:

        def rebuild(payload, context):
            context.report_progress({"stage": "embedding"})
            count = recall.sync(checkpoint=context.checkpoint)
            context.report_progress({"stage": "ready", "revision": store.revision})
            return {"encoded": count}

        worker = JobWorker(queue, {"memory_index": rebuild}, concurrency=1)

        async def sync():
            job = queue.submit(
                "memory_index",
                {"scope": scope, "revision": store.revision},
                idempotency_key=f"{scope}:{store.revision}",
            )
            await worker.run_once()
            result = queue.get(job.job_id)
            assert result.status == "succeeded", result.error
            return result

        await sync()
        query = "安排活动时，徒步的强度需要注意什么？"
        before = recall.search(query, 3)
        assert before[0].memory_id == old.memory_id, [r.content for r in before]
        corrected = store.revise(
            old.memory_id, "膝盖恢复期间，每天步行最多五公里。", "user:correction"
        )
        try:
            recall.search(query)
        except IndexStaleError:
            stale_rejected = True
        else:
            raise AssertionError("Unsynced correction must invalidate semantic recall")
        job = await sync()
        after = recall.search(query, 3)
        assert after[0].memory_id == corrected.memory_id
        assert all(r.user_id == "alice" and r.memory_id != old.memory_id for r in after)
        report = {
            "fixture_notice": "虚构用户记录的小型机制实验，不代表通用检索准确率。",
            "embedding": embedding.model_id,
            "query": query,
            "before": [r.to_dict() for r in before],
            "after": [r.to_dict() for r in after],
            "stale_index_rejected": stale_rejected,
            "index_job": job.result,
        }
        if live:
            registry = ToolRegistry(policy=AllowlistPolicy(["memory_search"]))
            registry.register_tool(MemoryTool(store, search_backend=recall))
            agent = SimpleAgent(
                "travel-memory", demo_llm([], live=True), tool_registry=registry
            )
            answer = await agent.arun(
                "先调用 memory_search 查询当前用户的步行限制。只返回 JSON，字段 walking_km 为当前每天步行上限的整数；不可使用旧值。"
            )
            parsed = json.loads(
                answer.strip().removeprefix("```json").removesuffix("```").strip()
            )
            assert parsed["walking_km"] == 5 and agent.last_run.tool_calls >= 1
            report["live_answer"] = parsed
            report["live_tool_calls"] = agent.last_run.tool_calls
        store.retract(corrected.memory_id)
        await sync()
        assert corrected.memory_id not in {r.memory_id for r in recall.search(query)}
        report["withdrawn_record_excluded"] = True
        report["other_user_excluded"] = True
        output = json.dumps(report, ensure_ascii=False, indent=2)
        (root / "semantic-memory-report.json").write_text(output, encoding="utf-8")
        print(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="FastEmbed embedding model name")
    parser.add_argument("--dimension", required=True, type=int)
    parser.add_argument("--cache-dir")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()
    embedding = FastEmbedProvider(
        args.model,
        args.dimension,
        cache_dir=args.cache_dir,
        local_files_only=args.local_files_only,
    )
    with TemporaryDirectory(prefix="hello-memory-") as temporary:
        root = args.workspace or Path(temporary)
        root.mkdir(parents=True, exist_ok=True)
        asyncio.run(run(root, embedding, args.live))


if __name__ == "__main__":
    main()
