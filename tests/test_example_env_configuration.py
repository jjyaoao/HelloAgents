"""Examples load .env before selecting services; existing environment wins."""

import json
import sys

import httpx
import pytest


@pytest.mark.parametrize("override_model", [None, "process-model"])
def test_embedding_api_example_loads_dotenv(tmp_path, monkeypatch, override_model):
    pytest.importorskip("qdrant_client")
    import openai
    from examples.retrieval import qdrant_retrieval_demo as demo

    monkeypatch.chdir(tmp_path)
    for key in ("EMBEDDING_API_KEY", "EMBEDDING_BASE_URL", "EMBEDDING_MODEL", "EMBEDDING_DIMENSION"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        "EMBEDDING_API_KEY=offline-test-key\n"
        "EMBEDDING_BASE_URL=https://embedding.example.invalid/v1\n"
        "EMBEDDING_MODEL=dotenv-model\nEMBEDDING_DIMENSION=3\n",
        encoding="utf-8",
    )
    if override_model:
        monkeypatch.setenv("EMBEDDING_MODEL", override_model)
    calls = []

    def respond(request):
        payload = json.loads(request.content)
        calls.append(payload)
        assert request.url.path == "/v1/embeddings"
        assert request.headers["authorization"] == "Bearer offline-test-key"
        return httpx.Response(200, json={
            "object": "list", "model": payload["model"],
            "data": [{"object": "embedding", "index": i, "embedding": [1.0, 2.0, 3.0]}
                     for i, _ in enumerate(payload["input"])],
            "usage": {"prompt_tokens": len(payload["input"]), "total_tokens": len(payload["input"])},
        })

    original_client = openai.OpenAI
    clients = []

    def make_client(**kwargs):
        client = original_client(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond)))
        clients.append(client)
        return client

    def no_local_model(*args, **kwargs):
        pytest.fail("API route must not load FastEmbed")

    monkeypatch.setattr(openai, "OpenAI", make_client)
    monkeypatch.setattr(demo, "FastEmbedProvider", no_local_model)
    monkeypatch.setattr(sys, "argv", ["demo", "--provider", "openai", "--workspace", str(tmp_path / "result")])
    demo.main()
    assert calls and all(call["model"] == (override_model or "dotenv-model") for call in calls)
    assert all(client.is_closed() for client in clients)
    report = json.loads((tmp_path / "result/retrieval-report.json").read_text(encoding="utf-8"))
    assert report["stale_index_rejected"] is True
    assert report["updated_evidence"]


@pytest.mark.parametrize("override_model", [None, "process-model"])
def test_graphrag_live_loads_dotenv_before_constructing_model(tmp_path, monkeypatch, override_model):
    import os
    from examples.retrieval import graphrag_demo as demo

    monkeypatch.chdir(tmp_path)
    for key in ("LLM_MODEL_ID", "LLM_API_KEY", "LLM_BASE_URL", "GRAPH_LLM_KWARGS"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        "LLM_MODEL_ID=dotenv-model\nLLM_API_KEY=offline-test-key\n"
        "LLM_BASE_URL=https://model.example.invalid/v1\n",
        encoding="utf-8",
    )
    if override_model:
        monkeypatch.setenv("LLM_MODEL_ID", override_model)

    class ModelConfigurationVerified(Exception):
        pass

    def inspect_model():
        assert os.environ["LLM_MODEL_ID"] == (override_model or "dotenv-model")
        assert os.environ["LLM_API_KEY"] == "offline-test-key"
        assert os.environ["LLM_BASE_URL"] == "https://model.example.invalid/v1"
        raise ModelConfigurationVerified

    monkeypatch.setattr(demo, "HelloAgentsLLM", inspect_model)
    monkeypatch.setattr(sys, "argv", ["demo", "--live"])
    with pytest.raises(ModelConfigurationVerified):
        demo.main()
