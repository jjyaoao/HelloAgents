"""真实 SDK 的 HTTP 序列化契约；云端响应为模拟，不证明账号连通性。"""

import json

import httpx
import pytest

pytest.importorskip("qdrant_client")
from qdrant_client import QdrantClient, models
from hello_agents.retrieval import (
    QdrantCloudInference,
    QdrantSearch,
    RAGStore,
    IndexStaleError,
)
from hello_agents.memory import MemoryStore, SemanticMemorySearch


@pytest.fixture
def cloud(monkeypatch):
    local = QdrantClient(":memory:")
    requests = []
    indexes = {}
    failure = {"upload": False}

    def handle(request):
        requests.append(request)
        assert request.headers["api-key"] == "test-key"
        body = json.loads(request.content) if request.content else {}
        path = request.url.path
        name = path.split("/")[2] if path.startswith("/collections/") else None
        if path in ("", "/"):
            return httpx.Response(200, json={"title": "qdrant", "version": "1.19.2"})
        if path.endswith("/exists"):
            result = {"exists": local.collection_exists(name)}
        elif path == f"/collections/{name}" and request.method == "PUT":
            result = local.create_collection(
                name, vectors_config=models.VectorParams(**body["vectors"])
            )
        elif path == f"/collections/{name}":
            result = local.get_collection(name).model_dump(mode="json")
            result["payload_schema"] = {
                field: {"data_type": "keyword", "points": 0}
                for field in indexes.get(name, set())
            }
        elif path.endswith("/index") and request.method == "PUT":
            assert body["field_schema"] == "keyword"
            indexes.setdefault(name, set()).add(body["field_name"])
            result = {"operation_id": 0, "status": "completed"}
        elif path.endswith("/points") and request.method == "POST":
            result = [
                r.model_dump(mode="json")
                for r in local.retrieve(
                    name,
                    ids=body["ids"],
                    with_payload=body.get("with_payload", True),
                    with_vectors=body.get("with_vector", False),
                )
            ]
        elif path.endswith("/points") and request.method == "PUT":
            if failure["upload"]:
                return httpx.Response(
                    400, json={"status": {"error": "inference unavailable"}, "time": 0}
                )
            points = []
            for point in body["points"]:
                if isinstance(point["vector"], dict):
                    assert point["vector"]["model"] == "intfloat/multilingual-e5-small"
                    assert point["vector"]["text"]
                    point["vector"] = [1.0] + [0.0] * 383
                points.append(models.PointStruct(**point))
            result = local.upsert(name, points).model_dump(mode="json")
        elif path.endswith("/points/query"):
            assert {c["key"] for c in body["filter"]["must"]} <= indexes.get(name, set())
            assert body["query"]["nearest"]["model"] == "intfloat/multilingual-e5-small"
            result = local.query_points(
                name,
                query=[1.0] + [0.0] * 383,
                query_filter=models.Filter(**body["filter"]),
                limit=body["limit"],
                with_payload=True,
                with_vectors=False,
            ).model_dump(mode="json")
        elif path.endswith("/points/delete"):
            result = local.delete(name, models.FilterSelector(**body)).model_dump(
                mode="json"
            )
        else:
            raise AssertionError((request.method, path, body))
        return httpx.Response(200, json={"result": result, "status": "ok", "time": 0})

    original = QdrantClient

    def client(**kwargs):
        assert kwargs["cloud_inference"] is True
        return original(
            **kwargs, transport=httpx.MockTransport(handle), check_compatibility=False
        )

    monkeypatch.setattr("qdrant_client.QdrantClient", client)
    yield (
        {"url": "https://cloud.example.test", "api_key": "test-key"},
        requests,
        failure,
    )
    local.close()


def test_cloud_documents_are_sent_as_text_and_failed_inference_never_publishes(
    tmp_path, cloud
):
    options, requests, failure = cloud
    store = RAGStore(str(tmp_path / "rag.sqlite"))
    store.add_document("雨天参观博物馆", "source:rain", document_id="rain")
    with QdrantSearch(store, QdrantCloudInference(), **options) as search:
        assert search.sync() == 1 and search.sync() == 0
        assert search.search("雨天活动", 1)[0].source == "source:rain"
        store.add_document("晴天去湖边", "source:lake", document_id="lake")
        failure["upload"] = True
        from qdrant_client.http.exceptions import UnexpectedResponse

        with pytest.raises(UnexpectedResponse):
            search.sync()
        with pytest.raises(IndexStaleError):
            search.search("雨天活动")
        failure["upload"] = False
        assert search.sync() == 2
        assert len(search.search("活动")) == 2
    assert any(b'"model"' in request.content for request in requests)
    created = [json.loads(r.content)["field_name"] for r in requests if r.url.path.endswith("/index")]
    assert set(created) == {"namespace", "kind", "generation", "model_id"}
    with QdrantSearch(store, QdrantCloudInference(), **options) as reopened:
        assert reopened.sync() == 0
    assert len([r for r in requests if r.url.path.endswith("/index")]) == len(created)


def test_cloud_memory_correction_and_retraction_use_same_protocol(tmp_path, cloud):
    options, _, _ = cloud
    store = MemoryStore(str(tmp_path / "memory.sqlite"), "alice", "travel")
    record = store.add("步行八公里", "user:1")
    with SemanticMemorySearch(
        store, QdrantCloudInference(), hybrid=False, **options
    ) as search:
        search.sync()
        updated = store.revise(record.memory_id, "步行五公里", "user:2")
        with pytest.raises(IndexStaleError):
            search.search("步行")
        search.sync()
        assert [r.memory_id for r in search.search("步行")] == [updated.memory_id]
        store.retract(updated.memory_id)
        search.sync()
        assert search.search("步行") == []


@pytest.mark.parametrize(
    "options",
    [
        {"path": ":memory:"},
        {"client": object()},
        {"url": "http://localhost:6333", "api_key": "test"},
        {"url": "https://cloud.example.test"},
    ],
)
def test_cloud_config_rejects_missing_key_or_local_destination_before_network(
    tmp_path, options
):
    with pytest.raises(ValueError):
        QdrantSearch(
            RAGStore(str(tmp_path / "r.sqlite")), QdrantCloudInference(), **options
        )


@pytest.mark.parametrize(
    "kwargs", [{"model": ""}, {"dimension": 0}, {"dimension": True}]
)
def test_invalid_cloud_model_configuration(kwargs):
    with pytest.raises(ValueError):
        QdrantCloudInference(**kwargs)
