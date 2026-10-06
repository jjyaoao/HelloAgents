"""公开示例的执行验收；不连接模型服务。"""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import hello_agents

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted(
    path.relative_to(ROOT).with_suffix("").as_posix().replace("/", ".")
    for path in (ROOT / "examples").rglob("*.py")
    if not path.name.startswith("_")
    and path.name
    not in {
        "fastapi_sse_server.py",
        "test_sse_client.py",
        "mcp_server.py",
        "qdrant_retrieval_demo.py",
        "semantic_memory_demo.py",
        "cloud_retrieval_demo.py",  # Requires a real cloud service; validated separately below.
    }
)


@pytest.mark.parametrize("module", EXAMPLES)
def test_example_runs_offline(module, tmp_path):
    if module == "examples.retrieval.graphrag_demo":
        pytest.importorskip("igraph")
        pytest.importorskip("leidenalg")
    if module == "examples.tools.mcp_agent_demo":
        pytest.importorskip("mcp")
        pytest.importorskip("jsonschema")
    # 先从当前测试环境加载框架，再加入 examples 所在源码根目录。
    runner = (
        "import sys,runpy,httpx; "
        f"sys.path.insert(0, {str(Path(hello_agents.__file__).resolve().parents[1])!r}); import hello_agents; "
        f"sys.path.insert(0, {str(ROOT)!r}); "
        'httpx.Client.send=httpx.AsyncClient.send=lambda *a,**k: (_ for _ in ()).throw(RuntimeError("offline example attempted model HTTP request")); '
        f'runpy.run_module({module!r},run_name="__main__")'
    )
    env = dict(
        os.environ,
        PYTHONUTF8="1",
        PYTHONIOENCODING="utf-8",
        LLM_MODEL_ID="offline-only",
        LLM_API_KEY="test-key",
        LLM_BASE_URL="http://127.0.0.1:9/v1",
        TEMP=str(tmp_path),
        TMP=str(tmp_path),
    )
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", runner],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=75,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stderr


def test_todo_clear_persists(tmp_path):
    from hello_agents.tools.builtin import TodoWriteTool

    tool = TodoWriteTool(persistence_dir=str(tmp_path))
    tool.run({"todos": [{"content": "旅行预算", "status": "pending"}]})
    assert tool.current_todos.todos
    tool.run({"action": "clear"})
    loaded = TodoWriteTool(persistence_dir=str(tmp_path))
    assert loaded.current_todos.todos == []


def test_devlog_schema_and_invalid_action(tmp_path):
    from hello_agents.tools.builtin import DevLogTool
    from hello_agents.tools.errors import ToolErrorCode

    tool = DevLogTool(
        session_id="test", agent_name="test", persistence_dir=str(tmp_path)
    )
    schema = tool.to_openai_schema()["function"]["parameters"]
    assert schema["properties"]["action"]["enum"] == [
        "append",
        "read",
        "summary",
        "clear",
    ]
    result = tool.run({"action": "not-an-action"})
    assert result.error_info["code"] == ToolErrorCode.INVALID_PARAM


@pytest.mark.parametrize("kind", ["simple", "react", "reflection", "plan"])
def test_sse_current_api(kind, monkeypatch):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    monkeypatch.syspath_prepend(str(ROOT))
    monkeypatch.delenv("HELLOAGENTS_DEMO_LIVE", raising=False)
    from examples.web.fastapi_sse_server import create_app, build_agent

    agents = []

    def factory(kind):
        agent = build_agent(kind)
        agents.append(agent)
        return agent

    client = TestClient(create_app(factory))
    for _ in range(2):
        response = client.post(
            "/agent/stream", json={"input": "你好", "agent_type": kind}
        )
        assert response.status_code == 200
        events = [
            json.loads(line[5:])
            for line in response.text.splitlines()
            if line.startswith("data:")
        ]
        assert events[0]["type"] == "agent_start"
        assert events[-1]["type"] == "agent_finish"
        assert events[-1]["data"]["status"] == "completed"
    assert agents[0] is not agents[1]
    assert (
        client.post("/agent/stream", json={"input": "", "agent_type": kind}).status_code
        == 422
    )
    assert client.get("/").status_code == 200


def test_cloud_example_explains_missing_configuration(tmp_path):
    """A cloud-only example should guide setup, not be treated as an offline demo."""
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    env.pop("QDRANT_URL", None)
    env.pop("QDRANT_API_KEY", None)
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "examples.retrieval.cloud_retrieval_demo"],
        cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert result.returncode == 2
    assert "QDRANT_URL" in result.stderr and "QDRANT_API_KEY" in result.stderr
    assert "docs/cloud-retrieval-guide.md" in result.stderr
    assert "Traceback" not in result.stderr
