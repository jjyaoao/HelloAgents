"""真实 SQLite 与工具协议测试；不访问网络、不调用模型。"""

import json
from pathlib import Path
import subprocess
import sys

import pytest

from hello_agents.memory import MemoryStore
from hello_agents.retrieval import RAGStore
from hello_agents.tools import ToolRegistry, ToolStatus
from hello_agents.tools.builtin import MemoryTool, RAGTool


def test_chinese_retrieval_offsets_versions_and_reopen(tmp_path):
    path = tmp_path / "rag.db"
    store = RAGStore(path)
    original = "杭州旅行🧳\n  博物馆周一闭馆。\n平日无需预约；节假日必须提前预约。"
    store.add_document(
        original, "notice://museum", document_id="museum", chunk_size=22, overlap=6
    )
    results = store.search("博物馆预约")
    assert results
    for result in results:
        assert original[result.start : result.end] == result.content
        assert RAGStore(path).read_chunk(result.chunk_id).content == result.content
    old = results[0]
    store.add_document(
        "博物馆每天需要预约。", "notice://museum", "2", document_id="museum"
    )
    assert {r.version for r in store.search("博物馆预约")} == {"2"}
    assert store.read_chunk(old.chunk_id).version == "1"
    store.add_document(original, "notice://museum", document_id="museum")
    assert {r.version for r in store.search("博物馆")} == {"2"}
    with pytest.raises(ValueError):
        store.add_document("修改旧版", "notice://museum", document_id="museum")
    path.rename(tmp_path / "closed.db")  # Windows 上验证不存在长寿命打开连接。


@pytest.mark.parametrize(
    "size,overlap", [(0, 0), (10, 10), (10, -1), (10, 11), (True, 0)]
)
def test_invalid_chunking_writes_nothing(tmp_path, size, overlap):
    store = RAGStore(tmp_path / "rag.db")
    with pytest.raises(ValueError):
        store.add_document(
            "有效资料", "fixture://source", chunk_size=size, overlap=overlap
        )
    assert store.search("有效资料") == []


def test_rag_no_match_and_tools(tmp_path):
    store = RAGStore(tmp_path / "rag.db")
    store.add_document("杭州公交出行", "fixture://bus")
    assert store.search("zzzz") == []
    registry = ToolRegistry()
    registry.register_tool(RAGTool(store))
    assert registry.list_tools() == ["rag_read", "rag_read_document", "rag_search"]
    response = registry.execute_tool("rag_search", {"query": "杭州公交"})
    assert response.status == ToolStatus.SUCCESS
    hit = response.data["results"][0]
    read = registry.execute_tool("rag_read", {"chunk_id": hit["chunk_id"]})
    assert read.data["result"]["source"] == "fixture://bus"
    assert (
        registry.execute_tool("rag_read", {"chunk_id": "unknown"}).error_info["code"]
        == "NOT_FOUND"
    )
    assert (
        registry.execute_tool("rag_search", {"query": "", "limit": 0}).error_info[
            "code"
        ]
        == "INVALID_PARAM"
    )


def test_memory_scope_revision_retraction_and_process(tmp_path):
    path = tmp_path / "memory.db"
    store = MemoryStore(path, "alice", "hangzhou")
    old = store.add("每天步行不超过八公里", "user:message-1")
    other = MemoryStore(path, "bob", "hangzhou")
    other_task = MemoryStore(path, "alice", "other")
    for isolated in (other, other_task):
        assert isolated.search() == []
        for operation in (
            lambda: isolated.get(old.memory_id),
            lambda: isolated.revise(old.memory_id, "恶意覆盖", "x"),
            lambda: isolated.retract(old.memory_id),
        ):
            with pytest.raises(KeyError):
                operation()
    revised = store.revise(old.memory_id, "每天步行不超过五公里", "user:message-2")
    assert revised.supersedes == old.memory_id
    assert store.get(old.memory_id, include_inactive=True).status == "superseded"
    assert [r.memory_id for r in store.search("步行")] == [revised.memory_id]
    with pytest.raises(ValueError):
        store.revise(old.memory_id, "重复修订", "source")
    code = "from hello_agents.memory import MemoryStore; import sys; print(MemoryStore(sys.argv[1],'alice','hangzhou').search()[0].memory_id)"
    output = subprocess.check_output(
        [sys.executable, "-X", "utf8", "-c", code, str(path)], text=True
    )
    assert output.strip() == revised.memory_id
    withdrawn = store.retract(revised.memory_id)
    assert store.search() == []
    assert store.retract(revised.memory_id) == withdrawn
    with pytest.raises(ValueError):
        withdrawn.to_context_packet()
    assert MemoryStore(path, "alice", "hangzhou").search() == []


def test_memory_tools_do_not_expose_or_accept_scope(tmp_path):
    store = MemoryStore(tmp_path / "memory.db", "alice", "trip")
    tool = MemoryTool(store)
    registry = ToolRegistry()
    registry.register_tool(tool)
    for expanded in registry.get_all_tools():
        schema = expanded.to_openai_schema()["function"]["parameters"]["properties"]
        assert "user_id" not in schema and "task_id" not in schema
    response = registry.execute_tool(
        "memory_add", {"content": "偏好历史", "source": "user:1", "user_id": "bob"}
    )
    assert response.error_info["code"] == "INVALID_PARAM"
    assert store.search() == []
    added = registry.execute_tool(
        "memory_add", {"content": "偏好历史", "source": "user:1"}
    )
    assert added.data["records"][0]["user_id"] == "alice"
    assert tool.run({"action": "search"}).status == ToolStatus.SUCCESS
    assert (
        tool.run({"action": "retract", "memory_id": ""}).error_info["code"]
        == "INVALID_PARAM"
    )


@pytest.mark.parametrize(
    "content,source,kind", [("", "s", "fact"), ("x", "", "fact"), ("x", "s", "magic")]
)
def test_invalid_memory_rejected(tmp_path, content, source, kind):
    store = MemoryStore(tmp_path / "memory.db", "u", "t")
    with pytest.raises(ValueError):
        store.add(content, source, kind)
    assert store.search() == []


def test_invalid_identifiers_are_parameter_errors(tmp_path):
    rag = RAGStore(tmp_path / "rag.db")
    with pytest.raises(ValueError):
        rag.add_document("预约说明", "fixture://notice", document_id="")
    with pytest.raises(ValueError):
        rag.read_chunk("")
    memory = MemoryStore(tmp_path / "memory.db", "u", "t")
    with pytest.raises(ValueError):
        memory.get("")
    response = MemoryTool(memory).run(
        {"action": "add", "content": "x", "source": "s", "kind": []}
    )
    assert response.error_info["code"] == "INVALID_PARAM"
