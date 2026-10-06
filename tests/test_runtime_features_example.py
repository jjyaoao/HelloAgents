"""执行公开离线示例和标为无需密钥的文档片段；不连接真实模型。"""

import importlib.util
import json
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "runtime_features", ROOT / "examples/agents/runtime_features.py"
)
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)


def test_runtime_features_persists_pairs_and_exposes_outcomes(tmp_path):
    result = example.run_demo(tmp_path)
    assert result["first_run"]["status"] == "completed"
    assert result["first_run"]["model_calls"] == 2
    assert result["first_run"]["tool_calls"] == 1
    assert result["statuses"] == {
        "limit": "max_iterations",
        "output": "output_limit",
        "error": "failed",
    }
    assert result["memory_old_status"] == "superseded"
    assert result["memory_current_status"] == "retracted"
    assert result["other_user_records"] == 0
    assert result["resumed_tool_pair"]
    assert result["tool_result"]["data"]["routes"][0]["walking_km"] == 3
    assert result["interrupted_resume"]["interrupted_status"] == "cancelled"
    assert result["interrupted_resume"]["resumed_status"] == "completed"
    assert result["interrupted_resume"]["tool_receipt_preserved"]
    assert result["interrupted_resume"]["writes_this_run"] == 1
    assert result["interrupted_resume"]["resume_tool_calls"] == 0
    assert (tmp_path / "confirmed-note.txt").read_text(
        encoding="utf-8"
    ).splitlines() == ["已确认步行偏好"]
    saved = json.loads(Path(result["session_path"]).read_text(encoding="utf-8"))
    native = [item["metadata"]["model_message"] for item in saved["history"]]
    assert any(item.get("tool_call_id") == "route-1" for item in native)
    assert any(
        item.get("tool_calls", [{}])[0].get("id") == "route-1" for item in native
    )
    assert result["context"]["tool_schema_tokens"] > 0
    assert result["context"]["selected"]


@pytest.mark.parametrize(
    "document",
    [
        "async-agent-guide.md",
        "streaming-sse-guide.md",
        "component-composition-guide.md",
        "session-persistence-guide.md",
    ],
)
def test_documented_offline_python_blocks(document, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # 示例模块只在源码树中提供；安装后的实际 Agent/Store 仍通过公开接口使用。
    monkeypatch.syspath_prepend(str(ROOT))
    source = (ROOT / "docs" / document).read_text(encoding="utf-8-sig")
    namespace = {"__name__": "documented_example"}
    executed = 0
    for index, block in enumerate(re.findall(r"```python\n(.*?)\n```", source, re.S)):
        if "from fastapi" in block:
            # Web 适配明确需要额外依赖和真实 LLM；这里只检验其 Python 语法。
            compile(block, f"{document}:{index}", "exec")
            continue
        exec(compile(block, f"{document}:{index}", "exec"), namespace)
        executed += 1
    assert executed >= (1 if document == "session-persistence-guide.md" else 2)


@pytest.mark.parametrize("document", ["rag-guide.md", "memory-guide.md"])
def test_storage_guides_actual_examples(document, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = (ROOT / "docs" / document).read_text(encoding="utf-8-sig")
    namespace = {"__name__": "documented_example"}
    executed = 0
    for index, block in enumerate(re.findall(r"```python\n(.*?)\n```", source, re.S)):
        if block.startswith(("RAGStore(path)", "MemoryStore(path,")):
            continue  # API 签名清单，不是可执行调用。
        exec(compile(block, f"{document}:{index}", "exec"), namespace)
        executed += 1
    assert executed >= 3


def test_context_first_input_example(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = (ROOT / "docs/context-engineering-guide.md").read_text(
        encoding="utf-8-sig"
    )
    block = re.findall(r"```python\n(.*?)\n```", source, re.S)[0]
    namespace = {}
    exec(block, namespace)
    result = namespace["result"]
    assert result.diagnostics["selected"][0]["source"] == "user:message-1"
    assert result.diagnostics["estimated_tokens"] <= result.diagnostics["budget"]
