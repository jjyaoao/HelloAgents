import pytest

pytest.importorskip("qdrant_client")
from qdrant_client import QdrantClient
from hello_agents.memory import MemoryStore, SemanticMemorySearch
from hello_agents.retrieval import IndexStaleError
from hello_agents.context import MemoryContextProvider
from hello_agents.tools import MemoryTool


class FixtureEmbedding:
    """Deterministic vectors for protocol tests, not semantic quality evidence."""

    model_id, dimension = "fixture-memory", 3

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        return [1.0, 0.0, 0.0] if "walk" in text else [0.0, 1.0, 0.0]


def test_update_retract_reopen_and_unchanged_scope(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.db"), "alice", "travel")
    record = store.add("walk at most eight km", "message:1")
    with SemanticMemorySearch(
        store, FixtureEmbedding(), path=str(tmp_path / "vectors")
    ) as search:
        assert search.sync() == 1
        assert search.search("walk", 1)[0].memory_id == record.memory_id
        assert search.sync() == 0
        new = store.revise(record.memory_id, "walk at most five km", "message:2")
        with pytest.raises(IndexStaleError):
            search.search("walk")
        search.sync()
        assert [r.memory_id for r in search.search("walk")] == [new.memory_id]
        store.retract(new.memory_id)
        with pytest.raises(IndexStaleError):
            search.search("walk")
        search.sync()
        assert search.search("walk") == []
    reopened = MemoryStore(str(store.path), "alice", "travel")
    assert reopened.namespace == store.namespace and reopened.revision == 3
    with SemanticMemorySearch(
        reopened, FixtureEmbedding(), path=str(tmp_path / "vectors")
    ) as search:
        assert search.sync() == 0 and search.search("walk") == []


def test_actual_shared_collection_keeps_user_and_task_scopes_separate(tmp_path):
    a = MemoryStore(str(tmp_path / "all.db"), "alice", "travel")
    b = MemoryStore(str(a.path), "bob", "travel")
    work = MemoryStore(str(a.path), "alice", "work")
    a.add("walk museum", "alice")
    b.add("walk secret bob", "bob")
    work.add("walk secret work", "work")
    client = QdrantClient(":memory:")
    try:
        with (
            SemanticMemorySearch(a, FixtureEmbedding(), client=client) as sa,
            SemanticMemorySearch(b, FixtureEmbedding(), client=client) as sb,
        ):
            sa.sync()
            sb.sync()
            assert [r.user_id for r in sa.search("walk")] == ["alice"]
            assert [r.user_id for r in sb.search("walk")] == ["bob"]
            b.add("new bob memory", "bob:2")
            assert len(sa.search("walk")) == 1  # other scope does not invalidate Alice
            provider = MemoryContextProvider(a, search_backend=sa, use_query=True)
            assert provider.get_context("walk")[0].content == "walk museum"
            tool = MemoryTool(a, search_backend=sa)
            assert tool.search("walk").data["records"][0]["source"] == "alice"
    finally:
        client.close()


def test_memory_revision_tracks_only_successful_state_changes(tmp_path):
    store = MemoryStore(str(tmp_path / "m.db"), "a", "t")
    with pytest.raises(ValueError):
        store.add("", "s")
    assert store.revision == 0
    record = store.add("content", "s")
    store.retract(record.memory_id)
    store.retract(record.memory_id)
    assert store.revision == 2
    assert store.snapshot() == (2, [])


def test_interrupted_index_keeps_previous_manifest_and_tools_report_stale(tmp_path):
    from hello_agents.background import LeaseLost

    store = MemoryStore(str(tmp_path / "m.db"), "a", "t")
    store.add("walk old", "s1")
    with SemanticMemorySearch(store, FixtureEmbedding(), path=":memory:") as search:
        search.sync()
        old_generation = search.dense._manifest()["generation"]
        store.add("walk new", "s2")
        calls = 0

        def checkpoint():
            nonlocal calls
            calls += 1
            if calls == 3:
                raise LeaseLost("cancelled before publish")

        with pytest.raises(LeaseLost):
            search.sync(checkpoint=checkpoint)
        assert search.dense._manifest()["generation"] == old_generation
        assert (
            MemoryTool(store, search_backend=search).search("walk").error_info["code"]
            == "CONFLICT"
        )
        search.sync()
        assert len(search.search("walk")) == 2
    with pytest.raises(RuntimeError):
        search.search("")
