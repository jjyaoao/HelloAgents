"""工具契约回归：离线协议、真实临时文件和独立事件循环，不连接模型。"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading

import pytest
from jsonschema import Draft202012Validator

from hello_agents.tools import (
    Tool,
    ToolParameter,
    ToolRegistry,
    ToolResponse,
    tool_action,
)
from hello_agents.tools.builtin import (
    EditTool,
    MultiEditTool,
    RelationTool,
    TodoWriteTool,
    WriteTool,
)
from hello_agents.tools.circuit_breaker import CircuitBreaker
from hello_agents.retrieval import RAGStore, RelationStore
from hello_agents.skills import SkillLoader
from hello_agents.tools.builtin.task_tool import TaskTool
from hello_agents.tools.tool_filter import ReadOnlyFilter
from pydantic import BaseModel
from hello_agents.tools.builtin.calculator import CalculatorTool


@pytest.mark.parametrize(
    "expression, expected", [("2+3*4", 14), ("-1.5", -1.5), ("sqrt(16)", 4)]
)
def test_calculator_numeric_constants_without_deprecated_ast(expression, expected):
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        response = CalculatorTool().run({"input": expression})
    assert response.status.value == "success"
    assert response.data["result"] == expected


@pytest.mark.parametrize("expression", ['"abc"', '"a" * 10', "True", "None"])
def test_calculator_rejects_non_numeric_constants(expression):
    response = CalculatorTool().run({"input": expression})
    assert response.status.value == "error"


def test_to_dict_preserves_legacy_shape_and_supplied_schema():
    assert "json_schema" not in Echo().to_dict()["parameters"][0]

    class Structured(Echo):
        def get_parameters(self):
            return [
                ToolParameter(
                    name="input",
                    type="string",
                    description="value",
                    json_schema={"enum": ["a"]},
                )
            ]

    assert Structured().to_dict()["parameters"][0]["json_schema"] == {"enum": ["a"]}


class NestedItem(BaseModel):
    label: str


def test_action_nested_model_schema_references_resolve():
    class NestedAction(Echo):
        @tool_action("nested")
        def nested(self, items: list[NestedItem]):
            return items

    tool = NestedAction()
    tool.expandable = True
    schema = tool.get_expanded_tools()[0].to_openai_schema()["function"]["parameters"]
    validator = Draft202012Validator(schema)
    assert validator.is_valid({"items": [{"label": "ok"}]})
    assert not validator.is_valid({"items": [{"label": 123}]})


@pytest.mark.parametrize(
    "overrides",
    [
        {"tool_filter": "readonyl"},
        {"tool_filter": None},
        {"agent_type": []},
        {"agent_type": "unknown"},
        {"max_steps": 0},
        {"max_steps": True},
        {"task": "  "},
        {"task": 12},
    ],
)
def test_task_invalid_parameters_rejected_before_factory(overrides):
    calls = []
    task = TaskTool(lambda kind: calls.append(kind))
    result = task.run({"task": "搜索资料", **overrides})
    assert result.error_info["code"] == "INVALID_PARAM"
    assert calls == []


def test_readonly_filter_includes_evidence_without_memory_mutations():
    reads = [
        "rag",
        "rag_search",
        "rag_read",
        "rag_read_document",
        "memory_search",
        "relation_lookup",
    ]
    writes = [
        "memory",
        "memory_add",
        "memory_revise",
        "memory_retract",
        "Write",
        "Bash",
    ]
    assert ReadOnlyFilter().filter(reads + writes) == reads


def test_task_explicit_filter_preserved():
    seen = []

    class Child:
        def run_as_subagent(self, **kwargs):
            seen.append(kwargs)
            return {
                "success": True,
                "summary": "完成",
                "metadata": {"steps": 1, "duration_seconds": 0},
            }

    tool = TaskTool(lambda kind: Child())
    assert (
        tool.run(
            {"task": "检索", "tool_filter": "readonly", "max_steps": 2}
        ).status.value
        == "success"
    )
    assert isinstance(seen[0]["tool_filter"], ReadOnlyFilter)
    assert seen[0]["max_steps_override"] == 2
    assert tool.run({"task": "检索", "tool_filter": "none"}).status.value == "success"
    assert seen[1]["tool_filter"] is None


def test_registry_fork_filters_tools_and_functions_without_parent_mutation():
    registry = ToolRegistry()
    echo = Echo()
    registry.register_tool(echo)
    registry.register_function(lambda query: query, name="read_func")
    registry.register_function(lambda query: query, name="write_func")
    registry.read_metadata_cache["a"] = {"nested": {"mtime": 1}}
    child = registry.fork(name for name in ["echo", "read_func"])
    assert set(child.list_tools()) == {"echo", "read_func"}
    assert child.get_tool("echo") is echo
    assert child.circuit_breaker is registry.circuit_breaker
    assert child.execute_tool("write_func", "x").error_info["code"] == "NOT_FOUND"
    child._functions["read_func"]["description"] = "changed"
    child.read_metadata_cache["a"]["nested"]["mtime"] = 2
    child.unregister("echo")
    child.register_function(lambda query: "new", name="read_func", replace=True)
    assert set(registry.list_tools()) == {"echo", "read_func", "write_func"}
    assert registry._functions["read_func"]["description"] != "changed"
    assert registry.read_metadata_cache["a"]["nested"]["mtime"] == 1
    assert registry.execute_tool("read_func", "original").text == "original"
    assert set(registry.fork().list_tools()) == set(registry.list_tools())
    assert registry.fork([]).list_tools() == []
    with pytest.raises(ValueError, match="未注册"):
        registry.fork(["missing"])
    with pytest.raises(TypeError):
        registry.fork("echo")


class Echo(Tool):
    def __init__(self, name="echo"):
        super().__init__(name, "测试回声")

    def get_parameters(self):
        return [ToolParameter(name="input", type="string", description="输入")]

    def run(self, parameters):
        return ToolResponse.success(parameters["input"])


def test_relation_parameters_are_constructible_and_constrained(tmp_path):
    tool = RelationTool(RelationStore(RAGStore(tmp_path / "r.sqlite")))
    schema = tool.to_openai_schema()["function"]["parameters"]
    validator = Draft202012Validator(schema)
    assert schema["required"] == ["entity"]
    assert set(schema["properties"]) == {"entity", "hops", "limit", "direction"}
    assert validator.is_valid({"entity": "杭州馆", "hops": 3, "direction": "out"})
    assert not validator.is_valid({"entity": "杭州馆", "hops": 4})
    assert not validator.is_valid({"direction": "unknown"})


def test_explicit_schema_is_preserved_without_mutation():
    fragment = {
        "type": "object",
        "properties": {"mode": {"enum": ["read"]}},
        "required": ["mode"],
        "additionalProperties": False,
    }

    class Structured(Echo):
        def get_parameters(self):
            return [
                ToolParameter(
                    name="input",
                    type="object",
                    description="结构",
                    json_schema=fragment,
                )
            ]

    tool = Structured()
    first = tool.to_openai_schema()
    assert (
        first["function"]["parameters"]["properties"]["input"]["additionalProperties"]
        is False
    )
    first["function"]["parameters"]["properties"]["input"]["properties"].clear()
    assert "mode" in fragment["properties"]
    assert (
        "mode"
        in tool.to_openai_schema()["function"]["parameters"]["properties"]["input"][
            "properties"
        ]
    )


@pytest.mark.parametrize("kind", ["edit", "todo"])
def test_object_array_contract_accepts_real_payload_rejects_strings(tmp_path, kind):
    if kind == "edit":
        tool, field, value = (
            MultiEditTool(),
            "edits",
            {"old_string": "a", "new_string": "b"},
        )
        payload = {"path": "a.txt", field: [value]}
    else:
        tool, field, value = (
            TodoWriteTool(project_root=str(tmp_path)),
            "todos",
            {"content": "工作", "status": "pending"},
        )
        payload = {field: [value]}
    validator = Draft202012Validator(tool.to_openai_schema()["function"]["parameters"])
    assert validator.is_valid(payload)
    assert not validator.is_valid({**payload, field: ["not-an-object"]})
    assert not validator.is_valid({**payload, field: [{}]})


def test_action_annotations_preserve_nested_array_types():
    class Actions(Echo):
        def __init__(self):
            super().__init__()
            self.expandable = True

        @tool_action("sum_values")
        def total(self, values: list[int]):
            return sum(values)

    schema = (
        Actions().get_expanded_tools()[0].to_openai_schema()["function"]["parameters"]
    )
    assert schema["properties"]["values"]["items"] == {"type": "integer"}


def test_registry_unique_name_and_explicit_cross_kind_replacement():
    registry = ToolRegistry()
    registry.register_tool(Echo("same"))
    with pytest.raises(ValueError):
        registry.register_function(lambda text: "hidden", name="same")
    assert registry.list_tools() == ["same"]
    assert registry.get_function("same") is None
    registry.register_function(lambda text: "replacement", name="same", replace=True)
    assert registry.get_tool("same") is None
    assert registry.execute_tool("same", "x").text == "replacement"
    with pytest.raises(ValueError):
        registry.register_tool(Echo("same"))
    registry.unregister("same")
    assert registry.list_tools() == []
    assert registry.execute_tool("same", "x").error_info["code"] == "NOT_FOUND"


def test_expanded_registration_is_all_or_nothing():
    class Bundle(Echo):
        def __init__(self):
            super().__init__()
            self.expandable = True

        def get_expanded_tools(self):
            return [Echo("new"), Echo("existing")]

    registry = ToolRegistry()
    registry.register_tool(Echo("existing"))
    with pytest.raises(ValueError):
        registry.register_tool(Bundle())
    assert registry.list_tools() == ["existing"]


def test_schema_failure_is_not_silently_registered():
    class Broken(Echo):
        def get_parameters(self):
            raise ValueError("bad contract")

    registry = ToolRegistry()
    with pytest.raises(ValueError, match="bad contract"):
        registry.register_tool(Broken())
    assert registry.list_tools() == []


def test_async_function_really_awaited_and_sync_rejected():
    calls = []

    async def native(text):
        await asyncio.sleep(0)
        calls.append(text)
        return ToolResponse.partial("partial", data={"source": "fixture://async"})

    registry = ToolRegistry()
    registry.register_function(native)
    assert registry.execute_tool("native", "sync").error_info["code"] == "INVALID_PARAM"
    assert calls == []
    result = asyncio.run(registry.aexecute_tool("native", "async"))
    assert calls == ["async"]
    assert (
        result.status.value == "partial" and result.data["source"] == "fixture://async"
    )


def test_async_action_really_awaited_and_signature_errors_preserved():
    class Actions(Echo):
        def __init__(self):
            super().__init__()
            self.expandable = True

        @tool_action("lookup")
        async def lookup(self, query: str):
            await asyncio.sleep(0)
            return {"query": query}

    registry = ToolRegistry()
    registry.register_tool(Actions())
    assert (
        registry.execute_tool("lookup", {"query": "sync"}).error_info["code"]
        == "INVALID_PARAM"
    )
    result = asyncio.run(registry.aexecute_tool("lookup", {"query": "async"}))
    assert result.data["output"] == {"query": "async"}
    assert (
        asyncio.run(registry.aexecute_tool("lookup", {})).error_info["code"]
        == "INVALID_PARAM"
    )


def test_sync_function_in_async_path_does_not_block_event_loop():
    release = threading.Event()

    def blocking(text):
        return release.wait(timeout=1)

    registry = ToolRegistry()
    registry.register_function(blocking)

    async def run():
        task = asyncio.create_task(registry.aexecute_tool("blocking", "x"))
        await asyncio.sleep(0.01)
        release.set()
        return await task

    assert asyncio.run(run()).data["output"] is True


def test_async_function_failure_participates_in_circuit():
    async def failing(text):
        raise RuntimeError("local failure")

    registry = ToolRegistry(CircuitBreaker(failure_threshold=1))
    registry.register_function(failing)
    assert (
        asyncio.run(registry.aexecute_tool("failing", "x")).error_info["code"]
        == "EXECUTION_ERROR"
    )
    assert (
        asyncio.run(registry.aexecute_tool("failing", "x")).error_info["code"]
        == "CIRCUIT_OPEN"
    )


@pytest.mark.parametrize("kind", ["write", "edit", "multi"])
def test_absolute_external_path_is_successful_after_allowed_mutation(tmp_path, kind):
    root = tmp_path / "root"
    root.mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("alpha", encoding="utf-8")
    tool = {"write": WriteTool, "edit": EditTool, "multi": MultiEditTool}[kind](
        project_root=str(root)
    )
    parameters = {"path": str(target)}
    if kind == "write":
        parameters["content"] = "beta"
    elif kind == "edit":
        parameters.update(old_string="alpha", new_string="beta")
    else:
        parameters["edits"] = [{"old_string": "alpha", "new_string": "beta"}]
    response = tool.run(parameters)
    assert response.status.value == "success"
    assert target.read_text(encoding="utf-8") == "beta"
    assert Path(response.data["backup_path"]).is_absolute()
    assert Path(response.data["backup_path"]).read_text(encoding="utf-8") == "alpha"


def test_fixed_temp_is_untouched_and_rapid_backups_are_distinct(tmp_path):
    existing = tmp_path / "doc.txt.tmp"
    existing.write_text("unrelated", encoding="utf-8")
    target = tmp_path / "doc.txt"
    target.write_text("one", encoding="utf-8")
    tool = WriteTool(project_root=str(tmp_path))
    first = tool.run({"path": "doc.txt", "content": "two"})
    second = tool.run({"path": "doc.txt", "content": "three"})
    assert existing.read_text(encoding="utf-8") == "unrelated"
    assert first.data["backup_path"] != second.data["backup_path"]
    assert (tmp_path / first.data["backup_path"]).read_text(encoding="utf-8") == "one"
    assert (tmp_path / second.data["backup_path"]).read_text(encoding="utf-8") == "two"


@pytest.mark.parametrize("kind", ["write", "edit", "multi"])
def test_replace_failure_leaves_original_and_cleans_only_owned_temp(
    tmp_path, monkeypatch, kind
):
    import hello_agents.tools.builtin.file_tools as module

    target = tmp_path / "doc.txt"
    target.write_text("alpha", encoding="utf-8")
    unrelated = tmp_path / "doc.txt.tmp"
    unrelated.write_text("unrelated", encoding="utf-8")

    def fail(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(module.os, "replace", fail)
    tool = {"write": WriteTool, "edit": EditTool, "multi": MultiEditTool}[kind](
        project_root=str(tmp_path)
    )
    args = {
        "path": "doc.txt",
        "content": "beta",
        "old_string": "alpha",
        "new_string": "beta",
        "edits": [{"old_string": "alpha", "new_string": "beta"}],
    }
    assert tool.run(args).status.value == "error"
    assert target.read_text(encoding="utf-8") == "alpha"
    assert unrelated.read_text(encoding="utf-8") == "unrelated"
    assert list(tmp_path.glob(".doc.txt.*.tmp")) == []


def test_concurrent_writes_do_not_share_temporary_file(tmp_path, monkeypatch):
    import hello_agents.tools.builtin.file_tools as module

    original_replace = module.os.replace
    barrier = threading.Barrier(2)
    temporary_names = []

    def coordinated_replace(source, destination):
        temporary_names.append(str(source))
        barrier.wait(timeout=3)
        return original_replace(source, destination)

    monkeypatch.setattr(module.os, "replace", coordinated_replace)
    tool = WriteTool(project_root=str(tmp_path))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda value: tool.run({"path": "doc.txt", "content": value}),
                ["a" * 1000, "b" * 1000],
            )
        )
    # Windows 上同时 ReplaceFile 可能返回共享冲突；原子替换不承诺写者串行化。
    assert any(result.status.value == "success" for result in results)
    assert all(
        result.status.value == "success"
        or result.error_info["code"] == "PERMISSION_DENIED"
        for result in results
    ), [result.to_dict() for result in results]
    assert len(set(temporary_names)) == 2
    assert (tmp_path / "doc.txt").read_text(encoding="utf-8") in {
        "a" * 1000,
        "b" * 1000,
    }


def test_multiedit_validates_sequential_state_before_writing(tmp_path):
    target = tmp_path / "doc.txt"
    target.write_text("alpha beta", encoding="utf-8")
    tool = MultiEditTool(project_root=str(tmp_path))
    invalid = tool.run(
        {
            "path": "doc.txt",
            "edits": [
                {"old_string": "alpha", "new_string": "beta"},
                {"old_string": "beta", "new_string": "gamma"},
            ],
        }
    )
    assert invalid.error_info["code"] == "INVALID_PARAM"
    assert invalid.context["edit_index"] == 1
    assert target.read_text(encoding="utf-8") == "alpha beta"
    assert not (tmp_path / ".backups").exists()
    valid = tool.run(
        {
            "path": "doc.txt",
            "edits": [
                {"old_string": "alpha", "new_string": "delta"},
                {"old_string": "delta", "new_string": "gamma"},
            ],
        }
    )
    assert valid.status.value == "success"
    assert target.read_text(encoding="utf-8") == "gamma beta"


@pytest.mark.parametrize(
    "metadata",
    ["123", "[a,b]", "name: [a]\ndescription: x", "name: valid\ndescription: ''"],
)
def test_invalid_skill_is_isolated_from_valid_skill(tmp_path, metadata):
    bad = tmp_path / "bad"
    good = tmp_path / "good"
    bad.mkdir()
    good.mkdir()
    (bad / "SKILL.md").write_text(f"---\n{metadata}\n---\nbody", encoding="utf-8")
    (good / "SKILL.md").write_text(
        "---\nname: good\ndescription: valid\n---\nusable", encoding="utf-8"
    )
    loader = SkillLoader(tmp_path)
    assert loader.list_skills() == ["good"]
    assert loader.get_skill("good").body == "usable"
    assert len(loader.diagnostics) == 1 and "bad" in loader.diagnostics[0]["path"]


def test_lazy_skill_validation_and_reload_use_same_rules(tmp_path):
    directory = tmp_path / "skill"
    directory.mkdir()
    path = directory / "SKILL.md"
    path.write_text("---\nname: skill\ndescription: valid\n---\nbody", encoding="utf-8")
    loader = SkillLoader(tmp_path)
    path.write_text("---\n123\n---\nbody", encoding="utf-8")
    assert loader.get_skill("skill") is None
    assert loader.diagnostics
    loader.reload()
    assert loader.list_skills() == [] and len(loader.diagnostics) == 1
