"""Actual Leiden/SQLite GraphRAG lifecycle; model responses are labeled fixtures."""

from collections import Counter
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

pytest.importorskip("igraph")
pytest.importorskip("leidenalg")

from hello_agents.retrieval import (
    RAGStore,
    GraphRAGIndex,
    GraphConfig,
    HelloAgentsGraphModel,
    IndexStaleError,
)
from hello_agents.retrieval.graph import (
    GraphBudgetError,
    GraphIntegrityError,
    GraphBuildConflict,
)
from hello_agents.tools.builtin.graphrag_tool import GraphRAGTool
from hello_agents import ToolRegistry


class FixtureModel:
    model_id = "graph-test-fixture-v1"

    def __init__(self):
        self.calls = Counter()
        self.before = None

    def generate(self, stage, payload, **kwargs):
        self.calls[stage] += 1
        if self.before:
            self.before(stage, payload)
        if stage == "extract":
            text = payload["content"]
            names = [
                name
                for name in ("Alpha", "Beta", "Gamma", "Delta", "Epsilon")
                if name in text
            ]
            return {
                "entities": [
                    {
                        "key": name,
                        "name": name,
                        "kind": "organization",
                        "scope": "region",
                        "aliases": [],
                        "description": name + " service",
                        "quote": text,
                    }
                    for name in names
                ],
                "relations": [
                    {
                        "source": a,
                        "target": b,
                        "predicate": "depends_on",
                        "description": text,
                        "quote": text,
                    }
                    for a, b in zip(names, names[1:])
                ],
            }
        if stage == "report":
            return {
                "title": "Service dependencies",
                "claims": [
                    {"text": item["quote"], "citations": [item["id"]]}
                    for item in payload["evidence"]
                ],
            }
        if stage == "map":
            return {
                "claims": (
                    []
                    if payload["question"] == "unanswerable"
                    else payload["report"]["claims"]
                )
            }
        claims = {}
        for item in payload["claims"]:
            claims.setdefault(item["text"], set()).update(item["citations"])
        return {
            "claims": [
                {"text": text, "citations": sorted(ids)} for text, ids in claims.items()
            ]
        }


@pytest.fixture
def built(tmp_path):
    store = RAGStore(str(tmp_path / "sources.db"))
    for identifier, content in (
        ("a", "Alpha depends on Beta."),
        ("b", "Beta depends on Gamma."),
        ("c", "Delta depends on Epsilon."),
    ):
        store.add_document(content, "fixture://" + identifier, document_id=identifier)
    model = FixtureModel()
    index = GraphRAGIndex(store, str(tmp_path / "graph.db"), model)
    return store, model, index


def test_real_leiden_hierarchy_provenance_and_global_coverage(built, monkeypatch):
    import leidenalg

    calls = []
    original = leidenalg.find_partition

    def observed(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(leidenalg, "find_partition", observed)
    store, model, index = built
    result = index.build()
    assert calls and all(call["seed"] == 42 for call in calls)
    assert result.entities == 5 and result.relations == 3
    data = index.inspect()
    for level in range(2):
        members = [
            eid
            for c in data["communities"]
            if c["level"] == level
            for eid in c["entity_ids"]
        ]
        assert sorted(members) == sorted(data["entities"])
    for community in data["communities"]:
        if community["level"]:
            parent = next(
                c for c in data["communities"] if c["id"] == community["parent"]
            )
            assert set(community["entity_ids"]) <= set(parent["entity_ids"])
    answer = index.global_search("What are the service dependencies?")
    assert answer.status == "answered" and answer.coverage["complete"]
    assert answer.coverage["mapped_reports"] == answer.coverage["total_reports"]
    assert answer.coverage["summarized_chunks"] == 3
    for citation in answer.citations:
        document = store.read_document(citation["document_id"], citation["version"])
        assert (
            document.content[citation["start"] : citation["end"]] == citation["quote"]
        )
    local = index.local_context("Alpha", 3)
    assert {c.document_id for c in local["chunks"]} == {"a", "b"}
    assert local["relations"] and local["reports"]


def test_repeat_reopen_update_and_cached_unchanged_chunks(built):
    store, model, index = built
    original = index.build()
    counts = model.calls.copy()
    assert index.build().reused_generation
    assert model.calls == counts
    reopened = GraphRAGIndex(store, str(index.storage.path), model)
    assert reopened.build().generation == original.generation
    store.add_document(
        "Beta depends on Gamma, except during closure.",
        "fixture://b",
        version="2",
        document_id="b",
    )
    with pytest.raises(IndexStaleError):
        index.search("Alpha")
    changed = index.build()
    assert changed.extraction_cache_hits == 2
    assert model.calls["extract"] == counts["extract"] + 1
    assert {r.version for r in index.search("Beta") if r.document_id == "b"} == {"2"}
    assert changed.report_cache_hits > 0


def test_partial_failure_resumes_and_does_not_publish(built):
    _, model, index = built

    def fail_second(stage, payload):
        if stage == "extract" and model.calls["extract"] == 2:
            raise RuntimeError("injected service outage")

    model.before = fail_second
    with pytest.raises(RuntimeError, match="outage"):
        index.build()
    assert index.storage.active() is None
    model.before = None
    result = index.build()
    assert result.extraction_cache_hits == 1
    assert model.calls["extract"] == 4  # first successful, failed, two remaining


@pytest.mark.parametrize("problem", ["quote", "endpoint", "name", "report_citation"])
def test_invalid_extraction_or_report_never_publishes(built, problem):
    _, model, index = built
    original = model.generate

    def invalid(stage, payload, **kwargs):
        raw = original(stage, payload, **kwargs)
        if stage == "extract" and problem == "quote":
            raw["entities"][0]["quote"] = "Invented sentence."
        elif stage == "extract" and problem == "endpoint":
            raw["relations"][0]["target"] = "undeclared"
        elif stage == "extract" and problem == "name":
            raw["entities"][0]["name"] = "MissingName"
        elif stage == "report" and problem == "report_citation":
            raw["claims"][0]["citations"] = ["invented-source"]
        return raw

    model.generate = invalid
    with pytest.raises(GraphIntegrityError):
        index.build()
    assert index.storage.active() is None


def test_alias_collisions_are_retained_not_merged(tmp_path):
    store = RAGStore(str(tmp_path / "source.db"))
    store.add_document("Alpha, also called Shared, operates here.", "fixture://east")
    store.add_document("Beta, also called Shared, operates here.", "fixture://west")
    model = FixtureModel()
    original = model.generate

    def aliases(stage, payload, **kwargs):
        raw = original(stage, payload, **kwargs)
        if stage == "extract":
            for entity in raw["entities"]:
                entity["aliases"] = ["Shared"]
        return raw

    model.generate = aliases
    index = GraphRAGIndex(store, str(tmp_path / "graph.db"), model)
    report = index.build()
    assert report.entities == 2 and len(report.ambiguous_aliases["shared"]) == 2
    context = index.local_context("Shared")
    assert len(context["entities"]) == 2
    assert context["diagnostics"]["ambiguous_aliases"]["shared"]


def test_entity_free_chunks_are_reported_and_no_answer_is_explicit(tmp_path):
    store = RAGStore(str(tmp_path / "source.db"))
    store.add_document("All bookings require advance notice.", "fixture://rule")
    index = GraphRAGIndex(store, str(tmp_path / "graph.db"), FixtureModel())
    assert index.build().entities == 0
    assert all(c["kind"] == "unassigned" for c in index.inspect()["communities"])
    assert index.global_search("booking rules").coverage["complete"]
    answer = index.global_search("unanswerable")
    assert answer.status == "no_answer" and answer.citations == []


@pytest.mark.parametrize("stage", ["map", "reduce"])
def test_query_cannot_introduce_new_citations(built, stage):
    _, model, index = built
    index.build()
    original = model.generate

    def bad(current, payload, **kwargs):
        raw = original(current, payload, **kwargs)
        if current == stage:
            raw["claims"][0]["citations"] = ["foreign-evidence"]
        return raw

    model.generate = bad
    with pytest.raises(GraphIntegrityError):
        index.global_search("dependencies")


def test_cancelled_build_and_competing_publish_are_fenced(built):
    store, model, index = built
    count = 0

    def cancel():
        nonlocal count
        count += 1
        if count == 3:
            raise RuntimeError("cancelled by job")

    with pytest.raises(RuntimeError, match="cancelled"):
        index.build(checkpoint=cancel)
    assert index.storage.active() is None
    competitor = GraphRAGIndex(store, str(index.storage.path), FixtureModel())
    triggered = False

    def publish_other():
        nonlocal triggered
        if not triggered:
            triggered = True
            competitor.build()

    model.before = lambda stage, payload: publish_other()
    with pytest.raises(GraphBuildConflict):
        index.build()
    assert (
        index.inspect()["build_report"]["generation"] == competitor.build().generation
    )


def test_source_change_and_different_store_are_rejected(built, tmp_path):
    store, model, index = built

    def update(stage, payload):
        if stage == "report":
            store.deactivate_document("a")

    model.before = update
    with pytest.raises(IndexStaleError):
        index.build()
    assert index.storage.active() is None
    other = RAGStore(str(tmp_path / "other.db"))
    with pytest.raises(GraphIntegrityError, match="different"):
        GraphRAGIndex(other, str(index.storage.path), model)


def test_small_budget_fails_instead_of_truncating_sources(tmp_path):
    store = RAGStore(str(tmp_path / "source.db"))
    store.add_document(
        "Alpha " + "证据" * 4000, "fixture://large", chunk_size=10000, overlap=0
    )
    index = GraphRAGIndex(
        store,
        str(tmp_path / "graph.db"),
        FixtureModel(),
        config=GraphConfig(max_input_tokens=3000),
    )
    with pytest.raises(GraphBudgetError, match="silently"):
        index.build()
    assert index.storage.active() is None


def test_empty_reports_are_not_mislabeled_as_full_source_coverage(built):
    _, model, index = built
    original = model.generate

    def empty(stage, payload, **kwargs):
        raw = original(stage, payload, **kwargs)
        if stage == "report":
            raw["claims"] = []
        return raw

    model.generate = empty
    index.build()
    answer = index.global_search("dependencies")
    assert answer.status == "no_answer" and not answer.coverage["complete"]
    assert len(answer.coverage["unsummarized_chunk_ids"]) == 3


def test_model_adapter_json_retry_truncation_and_token_bounds():
    responses = iter(["not-json", '{"claims": []}'])
    llm = SimpleNamespace(
        invoke=lambda *a, **k: SimpleNamespace(content=next(responses))
    )
    model = HelloAgentsGraphModel(llm)
    assert model.generate("map", {}, max_input_tokens=5000, max_output_tokens=100) == {
        "claims": []
    }
    llm.invoke = lambda *a, **k: SimpleNamespace(
        content='{"claims": []}', finish_reason="length"
    )
    with pytest.raises(GraphBudgetError, match="truncated"):
        model.generate("map", {}, max_input_tokens=5000, max_output_tokens=100)
    with pytest.raises(GraphBudgetError, match="prompt"):
        model.generate("map", {}, max_input_tokens=5, max_output_tokens=100)


def test_model_retry_explains_schema_error_without_echoing_invalid_input():
    calls = []
    responses = iter(
        [
            json.dumps(
                {
                    "entities": [
                        {
                            "key": "a",
                            "name": "Alpha",
                            "kind": "private-invalid-kind",
                            "description": "Alpha",
                            "quote": "Alpha",
                        }
                    ],
                    "relations": [],
                }
            ),
            '{"entities": [], "relations": []}',
        ]
    )

    def invoke(messages, **kwargs):
        calls.append(messages)
        return SimpleNamespace(content=next(responses))

    model = HelloAgentsGraphModel(SimpleNamespace(invoke=invoke))
    assert model.generate(
        "extract", {}, max_input_tokens=5000, max_output_tokens=1000
    ) == {"entities": [], "relations": []}
    feedback = calls[1][-1]["content"]
    assert "validation_errors_to_correct" in feedback and "organization" in feedback
    assert "private-invalid-kind" not in feedback


def test_semantic_entity_seeding_uses_real_qdrant(built, tmp_path):
    pytest.importorskip("qdrant_client")

    class Embedding:
        model_id = "deterministic-protocol-fixture"
        dimension = 3

        def embed_documents(self, texts):
            return [[1.0, 0.0, 0.0] for _ in texts]

        def embed_query(self, text):
            return [1.0, 0.0, 0.0]

    store, model, _ = built
    index = GraphRAGIndex(
        store, str(tmp_path / "semantic.db"), model, embedding=Embedding()
    )
    index.build()
    assert index.local_search("paraphrase without entity names")
    assert index.last_local_diagnostics["semantic_seeds"]


def test_graphrag_tool_integrates_with_registry(built):
    _, _, index = built
    index.build()
    registry = ToolRegistry()
    tool = GraphRAGTool(index)
    assert tool.to_openai_schema()["function"]["parameters"]
    registry.register_tool(tool)
    assert registry.execute_tool("graphrag_local", {"query": "Alpha"}).data["results"]
    assert registry.execute_tool("graphrag_global", {"query": "dependencies"}).data[
        "coverage"
    ]["complete"]


def test_changed_generation_budget_does_not_reuse_unchecked_cached_outputs(built):
    store, model, index = built
    index.build()
    before = model.calls.copy()
    changed = GraphRAGIndex(
        store,
        str(index.storage.path),
        model,
        config=GraphConfig(max_output_tokens=2000),
    )
    result = changed.build()
    assert result.extraction_cache_hits == result.report_cache_hits == 0
    assert model.calls["extract"] == before["extract"] + 3
    with pytest.raises(TypeError, match="checkpoint"):
        changed.build(checkpoint=False)
    with pytest.raises(TypeError, match="checkpoint"):
        changed.global_search("question", checkpoint=0)


@pytest.mark.asyncio
async def test_jobworker_retries_interrupted_graph_build_from_cached_extraction(
    built, tmp_path
):
    from hello_agents.background import JobQueue, JobWorker

    _, model, index = built
    now = [1000.0]
    queue = JobQueue(str(tmp_path / "jobs.db"), clock=lambda: now[0])

    def interrupted(stage, payload):
        if stage == "extract" and model.calls["extract"] == 2:
            raise RuntimeError("interrupted after one cached extraction")

    model.before = interrupted

    def handler(payload, context):
        return index.build(checkpoint=context.checkpoint).to_dict()

    job = queue.submit("graph_build", {}, max_attempts=2)
    worker = JobWorker(queue, {"graph_build": handler}, retry_delay=1)
    assert await worker.run_once()
    assert queue.get(job.job_id).status == "queued"
    assert index.storage.active() is None
    model.before = None
    now[0] += 2
    assert await worker.run_once()
    done = queue.get(job.job_id)
    assert done.status == "succeeded" and done.attempts == 2
    assert done.result["extraction_cache_hits"] == 1
    assert done.result["generation"] == index.inspect()["build_report"]["generation"]
