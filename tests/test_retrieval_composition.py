"""真实 SQLite/词项计算；重排替身只验证管线契约，不评估模型质量。"""

from dataclasses import replace

import pytest

from hello_agents import ToolRegistry
from hello_agents.context import RetrievalContextProvider
from hello_agents.retrieval import RAGStore, RelationStore, RetrievalPipeline
from hello_agents.tools import RAGTool, RelationTool


def source(tmp_path):
    store = RAGStore(tmp_path / "rag.db")
    store.add_document(
        "杭州馆连接东站。东站连接湖畔步道。湖畔步道连接杭州馆。",
        "fixture://route",
        document_id="route",
    )
    store.add_document("杭州馆预约需要一天。", "fixture://notice", document_id="notice")
    return store


def test_document_reread_never_changes_version(tmp_path):
    store = source(tmp_path)
    old = store.search("杭州馆预约")[0]
    store.add_document("杭州馆预约需要两天。", "fixture://notice", "2", "notice")
    assert store.read_document("notice").version == "2"
    assert store.read_document("notice", "1").active is False
    assert (
        store.read_document("notice", "1").content[old.start : old.end] == old.content
    )
    with pytest.raises(KeyError):
        store.read_document("notice", "missing")
    with pytest.raises(ValueError):
        store.read_document("notice", "")


def graph(tmp_path):
    store = source(tmp_path)
    relations = RelationStore(store)
    chunk = next(r for r in store.search("连接") if r.document_id == "route")
    for subject, obj in [
        ("杭州馆", "东站"),
        ("东站", "湖畔步道"),
        ("湖畔步道", "杭州馆"),
    ]:
        relations.add(subject, "连接", obj, chunk.chunk_id, f"{subject}连接{obj}。")
    return store, relations, chunk


def test_graph_evidence_depth_cycles_and_persistence(tmp_path):
    store, relations, chunk = graph(tmp_path)
    results = relations.neighbors("杭州馆", hops=3, direction="out")
    assert [r.depth for r in results] == [1, 2, 3]
    assert len({r.relation_id for r in results}) == 3
    assert all(r.quote in r.evidence.content for r in results)
    assert results[1].to_context_packet().metadata["chunk_id"] == chunk.chunk_id
    reopened = RelationStore(RAGStore(store.path))
    assert reopened.neighbors("杭州馆", direction="in")[0].subject == "湖畔步道"
    assert len(reopened.neighbors("杭州馆", hops=3, limit=1)) == 1


def test_graph_rejects_unverifiable_quote_and_filters_old_version(tmp_path):
    store, relations, chunk = graph(tmp_path)
    with pytest.raises(ValueError):
        relations.add("杭州馆", "连接", "火星", chunk.chunk_id, "此句不在原文")
    store.add_document("旧线路关闭。", "fixture://route", "2", "route")
    assert relations.neighbors("杭州馆", hops=3) == []
    assert store.read_chunk(chunk.chunk_id).version == "1"
    assert relations.neighbors("同名杭州馆") == []


@pytest.mark.parametrize(
    "kwargs", [{"hops": 0}, {"hops": True}, {"limit": 0}, {"direction": "unknown"}]
)
def test_graph_invalid_limits(tmp_path, kwargs):
    _, relations, _ = graph(tmp_path)
    with pytest.raises(ValueError):
        relations.neighbors("杭州馆", **kwargs)


def test_pipeline_injection_preserves_evidence(tmp_path):
    store = source(tmp_path)

    class Reverse:
        def rerank(self, query, candidates):
            return list(reversed(candidates))

    pipeline = RetrievalPipeline(store, Reverse(), candidate_limit=5)
    original = store.search("杭州", 5)
    assert pipeline.search("杭州", 2) == list(reversed(original))[:2]
    provider = RetrievalContextProvider(pipeline, limit=2)
    assert len(list(provider.get_context("杭州"))) == 2
    registry = ToolRegistry()
    registry.register_tool(RAGTool(store, search_backend=pipeline))
    response = registry.execute_tool("rag_search", {"query": "杭州", "limit": 2})
    assert response.data["results"][0]["chunk_id"] == original[-1].chunk_id
    document = registry.execute_tool(
        "rag_read_document", {"document_id": "notice", "version": "1"}
    )
    assert document.data["document"]["active"] is True
    invalid = registry.execute_tool(
        "rag_read_document", {"document_id": "notice", "version": None}
    )
    assert invalid.error_info["code"] == "INVALID_PARAM"


@pytest.mark.parametrize("change", ["drop", "duplicate", "rewrite"])
def test_reranker_cannot_silently_change_candidates(tmp_path, change):
    class BadReranker:
        def rerank(self, query, candidates):
            if change == "drop":
                return candidates[:-1]
            if change == "duplicate":
                return [candidates[0]] * len(candidates)
            return [replace(candidates[0], content="伪造内容"), *candidates[1:]]

    with pytest.raises(ValueError):
        RetrievalPipeline(source(tmp_path), BadReranker()).search("杭州")


def test_relation_tool_standard_response(tmp_path):
    _, relations, _ = graph(tmp_path)
    registry = ToolRegistry()
    registry.register_tool(RelationTool(relations))
    response = registry.execute_tool("relation_lookup", {"entity": "杭州馆", "hops": 2})
    assert response.data["relations"][0]["evidence"]["source"] == "fixture://route"
    invalid = registry.execute_tool("relation_lookup", {"entity": "杭州馆", "hops": 4})
    assert invalid.error_info["code"] == "INVALID_PARAM"
