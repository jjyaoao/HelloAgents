"""DevLogTool 测试套件

测试覆盖：
1. 数据模型（DevLogEntry, DevLogStore）
2. 工具操作（append, read, summary, clear）
3. 持久化机制
4. Agent 集成
5. 过滤查询
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from hello_agents.tools.builtin.devlog_tool import (
    DevLogTool,
    DevLogEntry,
    DevLogStore,
    CATEGORIES
)
from hello_agents.tools.response import ToolResponse, ToolStatus
from hello_agents.tools.errors import ToolErrorCode
from hello_agents import ReActAgent, ToolRegistry
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config
from dotenv import load_dotenv
load_dotenv()

class TestDevLogEntry:
    """测试 DevLogEntry 数据模型"""

    def test_create_entry(self):
        """测试创建日志条目"""
        entry = DevLogEntry.create(
            category="decision",
            content="选择使用 Redis",
            metadata={"tags": ["cache"]}
        )

        assert entry.id.startswith("log-")
        assert entry.category == "decision"
        assert entry.content == "选择使用 Redis"
        assert entry.metadata["tags"] == ["cache"]
        assert isinstance(entry.timestamp, str)

    def test_entry_to_dict(self):
        """测试转换为字典"""
        entry = DevLogEntry.create("issue", "API 超时")
        data = entry.to_dict()

        assert data["category"] == "issue"
        assert data["content"] == "API 超时"
        assert "id" in data
        assert "timestamp" in data

    def test_entry_from_dict(self):
        """测试从字典创建"""
        data = {
            "id": "log-test",
            "timestamp": "2026-02-20T12:00:00",
            "category": "solution",
            "content": "增加超时时间",
            "metadata": {"step": 5}
        }
        entry = DevLogEntry.from_dict(data)

        assert entry.id == "log-test"
        assert entry.category == "solution"
        assert entry.metadata["step"] == 5


class TestDevLogStore:
    """测试 DevLogStore 存储引擎"""

    def test_create_store(self):
        """测试创建存储"""
        store = DevLogStore.create("s-test-001", "TestAgent")

        assert store.session_id == "s-test-001"
        assert store.agent_name == "TestAgent"
        assert len(store.entries) == 0

    def test_append_entry(self):
        """测试追加日志"""
        store = DevLogStore.create("s-test-002", "TestAgent")
        entry = DevLogEntry.create("decision", "使用 PostgreSQL")

        store.append(entry)

        assert len(store.entries) == 1
        assert store.entries[0].content == "使用 PostgreSQL"

    def test_filter_by_category(self):
        """测试按类别过滤"""
        store = DevLogStore.create("s-test-003", "TestAgent")
        store.append(DevLogEntry.create("decision", "决策1"))
        store.append(DevLogEntry.create("issue", "问题1"))
        store.append(DevLogEntry.create("decision", "决策2"))

        filtered = store.filter_entries(category="decision")

        assert len(filtered) == 2
        assert all(e.category == "decision" for e in filtered)

    def test_filter_by_tags(self):
        """测试按标签过滤"""
        store = DevLogStore.create("s-test-004", "TestAgent")
        store.append(DevLogEntry.create("decision", "决策1", {"tags": ["cache", "redis"]}))
        store.append(DevLogEntry.create("decision", "决策2", {"tags": ["database"]}))
        store.append(DevLogEntry.create("issue", "问题1", {"tags": ["cache"]}))

        filtered = store.filter_entries(tags=["cache"])

        assert len(filtered) == 2
        assert all("cache" in e.metadata.get("tags", []) for e in filtered)

    def test_filter_with_limit(self):
        """测试限制数量"""
        store = DevLogStore.create("s-test-005", "TestAgent")
        for i in range(10):
            store.append(DevLogEntry.create("progress", f"进展{i}"))

        filtered = store.filter_entries(limit=3)

        assert len(filtered) == 3
        # 应该返回最新的 3 条
        assert filtered[-1].content == "进展9"

    def test_get_stats(self):
        """测试统计信息"""
        store = DevLogStore.create("s-test-006", "TestAgent")
        store.append(DevLogEntry.create("decision", "决策1"))
        store.append(DevLogEntry.create("decision", "决策2"))
        store.append(DevLogEntry.create("issue", "问题1"))

        stats = store.get_stats()

        assert stats["total_entries"] == 3
        assert stats["by_category"]["decision"] == 2
        assert stats["by_category"]["issue"] == 1

    def test_generate_summary(self):
        """测试生成摘要"""
        store = DevLogStore.create("s-test-007", "TestAgent")
        store.append(DevLogEntry.create("decision", "决策1"))
        store.append(DevLogEntry.create("issue", "问题1"))

        summary = store.generate_summary()

        assert "2 条日志" in summary
        assert "decision" in summary
        assert "issue" in summary

    def test_store_serialization(self):
        """测试存储序列化"""
        store = DevLogStore.create("s-test-008", "TestAgent")
        store.append(DevLogEntry.create("decision", "决策1"))

        # 转换为字典
        data = store.to_dict()
        assert data["session_id"] == "s-test-008"
        assert len(data["entries"]) == 1

        # 从字典恢复
        restored = DevLogStore.from_dict(data)
        assert restored.session_id == "s-test-008"
        assert len(restored.entries) == 1
        assert restored.entries[0].content == "决策1"


class TestDevLogTool:
    """测试 DevLogTool 工具"""

    def test_tool_initialization(self):
        """测试工具初始化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = DevLogTool(
                session_id="s-test-009",
                agent_name="TestAgent",
                project_root=temp_dir,
                persistence_dir="devlogs"
            )

            assert tool.name == "DevLog"
            assert tool.session_id == "s-test-009"
            assert tool.agent_name == "TestAgent"
            assert len(tool.store.entries) == 0

    def test_append_operation(self):
        """测试追加操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = DevLogTool(
                session_id="s-test-010",
                agent_name="TestAgent",
                project_root=temp_dir,
                persistence_dir="devlogs"
            )

            response = tool.run({
                "action": "append",
                "category": "decision",
                "content": "选择使用 Redis 作为缓存层",
                "metadata": {"tags": ["cache", "redis"]}
            })

            assert response.status == ToolStatus.SUCCESS
            assert "日志已记录" in response.text
            assert response.data["category"] == "decision"
            assert len(tool.store.entries) == 1

    def test_append_without_category(self):
        """测试追加时缺少类别"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = DevLogTool(
                session_id="s-test-011",
                agent_name="TestAgent",
                project_root=temp_dir
            )

            response = tool.run({
                "action": "append",
                "content": "测试内容"
            })

            assert response.status == ToolStatus.ERROR
            assert "必须指定 category" in response.text

    def test_append_invalid_category(self):
        """测试追加时使用无效类别"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = DevLogTool(
                session_id="s-test-012",
                agent_name="TestAgent",
                project_root=temp_dir
            )

            response = tool.run({
                "action": "append",
                "category": "invalid_category",
                "content": "测试内容"
            })

            assert response.status == ToolStatus.ERROR
            assert "无效的类别" in response.text

    def test_read_operation(self):
        """测试读取操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = DevLogTool(
                session_id="s-test-013",
                agent_name="TestAgent",
                project_root=temp_dir
            )

            # 添加一些日志
            tool.run({"action": "append", "category": "decision", "content": "决策1"})
            tool.run({"action": "append", "category": "issue", "content": "问题1"})

            # 读取所有日志
            response = tool.run({"action": "read"})

            assert response.status == ToolStatus.SUCCESS
            assert "2 条日志" in response.text
            assert len(response.data["entries"]) == 2

    def test_read_with_filter(self):
        """测试带过滤的读取"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = DevLogTool(
                session_id="s-test-014",
                agent_name="TestAgent",
                project_root=temp_dir
            )

            # 添加日志
            tool.run({"action": "append", "category": "decision", "content": "决策1"})
            tool.run({"action": "append", "category": "issue", "content": "问题1"})
            tool.run({"action": "append", "category": "decision", "content": "决策2"})

            # 只读取 decision 类别
            response = tool.run({
                "action": "read",
                "filter": {"category": "decision"}
            })

            assert response.status == ToolStatus.SUCCESS
            assert len(response.data["entries"]) == 2
            assert all(e["category"] == "decision" for e in response.data["entries"])

    def test_summary_operation(self):
        """测试摘要操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = DevLogTool(
                session_id="s-test-015",
                agent_name="TestAgent",
                project_root=temp_dir
            )

            # 添加日志
            tool.run({"action": "append", "category": "decision", "content": "决策1"})
            tool.run({"action": "append", "category": "issue", "content": "问题1"})

            # 生成摘要
            response = tool.run({"action": "summary"})

            assert response.status == ToolStatus.SUCCESS
            assert "2 条日志" in response.text
            assert response.data["total_entries"] == 2

    def test_clear_operation(self):
        """测试清空操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = DevLogTool(
                session_id="s-test-016",
                agent_name="TestAgent",
                project_root=temp_dir
            )

            # 添加日志
            tool.run({"action": "append", "category": "decision", "content": "决策1"})
            tool.run({"action": "append", "category": "issue", "content": "问题1"})

            # 清空
            response = tool.run({"action": "clear"})

            assert response.status == ToolStatus.SUCCESS
            assert "已清空 2 条日志" in response.text
            assert len(tool.store.entries) == 0

    def test_persistence(self):
        """测试持久化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            session_id = "s-test-017"

            # 创建工具并添加日志
            tool1 = DevLogTool(
                session_id=session_id,
                agent_name="TestAgent",
                project_root=temp_dir,
                persistence_dir="devlogs"
            )
            tool1.run({"action": "append", "category": "decision", "content": "决策1"})

            # 验证文件已创建
            devlog_file = Path(temp_dir) / "devlogs" / f"devlog-{session_id}.json"
            assert devlog_file.exists()

            # 创建新工具实例，应该加载已有日志
            tool2 = DevLogTool(
                session_id=session_id,
                agent_name="TestAgent",
                project_root=temp_dir,
                persistence_dir="devlogs"
            )

            assert len(tool2.store.entries) == 1
            assert tool2.store.entries[0].content == "决策1"


class TestAgentIntegration:
    """测试 Agent 集成"""

    def test_auto_registration(self):
        """测试自动注册"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = Config(
                devlog_enabled=True,
                devlog_persistence_dir=f"{temp_dir}/devlogs",
                trace_enabled=False,
                session_enabled=False,
                todowrite_enabled=False,
                subagent_enabled=False,
                skills_enabled=False
            )

            registry = ToolRegistry()
            llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")

            agent = ReActAgent(
                name="TestAgent",
                llm=llm,
                tool_registry=registry,
                config=config,
                max_steps=3
            )

            # 验证 DevLogTool 已注册
            tool = registry.get_tool("DevLog")
            assert tool is not None
            assert tool.name == "DevLog"
            assert isinstance(tool, DevLogTool)

    def test_disabled_devlog(self):
        """测试禁用 DevLog"""
        config = Config(
            devlog_enabled=False,
            trace_enabled=False,
            session_enabled=False,
            todowrite_enabled=False,
            subagent_enabled=False,
            skills_enabled=False
        )

        registry = ToolRegistry()
        llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")

        agent = ReActAgent(
            name="TestAgent",
            llm=llm,
            tool_registry=registry,
            config=config,
            max_steps=3
        )

        # 验证 DevLogTool 未注册
        tool = registry.get_tool("DevLog")
        assert tool is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

