"""本地工具示例行为回归；不调用模型或网络服务。"""

import ast
import asyncio
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import pytest

from hello_agents.tools import ToolRegistry
from hello_agents.tools.response import ToolStatus


ROOT = Path(__file__).resolve().parents[1]


def load_example(name):
    # Only load the example file; hello_agents remains the installed package.
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "examples/tools/custom_tools" / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AdvancedToolTemplate = load_example("advanced_tool_template").AdvancedToolTemplate
CodeFormatterTool = load_example("code_formatter_tool").CodeFormatterTool
ExpandableToolTemplate = load_example("expandable_tool_template").ExpandableToolTemplate


def test_ttl_expires_and_cached_values_are_isolated():
    now, calls = [0.0], []

    async def loader(query):
        calls.append(query)
        return {"items": [len(calls)]}

    tool = AdvancedToolTemplate(loader, cache_ttl=5, clock=lambda: now[0])
    first = tool.run({"query": "杭州"})
    first.data["items"].append(99)
    cached = tool.run({"query": "杭州", "timeout": 0.1})
    assert cached.stats == {"cache_hit": True, "attempts": 0}
    assert cached.data == {"items": [1]}
    now[0] = 5
    refreshed = tool.run({"query": "杭州"})
    assert refreshed.data == {"items": [2]}
    tool.clear_cache()
    assert tool.run({"query": "杭州"}).data == {"items": [3]}


def test_async_timeout_cancels_each_attempt_and_does_not_cache_error():
    starts, exits = [], []

    async def slow(query):
        starts.append(query)
        try:
            await asyncio.sleep(10)
        finally:
            exits.append(query)

    tool = AdvancedToolTemplate(slow, timeout=0.001, retries=1)
    result = asyncio.run(tool.arun({"query": "slow"}))
    assert result.error_info["code"] == "TIMEOUT"
    assert result.stats["attempts"] == 2
    assert len(starts) == len(exits) == 2
    assert not tool._cache


def test_transient_failure_retries_but_cancellation_propagates():
    calls = []

    async def flaky(query):
        calls.append(query)
        if len(calls) == 1:
            raise OSError("temporary")
        return {"ok": True}

    result = asyncio.run(AdvancedToolTemplate(flaky).arun({"query": "test"}))
    assert result.data == {"ok": True} and result.stats["attempts"] == 2

    async def cancelled(query):
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(AdvancedToolTemplate(cancelled).arun({"query": "test"}))


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"query": []},
        {"query": "x", "timeout": True},
        {"query": "x", "timeout": float("nan")},
        {"query": "x", "format": "json"},
    ],
)
def test_query_invalid_params(params):
    assert AdvancedToolTemplate().run(params).error_info["code"] == "INVALID_PARAM"


def test_sync_api_inside_event_loop_refuses_nested_runner():
    async def main():
        assert (
            AdvancedToolTemplate().run({"query": "x"}).error_info["code"]
            == "INVALID_PARAM"
        )

    asyncio.run(main())


def test_formatter_preserves_scopes_import_order_and_string_whitespace():
    code = (
        "events = []  \n"
        'value = """first   \n\n\n\nlast   \n"""\n'
        "if False:\n  import nonexistent_teaching_module\n"
        "def answer():\n  import math\n  return math.floor(2.9)  \n"
    )
    result = CodeFormatterTool().run({"code": code, "max_line_length": 10})
    assert result.status == ToolStatus.SUCCESS
    formatted = result.data["formatted_code"]
    assert ast.dump(ast.parse(code)) == ast.dump(ast.parse(formatted))
    original, cleaned = {}, {}
    exec(code, original)
    exec(formatted, cleaned)
    assert original["value"] == cleaned["value"]
    assert original["answer"]() == cleaned["answer"]() == 2
    assert result.data["long_lines"]
    assert not formatted.startswith("import")
    assert CodeFormatterTool().run({"code": formatted}).data["changed"] is False


@pytest.mark.parametrize(
    "params,code",
    [
        ({"code": "def broken("}, "INVALID_FORMAT"),
        ({"code": "x=1", "indent": 4}, "INVALID_PARAM"),
        ({"code": 1}, "INVALID_PARAM"),
        ({"code": "x=1", "max_line_length": True}, "INVALID_PARAM"),
    ],
)
def test_formatter_rejects_invalid_input(params, code):
    assert CodeFormatterTool().run(params).error_info["code"] == code


def test_storage_persists_and_directories_are_independent(tmp_path):
    first = ExpandableToolTemplate(tmp_path / "one")
    result = first.create("../name-is-data", "预约要求", ["旅行"])
    assert result.status == ToolStatus.SUCCESS
    result.data["resource"]["tags"].append("external")
    restored = ExpandableToolTemplate(tmp_path / "one")
    assert restored.read("../name-is-data").data["resource"]["tags"] == ["旅行"]
    assert ExpandableToolTemplate(tmp_path / "two").list_resources().data["count"] == 0
    assert (
        restored.create("../name-is-data", "duplicate").error_info["code"] == "CONFLICT"
    )
    assert restored.list_resources("旅行").data["count"] == 1
    assert (
        restored.update("../name-is-data", content="", tags=[]).status
        == ToolStatus.SUCCESS
    )
    assert ExpandableToolTemplate(tmp_path / "one").read(
        "../name-is-data", False
    ).data == {"resource": {"content": ""}}
    assert (
        restored.delete("../name-is-data", confirm="true").error_info["code"]
        == "INVALID_PARAM"
    )
    assert restored.delete("../name-is-data", confirm=True).status == ToolStatus.SUCCESS
    assert (
        ExpandableToolTemplate(tmp_path / "one")
        .read("../name-is-data")
        .error_info["code"]
        == "NOT_FOUND"
    )
    assert not (tmp_path / "name-is-data").exists()


def test_expandable_registry_schema_and_validation(tmp_path):
    registry = ToolRegistry()
    tool = ExpandableToolTemplate(tmp_path)
    registry.register_tool(tool)
    assert len(registry.list_tools()) == 5
    schema = registry.get_tool("expandable_create").to_openai_schema()
    assert "array" in str(schema["function"]["parameters"]["properties"]["tags"])
    assert (
        registry.execute_tool("expandable_create", {"name": "", "content": "x"}).status
        == ToolStatus.ERROR
    )
    assert (
        registry.execute_tool(
            "expandable_create", {"name": "x", "content": "x", "tags": "travel"}
        ).status
        == ToolStatus.ERROR
    )
    assert (
        registry.execute_tool(
            "expandable_create", {"name": "x", "content": "x", "tags": ["travel"]}
        ).status
        == ToolStatus.SUCCESS
    )
    assert (
        registry.execute_tool("expandable_update", {"name": "x"}).error_info["code"]
        == "INVALID_PARAM"
    )
    assert (
        registry.execute_tool("expandable_list", {"filter_tag": "travel"}).data["count"]
        == 1
    )


@pytest.mark.parametrize(
    "module",
    ["advanced_tool_template", "code_formatter_tool", "expandable_tool_template"],
)
def test_module_entrypoint_runs_offline(module, tmp_path):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    for key in ("LLM_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
        env.pop(key, None)
    script = (
        "import hello_agents, runpy, sys; "
        "sys.path.insert(0, sys.argv[1]); "
        "runpy.run_module(sys.argv[2], run_name='__main__')"
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-c",
            script,
            str(ROOT),
            "examples.tools.custom_tools." + module,
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert '"status":' in completed.stdout
