"""文件操作工具测试 - 包含乐观锁机制验证"""

import pytest
import tempfile
import shutil
from pathlib import Path
import time
import os

from hello_agents.tools.builtin.file_tools import ReadTool, WriteTool, EditTool, MultiEditTool
from hello_agents.tools.registry import ToolRegistry
from hello_agents.tools.response import ToolStatus
from hello_agents.tools.errors import ToolErrorCode


@pytest.fixture
def temp_workspace():
    """创建临时工作空间"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def registry():
    """创建工具注册表"""
    return ToolRegistry()


class TestReadTool:
    """ReadTool 测试"""
    
    def test_read_file_success(self, temp_workspace, registry):
        """测试成功读取文件"""
        # 创建测试文件
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3\n", encoding='utf-8')
        
        # 创建工具
        read_tool = ReadTool(project_root=str(temp_workspace), registry=registry)
        
        # 执行读取
        response = read_tool.run({"path": "test.txt"})
        
        # 验证响应
        assert response.status == ToolStatus.SUCCESS
        assert response.data["content"] == "Line 1\nLine 2\nLine 3\n"
        assert response.data["lines"] == 3
        assert "file_mtime_ms" in response.data
        assert "file_size_bytes" in response.data
    
    def test_read_file_with_offset_limit(self, temp_workspace, registry):
        """测试带 offset 和 limit 的读取"""
        # 创建测试文件
        test_file = temp_workspace / "test.txt"
        test_file.write_text("\n".join([f"Line {i}" for i in range(1, 11)]), encoding='utf-8')
        
        read_tool = ReadTool(project_root=str(temp_workspace), registry=registry)
        
        # 读取第 3-5 行
        response = read_tool.run({"path": "test.txt", "offset": 2, "limit": 3})
        
        assert response.status == ToolStatus.SUCCESS
        assert response.data["lines"] == 3
        assert "Line 3" in response.data["content"]
        assert "Line 6" not in response.data["content"]
    
    def test_read_file_not_found(self, temp_workspace, registry):
        """测试读取不存在的文件"""
        read_tool = ReadTool(project_root=str(temp_workspace), registry=registry)
        
        response = read_tool.run({"path": "nonexistent.txt"})
        
        assert response.status == ToolStatus.ERROR
        assert response.error_info["code"] == ToolErrorCode.NOT_FOUND
    
    def test_read_metadata_caching(self, temp_workspace, registry):
        """测试元数据缓存"""
        # 创建测试文件
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Test content", encoding='utf-8')
        
        read_tool = ReadTool(project_root=str(temp_workspace), registry=registry)
        
        # 执行读取
        response = read_tool.run({"path": "test.txt"})
        
        # 验证元数据已缓存
        cached_metadata = registry.get_read_metadata("test.txt")
        assert cached_metadata is not None
        assert cached_metadata["file_mtime_ms"] == response.data["file_mtime_ms"]
        assert cached_metadata["file_size_bytes"] == response.data["file_size_bytes"]


class TestWriteTool:
    """WriteTool 测试"""
    
    def test_write_new_file(self, temp_workspace, registry):
        """测试创建新文件"""
        write_tool = WriteTool(project_root=str(temp_workspace), registry=registry)
        
        response = write_tool.run({
            "path": "new_file.txt",
            "content": "Hello, World!"
        })
        
        assert response.status == ToolStatus.SUCCESS
        assert response.data["written"] is True
        assert (temp_workspace / "new_file.txt").exists()
        assert (temp_workspace / "new_file.txt").read_text(encoding='utf-8') == "Hello, World!"
    
    def test_write_overwrite_file(self, temp_workspace, registry):
        """测试覆盖已存在的文件"""
        # 创建原文件
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Original content", encoding='utf-8')
        
        write_tool = WriteTool(project_root=str(temp_workspace), registry=registry)
        
        response = write_tool.run({
            "path": "test.txt",
            "content": "New content"
        })
        
        assert response.status == ToolStatus.SUCCESS
        assert test_file.read_text(encoding='utf-8') == "New content"
        
        # 验证备份文件存在
        backup_dir = temp_workspace / ".backups"
        assert backup_dir.exists()
        assert len(list(backup_dir.glob("test.txt.*.bak"))) > 0
    
    def test_write_conflict_detection(self, temp_workspace, registry):
        """测试冲突检测"""
        # 创建测试文件
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Original", encoding='utf-8')

        # 获取初始 mtime
        initial_mtime = int(os.path.getmtime(test_file) * 1000)

        # 等待足够时间确保 mtime 变化（跨平台兼容）
        time.sleep(0.1)
        test_file.write_text("Modified by external", encoding='utf-8')
        
        write_tool = WriteTool(project_root=str(temp_workspace), registry=registry)
        
        # 尝试写入，使用旧的 mtime
        response = write_tool.run({
            "path": "test.txt",
            "content": "My changes",
            "file_mtime_ms": initial_mtime
        })
        
        # 应该检测到冲突
        assert response.status == ToolStatus.ERROR
        assert response.error_info["code"] == ToolErrorCode.CONFLICT
        assert "被修改" in response.error_info["message"]
    
    def test_write_atomic_operation(self, temp_workspace, registry):
        """测试原子写入"""
        write_tool = WriteTool(project_root=str(temp_workspace), registry=registry)
        
        # 写入文件
        response = write_tool.run({
            "path": "atomic.txt",
            "content": "Atomic content"
        })
        
        assert response.status == ToolStatus.SUCCESS
        
        # 验证没有临时文件残留
        assert not (temp_workspace / "atomic.txt.tmp").exists()


class TestEditTool:
    """EditTool 测试"""
    
    def test_edit_success(self, temp_workspace, registry):
        """测试成功编辑"""
        # 创建测试文件
        test_file = temp_workspace / "config.py"
        test_file.write_text('API_KEY = "old_key"\nDEBUG = True\n', encoding='utf-8')
        
        edit_tool = EditTool(project_root=str(temp_workspace), registry=registry)

        # 执行编辑
        response = edit_tool.run({
            "path": "config.py",
            "old_string": 'API_KEY = "old_key"',
            "new_string": 'API_KEY = "new_key"'
        })

        assert response.status == ToolStatus.SUCCESS
        assert response.data["modified"] is True
        assert 'API_KEY = "new_key"' in test_file.read_text(encoding='utf-8')

        # 验证备份文件存在
        backup_dir = temp_workspace / ".backups"
        assert backup_dir.exists()

    def test_edit_conflict_detection(self, temp_workspace, registry):
        """测试编辑冲突检测"""
        # 创建测试文件
        test_file = temp_workspace / "config.py"
        test_file.write_text('API_KEY = "old_key"\n', encoding='utf-8')

        # 获取初始 mtime
        initial_mtime = int(os.path.getmtime(test_file) * 1000)

        # 模拟外部修改（跨平台兼容）
        time.sleep(0.1)
        test_file.write_text('API_KEY = "external_change"\n', encoding='utf-8')

        edit_tool = EditTool(project_root=str(temp_workspace), registry=registry)

        # 尝试编辑，使用旧的 mtime
        response = edit_tool.run({
            "path": "config.py",
            "old_string": 'API_KEY = "old_key"',
            "new_string": 'API_KEY = "my_key"',
            "file_mtime_ms": initial_mtime
        })

        # 应该检测到冲突
        assert response.status == ToolStatus.ERROR
        assert response.error_info["code"] == ToolErrorCode.CONFLICT

    def test_edit_old_string_not_unique(self, temp_workspace, registry):
        """测试 old_string 不唯一的情况"""
        # 创建测试文件
        test_file = temp_workspace / "test.txt"
        test_file.write_text("foo\nfoo\nbar\n", encoding='utf-8')

        edit_tool = EditTool(project_root=str(temp_workspace), registry=registry)

        response = edit_tool.run({
            "path": "test.txt",
            "old_string": "foo",
            "new_string": "baz"
        })

        # 应该返回错误
        assert response.status == ToolStatus.ERROR
        assert response.error_info["code"] == ToolErrorCode.INVALID_PARAM
        assert "2 处匹配" in response.error_info["message"]

    def test_edit_backup_creation(self, temp_workspace, registry):
        """测试备份创建"""
        # 创建测试文件
        test_file = temp_workspace / "important.txt"
        original_content = "Important data"
        test_file.write_text(original_content, encoding='utf-8')

        edit_tool = EditTool(project_root=str(temp_workspace), registry=registry)

        response = edit_tool.run({
            "path": "important.txt",
            "old_string": "Important data",
            "new_string": "Modified data"
        })

        assert response.status == ToolStatus.SUCCESS

        # 验证备份文件包含原始内容
        backup_dir = temp_workspace / ".backups"
        backup_files = list(backup_dir.glob("important.txt.*.bak"))
        assert len(backup_files) > 0
        assert backup_files[0].read_text(encoding='utf-8') == original_content


class TestMultiEditTool:
    """MultiEditTool 测试"""

    def test_multiedit_success(self, temp_workspace, registry):
        """测试批量编辑成功"""
        # 创建测试文件
        test_file = temp_workspace / "config.py"
        test_file.write_text(
            'API_KEY = "old_key"\n'
            'DEBUG = False\n'
            'PORT = 8000\n',
            encoding='utf-8'
        )

        multiedit_tool = MultiEditTool(project_root=str(temp_workspace), registry=registry)

        response = multiedit_tool.run({
            "path": "config.py",
            "edits": [
                {"old_string": 'API_KEY = "old_key"', "new_string": 'API_KEY = "new_key"'},
                {"old_string": "DEBUG = False", "new_string": "DEBUG = True"},
                {"old_string": "PORT = 8000", "new_string": "PORT = 9000"}
            ]
        })

        assert response.status == ToolStatus.SUCCESS
        assert response.data["num_edits"] == 3

        content = test_file.read_text(encoding='utf-8')
        assert 'API_KEY = "new_key"' in content
        assert "DEBUG = True" in content
        assert "PORT = 9000" in content

    def test_multiedit_conflict_detection(self, temp_workspace, registry):
        """测试批量编辑冲突检测"""
        # 创建测试文件
        test_file = temp_workspace / "config.py"
        test_file.write_text('KEY = "value"\n', encoding='utf-8')

        # 获取初始 mtime
        initial_mtime = int(os.path.getmtime(test_file) * 1000)

        # 模拟外部修改（跨平台兼容）
        time.sleep(0.1)
        test_file.write_text('KEY = "external"\n', encoding='utf-8')

        multiedit_tool = MultiEditTool(project_root=str(temp_workspace), registry=registry)

        response = multiedit_tool.run({
            "path": "config.py",
            "edits": [
                {"old_string": 'KEY = "value"', "new_string": 'KEY = "new"'}
            ],
            "file_mtime_ms": initial_mtime
        })

        # 应该检测到冲突
        assert response.status == ToolStatus.ERROR
        assert response.error_info["code"] == ToolErrorCode.CONFLICT
        assert "所有替换已取消" in response.error_info["message"]

    def test_multiedit_atomicity(self, temp_workspace, registry):
        """测试批量编辑的原子性"""
        # 创建测试文件
        test_file = temp_workspace / "test.txt"
        original_content = "line1\nline2\nline3\n"
        test_file.write_text(original_content, encoding='utf-8')

        multiedit_tool = MultiEditTool(project_root=str(temp_workspace), registry=registry)

        # 尝试批量编辑，其中一个替换不唯一
        response = multiedit_tool.run({
            "path": "test.txt",
            "edits": [
                {"old_string": "line1", "new_string": "LINE1"},
                {"old_string": "line", "new_string": "LINE"}  # 这个会匹配多次
            ]
        })

        # 应该失败
        assert response.status == ToolStatus.ERROR

        # 验证文件内容未被修改（原子性）
        assert test_file.read_text(encoding='utf-8') == original_content


class TestOptimisticLocking:
    """乐观锁机制集成测试"""

    def test_external_modification_detection(self, temp_workspace, registry):
        """测试外部修改检测"""
        # 创建测试文件
        test_file = temp_workspace / "data.txt"
        test_file.write_text("Original data", encoding='utf-8')

        # 1. Read 文件（缓存元数据）
        read_tool = ReadTool(project_root=str(temp_workspace), registry=registry)
        read_response = read_tool.run({"path": "data.txt"})
        assert read_response.status == ToolStatus.SUCCESS

        # 2. 外部修改文件（跨平台兼容）
        time.sleep(0.1)
        test_file.write_text("External modification", encoding='utf-8')

        # 3. 尝试 Edit（应该检测到冲突）
        edit_tool = EditTool(project_root=str(temp_workspace), registry=registry)

        # 从缓存获取元数据
        cached_metadata = registry.get_read_metadata("data.txt")

        edit_response = edit_tool.run({
            "path": "data.txt",
            "old_string": "Original data",
            "new_string": "My changes",
            "file_mtime_ms": cached_metadata["file_mtime_ms"]
        })

        # 应该检测到冲突
        assert edit_response.status == ToolStatus.ERROR
        assert edit_response.error_info["code"] == ToolErrorCode.CONFLICT

    def test_multi_agent_collaboration(self, temp_workspace):
        """测试多 Agent 协作场景"""
        # 创建两个独立的 registry（模拟两个 Agent）
        registry_a = ToolRegistry()
        registry_b = ToolRegistry()

        # 创建测试文件
        test_file = temp_workspace / "shared.txt"
        test_file.write_text("Shared content", encoding='utf-8')

        # Agent A 读取文件
        read_tool_a = ReadTool(project_root=str(temp_workspace), registry=registry_a)
        read_a = read_tool_a.run({"path": "shared.txt"})
        assert read_a.status == ToolStatus.SUCCESS

        # Agent B 读取文件
        read_tool_b = ReadTool(project_root=str(temp_workspace), registry=registry_b)
        read_b = read_tool_b.run({"path": "shared.txt"})
        assert read_b.status == ToolStatus.SUCCESS

        # Agent B 先修改
        edit_tool_b = EditTool(project_root=str(temp_workspace), registry=registry_b)
        cached_b = registry_b.get_read_metadata("shared.txt")
        edit_b = edit_tool_b.run({
            "path": "shared.txt",
            "old_string": "Shared content",
            "new_string": "Modified by B",
            "file_mtime_ms": cached_b["file_mtime_ms"]
        })
        assert edit_b.status == ToolStatus.SUCCESS

        # Agent A 尝试修改（应该失败）
        edit_tool_a = EditTool(project_root=str(temp_workspace), registry=registry_a)
        cached_a = registry_a.get_read_metadata("shared.txt")
        edit_a = edit_tool_a.run({
            "path": "shared.txt",
            "old_string": "Shared content",
            "new_string": "Modified by A",
            "file_mtime_ms": cached_a["file_mtime_ms"]
        })

        # Agent A 应该检测到冲突
        assert edit_a.status == ToolStatus.ERROR
        assert edit_a.error_info["code"] == ToolErrorCode.CONFLICT

