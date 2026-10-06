"""Real local Qdrant integration; deterministic vectors test protocol, not model quality."""

from dataclasses import replace
from contextlib import closing
from types import SimpleNamespace

import pytest

pytest.importorskip("qdrant_client")
from qdrant_client import QdrantClient, models

from hello_agents.retrieval import (
    RAGStore,
    QdrantSearch,
    HybridSearch,
    IndexStaleError,
    OpenAIEmbeddingProvider,
    FastEmbedProvider,
)


class FixtureEmbedding:
    model_id = "test-fixture-v1"
    dimension = 3

    def __init__(self):
        self.calls = 0

    def embed_query(self, text):
        return (
            [1.0, 0.0, 0.0] if "museum" in text or "rain" in text else [0.0, 1.0, 0.0]
        )

    def embed_documents(self, texts):
        self.calls += len(texts)
        return [self.embed_query(text) for text in texts]


@pytest.fixture
def store(tmp_path):
    result = RAGStore(str(tmp_path / "evidence.db"))
    result.add_document(
        "museum indoors rain plan", "guide:indoor", document_id="indoor"
    )
    result.add_document("lake walk sunshine", "guide:outdoor", document_id="outdoor")
    return result


def test_real_qdrant_persistence_sources_and_no_reembedding(store, tmp_path):
    embedding = FixtureEmbedding()
    path = str(tmp_path / "vectors")
    with QdrantSearch(store, embedding, path=path) as search:
        with pytest.raises(IndexStaleError):
            search.search("rain")
        assert search.sync() == 2
        assert search.sync() == 0
        assert embedding.calls == 2
        hit = search.search("rain", 1)[0]
        assert hit.document_id == "indoor"
        assert hit.source == "guide:indoor"
        assert store.read_chunk(hit.chunk_id).content == hit.content
        assert hit.to_context_packet().metadata["version"] == "1"
    with QdrantSearch(
        RAGStore(str(store.path)), FixtureEmbedding(), path=path
    ) as reopened:
        assert reopened.sync() == 0
        assert reopened.search("rain", 1)[0].chunk_id == hit.chunk_id


def test_version_update_and_retraction_are_fail_closed(store):
    with QdrantSearch(store, FixtureEmbedding(), path=":memory:") as search:
        search.sync()
        old = search.search("rain", 1)[0]
        store.add_document(
            "museum opens after noon", "guide:indoor", version="2", document_id="indoor"
        )
        with pytest.raises(IndexStaleError):
            search.search("museum")
        search.sync()
        current = search.search("museum", 1)[0]
        assert current.version == "2"
        assert store.read_chunk(old.chunk_id).content == old.content
        assert store.deactivate_document("indoor")
        assert not store.deactivate_document("indoor")
        with pytest.raises(IndexStaleError):
            search.search("museum")
        search.sync()
        assert all(item.document_id != "indoor" for item in search.search("museum"))


def test_namespaces_do_not_leak_and_borrowed_client_remains_open(store, tmp_path):
    other = RAGStore(str(tmp_path / "other.db"))
    other.add_document("museum private notes", "private", document_id="indoor")
    with closing(QdrantClient(":memory:")) as client:
        first = QdrantSearch(store, FixtureEmbedding(), client=client)
        second = QdrantSearch(other, FixtureEmbedding(), client=client)
        first.sync()
        second.sync()
        assert first.search("museum", 1)[0].source == "guide:indoor"
        assert second.search("museum", 1)[0].source == "private"
        first.close()
        assert second.search("museum", 1)[0].source == "private"
        assert client.get_collection("hello_agents")


def test_embedding_identity_and_dimension_are_checked(store):
    with closing(QdrantClient(":memory:")) as client:
        search = QdrantSearch(store, FixtureEmbedding(), client=client)
        search.sync()
        other = FixtureEmbedding()
        other.model_id = "changed-preprocessing"
        with pytest.raises(ValueError, match="嵌入模型"):
            QdrantSearch(store, other, client=client)
        other.dimension = 7
        with pytest.raises(ValueError, match="维度"):
            QdrantSearch(store, other, client=client)


@pytest.mark.parametrize(
    "vectors", [[[1, 2]], [[0, 0, 0]], [[float("nan"), 0, 1]], [[True, 0, 1]], []]
)
def test_bad_embeddings_never_publish_partial_generation(store, vectors):
    embedding = FixtureEmbedding()
    with QdrantSearch(store, embedding, path=":memory:") as search:
        embedding.embed_documents = lambda texts: vectors
        with pytest.raises(ValueError):
            search.sync(batch_size=1)
        with pytest.raises(IndexStaleError):
            search.search("museum")


def test_interrupted_upload_keeps_published_manifest(store, monkeypatch):
    with QdrantSearch(store, FixtureEmbedding(), path=":memory:") as search:
        search.sync()
        previous = search._manifest()
        store.add_document("museum archives", "archives")
        real = search.client.upsert
        count = 0

        def fail_second(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise RuntimeError("injected transport failure")
            return real(*args, **kwargs)

        monkeypatch.setattr(search.client, "upsert", fail_second)
        with pytest.raises(RuntimeError, match="transport"):
            search.sync(batch_size=1)
        assert search._manifest() == previous
        with pytest.raises(IndexStaleError):
            search.search("museum")
        monkeypatch.setattr(search.client, "upsert", real)
        assert search.sync() == 3
        assert len(search.search("museum")) == 3


def test_source_change_during_embedding_does_not_publish(store):
    embedding = FixtureEmbedding()
    original = embedding.embed_documents

    def mutate(texts):
        store.add_document("new entry", "changed")
        return original(texts)

    embedding.embed_documents = mutate
    with QdrantSearch(store, embedding, path=":memory:") as search:
        with pytest.raises(IndexStaleError, match="同步期间"):
            search.sync()
        assert search._manifest() is None


def test_missing_canonical_chunk_is_never_returned(store):
    with QdrantSearch(store, FixtureEmbedding(), path=":memory:") as search:
        search.sync()
        manifest = search._manifest()
        search.client.upsert(
            "hello_agents",
            points=[
                models.PointStruct(
                    id=999,
                    vector=[1, 0, 0],
                    payload={
                        "namespace": store.namespace,
                        "kind": "chunk",
                        "generation": manifest["generation"],
                        "model_id": "test-fixture-v1",
                        "chunk_id": "missing",
                    },
                )
            ],
        )
        with pytest.raises(IndexStaleError, match="无有效原文"):
            search.search("museum", 100)


def test_hybrid_rank_fusion_preserves_evidence_and_scores(store):
    rows = store.snapshot()[1]
    a, b = rows
    first = SimpleNamespace(
        search=lambda query, limit: [replace(a, score=1000), replace(b, score=20)]
    )
    second = SimpleNamespace(search=lambda query, limit: [replace(b, score=0.9)])
    result = HybridSearch([first, second]).search("anything")
    assert result[0].chunk_id == b.chunk_id
    assert result[0].score == pytest.approx(1 / 62 + 1 / 61)
    assert replace(result[0], score=0) == b
    second.search = lambda query, limit: [replace(a, content="fabricated")]
    with pytest.raises(ValueError, match="不同证据"):
        HybridSearch([first, second]).search("anything")
    second.search = lambda query, limit: [a, a]
    with pytest.raises(ValueError, match="重复片段"):
        HybridSearch([first, second]).search("anything")


def test_real_hybrid_combines_bm25_and_vector_backend(store):
    with QdrantSearch(store, FixtureEmbedding(), path=":memory:") as dense:
        dense.sync()
        result = HybridSearch([store, dense]).search("rain", 1)
        assert result[0].document_id == "indoor"


def test_openai_embedding_reorders_by_input_index_and_checks_dimensions():
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=[0.0, 1.0]),
                SimpleNamespace(index=0, embedding=[1.0, 0.0]),
            ]
        )

    client = SimpleNamespace(
        embeddings=SimpleNamespace(create=create), base_url="https://example.test"
    )
    embedding = OpenAIEmbeddingProvider(client, "configured-model", 2)
    assert embedding.embed_documents(["a", "b"]) == [[1.0, 0.0], [0.0, 1.0]]
    assert "dimensions" not in calls[0]
    requested = OpenAIEmbeddingProvider(
        client, "configured-model", 2, request_dimensions=True
    )
    requested.embed_documents(["a", "b"])
    assert calls[-1]["dimensions"] == 2
    assert requested.model_id != embedding.model_id


def test_fastembed_is_lazy_and_uses_query_and_passage_methods():
    import numpy as np

    embedding = FastEmbedProvider("explicit-model", 2)
    assert embedding._model is None
    embedding._model = SimpleNamespace(
        passage_embed=lambda texts: iter([np.array([1.0, 0.0]) for _ in texts]),
        query_embed=lambda text: iter([np.array([0.0, 1.0])]),
    )
    assert embedding.embed_documents(["text"]) == [[1.0, 0.0]]
    assert embedding.embed_query("question") == [0.0, 1.0]


def test_empty_store_can_sync_and_close_is_explicit(tmp_path):
    empty = RAGStore(str(tmp_path / "empty.db"))
    with QdrantSearch(empty, FixtureEmbedding(), path=":memory:") as search:
        assert search.sync() == 0
        assert search.search("hello") == []
    with pytest.raises(RuntimeError, match="已关闭"):
        search.search("hello")
