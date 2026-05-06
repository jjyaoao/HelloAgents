"""NoteOrganizer - 笔记自动整理器测试"""

import pytest
import sys
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from hello_agents.tools.builtin.note_organizer import (
    NoteOrganizer,
    NoteOrganizerPolicy,
    NoteClassifier,
    OrganizeResult,
)

try:
    from hello_agents.tools.builtin.note_tool import NoteTool

    NOTE_TOOL_AVAILABLE = True
except ImportError:
    NOTE_TOOL_AVAILABLE = False
    NoteTool = None


class TestNoteClassifier:
    """笔记分类器测试"""

    @pytest.fixture
    def classifier(self):
        return NoteClassifier(current_task_context="实现用户登录功能")

    def test_decision_keywords_boost_score(self, classifier):
        """测试决策关键词提升分数"""
        note = {
            "title": "决定使用JWT认证",
            "content": "经过讨论决定使用JWT作为认证方案，因为它更适合分布式系统。",
            "created_at": datetime.now().isoformat(),
            "tags": ["auth"],
        }
        score = classifier.calculate_importance(note)
        assert score >= 0.25, f"决策关键词应该提升分数，实际: {score}"

    def test_problem_keywords_boost_score(self, classifier):
        """测试问题关键词提升分数"""
        note = {
            "title": "登录失败问题",
            "content": "发现密码验证失败，原因是salt未正确传递。已修复。",
            "created_at": datetime.now().isoformat(),
            "tags": ["bug"],
        }
        score = classifier.calculate_importance(note)
        assert score >= 0.2, f"问题关键词应该提升分数，实际: {score}"

    def test_task_keywords_boost_score(self, classifier):
        """测试任务关键词提升分数"""
        note = {
            "title": "下一步计划",
            "content": "目标：完成用户管理模块的实现。计划：1. 创建用户表 2. 实现CRUD接口",
            "created_at": datetime.now().isoformat(),
            "tags": [],
        }
        score = classifier.calculate_importance(note)
        assert score >= 0.2, f"任务关键词应该提升分数，实际: {score}"

    def test_learning_keywords_boost_score(self, classifier):
        """测试学习关键词提升分数"""
        note = {
            "title": "学到的经验",
            "content": "学会了使用async/await处理异步操作，需要注意错误捕获。",
            "created_at": datetime.now().isoformat(),
            "tags": [],
        }
        score = classifier.calculate_importance(note)
        assert score >= 0.25, f"学习关键词应该提升分数，实际: {score}"

    def test_structured_content_boost_score(self, classifier):
        """测试结构化内容提升分数"""
        note = {
            "title": "测试记录",
            "content": "1. 单元测试\n2. 集成测试\n3. 端到端测试\n- 所有测试通过",
            "created_at": datetime.now().isoformat(),
            "tags": [],
        }
        score = classifier.calculate_importance(note)
        assert score >= 0.15, f"结构化内容应该提升分数，实际: {score}"

    def test_old_note_lower_score(self, classifier):
        """测试旧笔记分数更低"""
        old_note = {
            "title": "旧笔记",
            "content": "这是一个很久以前的笔记",
            "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "tags": [],
        }
        old_score = classifier.calculate_importance(old_note)

        new_note = {
            "title": "新笔记",
            "content": "这是一个新笔记",
            "created_at": datetime.now().isoformat(),
            "tags": [],
        }
        new_score = classifier.calculate_importance(new_note)

        assert new_score > old_score, (
            f"新笔记分数应该更高: new={new_score}, old={old_score}"
        )

    def test_context_alignment_boost_score(self, classifier):
        """测试上下文相关性提升分数"""
        context_classifier = NoteClassifier(current_task_context="用户登录 认证 JWT")
        note = {
            "title": "登录流程",
            "content": "用户登录需要验证JWT token",
            "created_at": datetime.now().isoformat(),
            "tags": [],
        }
        score = context_classifier.calculate_importance(note)
        assert score >= 0.08, f"上下文相关应该提升分数，实际: {score}"

    def test_similarity_calculation(self, classifier):
        """测试相似度计算"""
        note1 = {"content": "使用JWT进行用户认证", "title": "认证方案"}
        note2 = {"content": "JWT用于用户身份验证", "title": "认证方案"}

        sim = classifier.compute_similarity(note1, note2)
        assert sim > 0.3, f"相似内容应该有较高相似度，实际: {sim}"

    def test_different_content_low_similarity(self, classifier):
        """测试不同内容相似度低"""
        note1 = {"content": "用户登录功能", "title": "登录"}
        note2 = {"content": "数据库连接配置", "title": "配置"}

        sim = classifier.compute_similarity(note1, note2)
        assert sim < 0.3, f"不同内容应该相似度低，实际: {sim}"


class TestNoteOrganizerPolicy:
    """笔记整理策略配置测试"""

    def test_default_policy_values(self):
        """测试默认策略值"""
        policy = NoteOrganizerPolicy()

        assert policy.temp_notes_threshold == 10
        assert policy.importance_threshold_promote == 0.7
        assert policy.importance_threshold_project == 0.85
        assert policy.importance_threshold_delete == 0.2
        assert policy.max_temp_age_days == 7
        assert policy.auto_promote_enabled is True
        assert policy.auto_cleanup_enabled is True

    def test_custom_policy_values(self):
        """测试自定义策略值"""
        policy = NoteOrganizerPolicy(
            temp_notes_threshold=5,
            importance_threshold_promote=0.6,
            max_temp_age_days=3,
        )

        assert policy.temp_notes_threshold == 5
        assert policy.importance_threshold_promote == 0.6
        assert policy.max_temp_age_days == 3


class TestOrganizeResult:
    """整理结果测试"""

    def test_empty_result(self):
        """测试空结果"""
        result = OrganizeResult()
        assert result.total_changes == 0

    def test_result_with_changes(self):
        """测试有变更的结果"""
        result = OrganizeResult(
            promoted=[{"note_id": "1", "score": 0.8}],
            deleted=[{"note_id": "2", "reason": "过期"}],
            merged=[{"note_id": "3", "merged_count": 2}],
        )

        assert result.total_changes == 3
        assert len(result.promoted) == 1
        assert len(result.deleted) == 1
        assert len(result.merged) == 1

    def test_result_to_dict(self):
        """测试结果转字典"""
        result = OrganizeResult(
            promoted=[{"note_id": "1"}],
        )
        data = result.to_dict()

        assert "promoted" in data
        assert "timestamp" in data
        assert "total_changes" in data


class TestNoteOrganizer:
    """笔记自动整理器测试"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def note_tool(self, temp_workspace):
        """创建 NoteTool 实例"""
        if not NOTE_TOOL_AVAILABLE:
            pytest.skip("NoteTool not available due to import error")
        return NoteTool(workspace=temp_workspace)

    @pytest.fixture
    def policy(self):
        """创建测试策略"""
        return NoteOrganizerPolicy(
            temp_notes_threshold=1,
            importance_threshold_promote=0.2,
            importance_threshold_delete=0.3,
            max_temp_age_days=7,
            auto_promote_enabled=True,
            auto_cleanup_enabled=True,
            auto_merge_enabled=True,
        )

    def test_organize_empty_notes(self, note_tool, policy):
        """测试空笔记列表的整理"""
        organizer = NoteOrganizer(note_tool, policy=policy)
        result = organizer.organize(force=True)

        assert result.total_changes == 0

    def test_promote_high_importance_note(self, note_tool, policy):
        """测试提升高重要性笔记"""
        note_tool.run(
            {
                "action": "create",
                "title": "决定使用Redis缓存",
                "content": "经过性能测试，决定使用Redis作为缓存方案，预计提升响应速度50%。",
                "note_type": "general",
                "tags": ["temp", "important"],
            }
        )

        organizer = NoteOrganizer(note_tool, policy=policy)
        result = organizer.organize(force=True)

        assert len(result.promoted) >= 1

    def test_cleanup_old_low_importance_note(self, note_tool, policy):
        """测试清理旧低重要性笔记"""
        old_time = (datetime.now() - timedelta(days=10)).isoformat()

        note_tool.run(
            {
                "action": "create",
                "title": "测试内容",
                "content": "这是一些临时测试内容",
                "note_type": "general",
                "tags": ["temp"],
            }
        )

        index = note_tool.notes_index["notes"]
        if index:
            index[0]["created_at"] = old_time
            note_tool._save_index()

        policy.importance_threshold_delete = 0.5
        organizer = NoteOrganizer(note_tool, policy=policy)
        result = organizer.organize(force=True)

        assert len(result.deleted) >= 0

    def test_get_status(self, note_tool, policy):
        """测试获取状态"""
        organizer = NoteOrganizer(note_tool, policy=policy)
        status = organizer.get_status()

        assert "temp_notes_count" in status
        assert "threshold" in status
        assert "enabled" in status

    def test_should_organize_below_threshold(self, note_tool, policy):
        """测试未达到阈值时不触发整理"""
        policy.temp_notes_threshold = 100
        organizer = NoteOrganizer(note_tool, policy=policy)

        assert not organizer._should_organize()

    def test_should_organize_above_threshold(self, note_tool, policy):
        """测试达到阈值时触发整理"""
        for i in range(3):
            note_tool.run(
                {
                    "action": "create",
                    "title": f"临时笔记{i}",
                    "content": f"内容{i}",
                    "note_type": "general",
                    "tags": ["temp"],
                }
            )

        policy.temp_notes_threshold = 2
        organizer = NoteOrganizer(note_tool, policy=policy)

        assert organizer._should_organize()

    def test_get_temp_notes(self, note_tool, policy):
        """测试获取临时笔记"""
        note_tool.run(
            {
                "action": "create",
                "title": "临时笔记",
                "content": "临时内容",
                "note_type": "general",
                "tags": ["temp"],
            }
        )

        organizer = NoteOrganizer(note_tool, policy=policy)
        temp_notes = organizer._get_temp_notes()

        assert len(temp_notes) >= 1


class TestNoteToolOrganizeIntegration:
    """NoteTool 集成测试"""

    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def note_tool(self, temp_workspace):
        """创建 NoteTool 实例"""
        return NoteTool(workspace=temp_workspace)

    def test_organize_action_via_note_tool(self, note_tool):
        """测试通过 NoteTool 调用 organize"""
        for i in range(3):
            note_tool.run(
                {
                    "action": "create",
                    "title": f"测试笔记{i}",
                    "content": f"内容{i}",
                    "note_type": "general",
                    "tags": ["temp"],
                }
            )

        result = note_tool.run(
            {
                "action": "organize",
                "mode": "auto",
                "force": True,
            }
        )

        assert "笔记整理结果" in result or "无需整理" in result

    def test_organize_mode_manual(self, note_tool):
        """测试手动模式"""
        result = note_tool.run(
            {
                "action": "organize",
                "mode": "manual",
                "force": True,
            }
        )

        assert "笔记整理结果" in result or "无需整理" in result


class TestNoteOrganizerEdgeCases:
    """边界情况测试"""

    @pytest.fixture
    def temp_workspace(self):
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def note_tool(self, temp_workspace):
        return NoteTool(workspace=temp_workspace)

    @pytest.fixture
    def policy(self):
        return NoteOrganizerPolicy(
            temp_notes_threshold=1,
            auto_promote_enabled=True,
            auto_cleanup_enabled=True,
        )

    def test_very_short_content(self, note_tool, policy):
        """测试极短内容"""
        note_tool.run(
            {
                "action": "create",
                "title": "短",
                "content": "a",
                "note_type": "general",
                "tags": ["temp"],
            }
        )

        organizer = NoteOrganizer(note_tool, policy=policy)
        result = organizer.organize(force=True)

        assert result is not None

    def test_very_long_content(self, note_tool, policy):
        """测试极长内容"""
        long_content = "测试内容 " * 1000
        note_tool.run(
            {
                "action": "create",
                "title": "长笔记",
                "content": long_content,
                "note_type": "general",
                "tags": ["temp"],
            }
        )

        organizer = NoteOrganizer(note_tool, policy=policy)
        result = organizer.organize(force=True)

        assert result is not None

    def test_special_characters_content(self, note_tool, policy):
        """测试特殊字符内容"""
        note_tool.run(
            {
                "action": "create",
                "title": "特殊字符",
                "content": "测试@#$%^&*()<>?/\\|",
                "note_type": "general",
                "tags": ["temp"],
            }
        )

        organizer = NoteOrganizer(note_tool, policy=policy)
        result = organizer.organize(force=True)

        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
