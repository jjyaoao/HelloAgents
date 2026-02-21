"""Skills 知识外化使用示例

演示如何使用 Skills 系统实现知识外化：
- 渐进式披露（启动时仅加载元数据）
- 按需加载完整技能
- 零配置自动激活
- 自定义技能创建
"""

from hello_agents.skills import SkillLoader, Skill
from hello_agents import ReActAgent, SimpleAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config
from hello_agents.tools.registry import ToolRegistry
from hello_agents.tools.builtin.skill_tool import SkillTool
from pathlib import Path
import tempfile
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


def demo_skill_loader():
    """演示技能加载器"""
    print("=" * 60)
    print("示例 1: 技能加载器基础")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        skills_dir = Path(temp_dir) / "skills"
        skills_dir.mkdir()
        
        # 创建示例技能文件
        pdf_skill = skills_dir / "pdf"
        pdf_skill.mkdir()
        (pdf_skill / "SKILL.md").write_text("""---
name: pdf
description: Process PDF files and extract text content
---

# PDF Processing Skill

This skill helps you process PDF files.

## Usage
Use `pdftotext` command to extract text from PDF files.

## Example
```bash
pdftotext input.pdf output.txt
```
""", encoding='utf-8')
        
        # 创建技能加载器
        loader = SkillLoader(skills_dir=skills_dir)
        
        # 获取技能描述（仅元数据）
        print("\n技能描述（元数据）:")
        descriptions = loader.get_descriptions()
        for name, desc in descriptions.items():
            print(f"  - {name}: {desc}")
        
        # 按需加载完整技能
        print("\n加载完整技能:")
        skill = loader.get_skill("pdf")
        if skill:
            print(f"  名称: {skill.name}")
            print(f"  描述: {skill.description}")
            print(f"  内容长度: {len(skill.body)} 字符")
            print(f"  内容预览: {skill.body[:100]}...")
        
        print("\n✅ 技能加载器测试完成")


def demo_skill_tool():
    """演示技能工具"""
    print("\n" + "=" * 60)
    print("示例 2: 技能工具使用")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        skills_dir = Path(temp_dir) / "skills"
        skills_dir.mkdir()
        
        # 创建代码审查技能
        review_skill = skills_dir / "code-review"
        review_skill.mkdir()
        (review_skill / "SKILL.md").write_text("""---
name: code-review
description: Perform comprehensive code reviews
---

# Code Review Skill

## Checklist
1. Security vulnerabilities
2. Performance issues
3. Code style consistency
4. Error handling
5. Test coverage

## Best Practices
- Use static analysis tools
- Check for common patterns
- Review documentation
""", encoding='utf-8')
        
        # 创建技能加载器和工具
        loader = SkillLoader(skills_dir=skills_dir)
        skill_tool = SkillTool(skill_loader=loader)
        
        # 调用技能工具
        print("\n调用技能工具:")
        response = skill_tool.run({"skill": "code-review"})
        
        print(f"  状态: {response.status.value}")
        print(f"  内容长度: {len(response.text)} 字符")
        print(f"  内容预览:\n{response.text[:200]}...")
        
        # 测试不存在的技能
        print("\n调用不存在的技能:")
        response = skill_tool.run({"skill": "nonexistent"})
        print(f"  状态: {response.status.value}")
        print(f"  错误码: {response.error_info['code']}")
        
        print("\n✅ 技能工具测试完成")


def demo_zero_config_activation():
    """演示零配置激活"""
    print("\n" + "=" * 60)
    print("示例 3: 零配置自动激活")
    print("=" * 60)
    
    # 检查 skills 目录是否存在
    skills_dir = Path("skills")
    
    if skills_dir.exists():
        print(f"\n检测到 skills 目录: {skills_dir.absolute()}")
        
        # 创建 Agent（自动激活 Skills）
        config = Config(
            skills_enabled=True,
            skills_auto_register=True,
            trace_enabled=False
        )
        
        llm = HelloAgentsLLM()
        registry = ToolRegistry()
        agent = ReActAgent("assistant", llm, tool_registry=registry, config=config)
        
        # 检查 Skill 工具是否已注册
        tools = registry.list_tools()
        print(f"\n已注册工具: {tools}")
        
        if "Skill" in tools:
            print("✅ Skill 工具已自动注册")
        else:
            print("⚠️ Skill 工具未注册（可能 skills 目录为空）")
    else:
        print(f"\n⚠️ skills 目录不存在: {skills_dir.absolute()}")
        print("   创建 skills 目录并添加 SKILL.md 文件即可自动激活")
    
    print("\n✅ 零配置激活测试完成")


def demo_skill_with_arguments():
    """演示带参数的技能"""
    print("\n" + "=" * 60)
    print("示例 4: 带参数的技能")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        skills_dir = Path(temp_dir) / "skills"
        skills_dir.mkdir()
        
        # 创建带参数占位符的技能
        template_skill = skills_dir / "template"
        template_skill.mkdir()
        (template_skill / "SKILL.md").write_text("""---
name: template
description: A template skill with arguments
---

# Template Skill

This skill accepts custom arguments.

## Arguments
$ARGUMENTS

## Usage
Process the arguments above and generate output.
""", encoding='utf-8')
        
        # 创建技能工具
        loader = SkillLoader(skills_dir=skills_dir)
        skill_tool = SkillTool(skill_loader=loader)
        
        # 调用带参数的技能
        print("\n调用带参数的技能:")
        response = skill_tool.run({
            "skill": "template",
            "arguments": "Target: Python code\nFocus: Performance optimization"
        })
        
        print(f"  状态: {response.status.value}")
        print(f"  内容预览:\n{response.text[:300]}...")
        
        # 验证参数替换
        assert "Target: Python code" in response.text
        assert "Performance optimization" in response.text
        
        print("\n✅ 带参数技能测试完成")


def demo_skill_resources():
    """演示技能资源文件"""
    print("\n" + "=" * 60)
    print("示例 5: 技能资源文件")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        skills_dir = Path(temp_dir) / "skills"
        skills_dir.mkdir()
        
        # 创建带资源的技能
        mcp_skill = skills_dir / "mcp-builder"
        mcp_skill.mkdir()
        
        # 创建 SKILL.md
        (mcp_skill / "SKILL.md").write_text("""---
name: mcp-builder
description: Build MCP servers
---

# MCP Server Builder

Build Model Context Protocol servers.

## Resources
Check the scripts/ and examples/ folders for templates.
""", encoding='utf-8')
        
        # 创建资源文件夹
        (mcp_skill / "scripts").mkdir()
        (mcp_skill / "examples").mkdir()
        (mcp_skill / "references").mkdir()
        
        # 创建资源文件
        (mcp_skill / "scripts" / "template.py").write_text("# MCP template", encoding='utf-8')
        (mcp_skill / "examples" / "weather.py").write_text("# Weather example", encoding='utf-8')
        (mcp_skill / "references" / "spec.md").write_text("# MCP spec", encoding='utf-8')
        
        # 加载技能
        loader = SkillLoader(skills_dir=skills_dir)
        skill = loader.get_skill("mcp-builder")
        
        print("\n技能资源:")
        print(f"  脚本: {skill.scripts}")
        print(f"  示例: {skill.examples}")
        print(f"  参考: {skill.references}")
        
        # 验证资源检测
        assert len(skill.scripts) == 1
        assert len(skill.examples) == 1
        assert len(skill.references) == 1
        
        print("\n✅ 技能资源测试完成")


if __name__ == "__main__":
    demo_skill_loader()
    demo_skill_tool()
    demo_zero_config_activation()
    demo_skill_with_arguments()
    demo_skill_resources()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成！")
    print("=" * 60)

