"""工具 JSON Schema 生成测试"""

from hello_agents.agents.react_agent import ReActAgent
from hello_agents.core.config import Config
from hello_agents.tools.builtin.devlog_tool import DevLogTool
from hello_agents.tools.builtin.file_tools import MultiEditTool
from hello_agents.tools.builtin.todowrite_tool import TodoWriteTool
from hello_agents.tools.registry import ToolRegistry


class DummyLLM:
    """用于 schema 测试的轻量 LLM 桩对象"""

    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.model = model


class TestToolSchemaGeneration:
    """测试工具 schema 构建"""

    def test_todowrite_to_openai_schema_includes_array_items(self, tmp_path):
        """TodoWrite 的数组参数应包含 items 定义"""
        tool = TodoWriteTool(project_root=str(tmp_path), persistence_dir="todos")

        schema = tool.to_openai_schema()
        todo_param = schema["function"]["parameters"]["properties"]["todos"]
        action_param = schema["function"]["parameters"]["properties"]["action"]

        assert todo_param["type"] == "array"
        assert todo_param["items"]["type"] == "object"
        assert todo_param["items"]["properties"]["status"]["enum"] == [
            "pending",
            "in_progress",
            "completed"
        ]
        assert action_param["enum"] == ["create", "update", "clear"]

    def test_multiedit_to_openai_schema_preserves_object_array_shape(self, tmp_path):
        """MultiEdit 的 edits 参数应保留对象数组结构"""
        tool = MultiEditTool(project_root=str(tmp_path), working_dir=str(tmp_path))

        schema = tool.to_openai_schema()
        edits_param = schema["function"]["parameters"]["properties"]["edits"]

        assert edits_param["type"] == "array"
        assert edits_param["items"]["type"] == "object"
        assert edits_param["items"]["required"] == ["old_string", "new_string"]
        assert edits_param["items"]["properties"]["old_string"]["type"] == "string"
        assert edits_param["items"]["properties"]["new_string"]["type"] == "string"

    def test_devlog_to_openai_schema_includes_enum(self, tmp_path):
        """DevLog 的枚举参数应保留在 schema 中"""
        tool = DevLogTool(
            session_id="s-test",
            agent_name="schema-test",
            project_root=str(tmp_path),
            persistence_dir="devlogs"
        )

        schema = tool.to_openai_schema()
        action_param = schema["function"]["parameters"]["properties"]["action"]
        category_param = schema["function"]["parameters"]["properties"]["category"]

        assert action_param["enum"] == ["append", "read", "summary", "clear"]
        assert "decision" in category_param["enum"]

    def test_react_agent_builds_todowrite_schema_with_items(self, tmp_path):
        """ReActAgent 组装工具 schema 时不应丢失数组 items"""
        registry = ToolRegistry()
        registry.register_tool(
            TodoWriteTool(project_root=str(tmp_path), persistence_dir="todos")
        )
        agent = ReActAgent(
            name="schema-agent",
            llm=DummyLLM(),
            tool_registry=registry,
            config=Config(
                trace_enabled=False,
                skills_enabled=False,
                session_enabled=False,
                subagent_enabled=False,
                devlog_enabled=False,
                todowrite_enabled=False
            )
        )

        schemas = agent._build_tool_schemas()
        todo_schema = next(
            schema for schema in schemas
            if schema["function"]["name"] == "TodoWrite"
        )
        todo_param = todo_schema["function"]["parameters"]["properties"]["todos"]

        assert todo_param["type"] == "array"
        assert todo_param["items"]["type"] == "object"
