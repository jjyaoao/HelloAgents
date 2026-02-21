"""Skills 知识外化系统测试

测试内容：
1. SkillLoader 元数据加载
2. SkillLoader 完整技能加载
3. SkillTool 工具执行
4. Agent 集成测试
5. 缓存友好性验证
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from hello_agents.skills import SkillLoader, Skill
from hello_agents.tools.builtin.skill_tool import SkillTool
from hello_agents.tools.response import ToolResponse, ToolStatus
from hello_agents.tools.errors import ToolErrorCode
from dotenv import load_dotenv
load_dotenv()

class TestSkillLoader:
    """测试 SkillLoader"""

    @pytest.fixture
    def temp_skills_dir(self):
        """创建临时 skills 目录"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_skill(self, temp_skills_dir):
        """创建示例技能"""
        skill_dir = temp_skills_dir / "test-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: A test skill for unit testing
---

# Test Skill

This is a test skill body.

## Usage

Use this skill for testing.

$ARGUMENTS
""", encoding='utf-8')

        return skill_dir

    def test_scan_skills(self, temp_skills_dir, sample_skill):
        """测试扫描技能目录"""
        loader = SkillLoader(skills_dir=temp_skills_dir)

        assert "test-skill" in loader.list_skills()
        assert len(loader.metadata_cache) == 1

    def test_get_descriptions(self, temp_skills_dir, sample_skill):
        """测试获取技能描述"""
        loader = SkillLoader(skills_dir=temp_skills_dir)

        descriptions = loader.get_descriptions()
        assert "test-skill" in descriptions
        assert "A test skill for unit testing" in descriptions

    def test_get_skill(self, temp_skills_dir, sample_skill):
        """测试加载完整技能"""
        loader = SkillLoader(skills_dir=temp_skills_dir)

        skill = loader.get_skill("test-skill")
        assert skill is not None
        assert skill.name == "test-skill"
        assert skill.description == "A test skill for unit testing"
        assert "This is a test skill body" in skill.body
        assert "$ARGUMENTS" in skill.body

    def test_get_skill_not_found(self, temp_skills_dir):
        """测试加载不存在的技能"""
        loader = SkillLoader(skills_dir=temp_skills_dir)

        skill = loader.get_skill("non-existent")
        assert skill is None

    def test_skill_caching(self, temp_skills_dir, sample_skill):
        """测试技能缓存"""
        loader = SkillLoader(skills_dir=temp_skills_dir)

        # 第一次加载
        skill1 = loader.get_skill("test-skill")
        # 第二次加载（应该从缓存）
        skill2 = loader.get_skill("test-skill")

        assert skill1 is skill2  # 同一个对象

    def test_reload(self, temp_skills_dir, sample_skill):
        """测试热重载"""
        loader = SkillLoader(skills_dir=temp_skills_dir)

        # 初始加载
        assert "test-skill" in loader.list_skills()

        # 添加新技能
        new_skill_dir = temp_skills_dir / "new-skill"
        new_skill_dir.mkdir()
        (new_skill_dir / "SKILL.md").write_text("""---
name: new-skill
description: A new skill
---

# New Skill
""", encoding='utf-8')

        # 重载
        loader.reload()

        assert "new-skill" in loader.list_skills()
        assert len(loader.list_skills()) == 2


class TestSkillTool:
    """测试 SkillTool"""

    @pytest.fixture
    def temp_skills_dir(self):
        """创建临时 skills 目录"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_skill_with_resources(self, temp_skills_dir):
        """创建带资源的示例技能"""
        skill_dir = temp_skills_dir / "resource-skill"
        skill_dir.mkdir()

        # 创建 SKILL.md
        (skill_dir / "SKILL.md").write_text("""---
name: resource-skill
description: A skill with resources
---

# Resource Skill

Use the scripts in the scripts/ folder.

$ARGUMENTS
""", encoding='utf-8')

        # 创建资源文件夹
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "script1.py").write_text("# Script 1")
        (scripts_dir / "script2.py").write_text("# Script 2")

        return skill_dir

    def test_skill_tool_success(self, temp_skills_dir, sample_skill_with_resources):
        """测试成功加载技能"""
        loader = SkillLoader(skills_dir=temp_skills_dir)
        tool = SkillTool(skill_loader=loader)

        response = tool.run({"skill": "resource-skill"})

        assert isinstance(response, ToolResponse)
        assert response.status == ToolStatus.SUCCESS
        assert "resource-skill" in response.text
        assert "Use the scripts" in response.text
        assert response.data["loaded"] is True
        assert response.data["has_resources"] is True

    def test_skill_tool_with_args(self, temp_skills_dir, sample_skill_with_resources):
        """测试带参数的技能加载"""
        loader = SkillLoader(skills_dir=temp_skills_dir)
        tool = SkillTool(skill_loader=loader)

        response = tool.run({"skill": "resource-skill", "args": "custom arguments"})

        assert response.status == ToolStatus.SUCCESS
        assert "custom arguments" in response.text  # $ARGUMENTS 被替换

    def test_skill_tool_not_found(self, temp_skills_dir):
        """测试加载不存在的技能"""
        loader = SkillLoader(skills_dir=temp_skills_dir)
        tool = SkillTool(skill_loader=loader)

        response = tool.run({"skill": "non-existent"})

        assert response.status == ToolStatus.ERROR
        assert response.error_info["code"] == ToolErrorCode.NOT_FOUND
        assert "不存在" in response.error_info["message"]

    def test_skill_tool_invalid_param(self, temp_skills_dir):
        """测试无效参数"""
        loader = SkillLoader(skills_dir=temp_skills_dir)
        tool = SkillTool(skill_loader=loader)

        response = tool.run({})  # 缺少 skill 参数

        assert response.status == ToolStatus.ERROR
        assert response.error_info["code"] == ToolErrorCode.INVALID_PARAM


class TestAgentIntegration:
    """测试 Agent 集成"""

    def test_agent_skill_loader_initialization(self):
        """测试 Agent 初始化时创建 SkillLoader"""
        from hello_agents.core.agent import Agent
        from hello_agents.core.llm import HelloAgentsLLM
        from hello_agents.core.config import Config
        from hello_agents.tools.registry import ToolRegistry

        # 创建临时 skills 目录
        temp_dir = tempfile.mkdtemp()
        try:
            config = Config(skills_enabled=True, skills_dir=temp_dir)
            llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")
            registry = ToolRegistry()

            # 创建一个简单的 Agent 子类用于测试
            class TestAgent(Agent):
                def run(self, input_text: str, **kwargs) -> str:
                    return "test"

            agent = TestAgent(
                name="test-agent",
                llm=llm,
                config=config,
                tool_registry=registry
            )

            # 验证 SkillLoader 已创建
            assert agent.skill_loader is not None
            assert isinstance(agent.skill_loader, SkillLoader)

            # 验证 SkillTool 已自动注册
            assert "Skill" in registry._tools

        finally:
            shutil.rmtree(temp_dir)

    def test_agent_skill_disabled(self):
        """测试禁用 Skills 功能"""
        from hello_agents.core.agent import Agent
        from hello_agents.core.llm import HelloAgentsLLM
        from hello_agents.core.config import Config

        config = Config(skills_enabled=False)
        llm = HelloAgentsLLM(provider="openai", model="gpt-3.5-turbo")

        class TestAgent(Agent):
            def run(self, input_text: str, **kwargs) -> str:
                return "test"

        agent = TestAgent(name="test-agent", llm=llm, config=config)

        # 验证 SkillLoader 未创建
        assert agent.skill_loader is None


class TestCacheFriendly:
    """测试缓存友好性"""

    def test_skill_content_as_tool_result(self, tmp_path):
        """验证技能内容作为 tool_result 返回（而非修改 system_prompt）"""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("""---
name: test
description: Test skill
---

# Test Content
""", encoding='utf-8')

        loader = SkillLoader(skills_dir=tmp_path)
        tool = SkillTool(skill_loader=loader)

        response = tool.run({"skill": "test"})

        # 验证返回的是 ToolResponse（会被 Agent 作为 user message 处理）
        assert isinstance(response, ToolResponse)
        assert response.status == ToolStatus.SUCCESS
        # 验证内容包含 skill 标签（缓存友好的标记）
        assert "<skill-loaded" in response.text
        assert "</skill-loaded>" in response.text

