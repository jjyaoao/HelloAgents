"""Skill Tool - 技能工具

允许 Agent 按需加载领域知识。

特性：
- 渐进式披露：仅在需要时加载完整技能
- 缓存友好：作为 tool_result 注入，不修改 system_prompt
- 资源提示：自动列出可用的脚本、文档、示例等
- 参数替换：支持 $ARGUMENTS 占位符

使用示例：
    >>> from hello_agents.skills import SkillLoader
    >>> from hello_agents.tools.builtin.skill_tool import SkillTool
    >>> loader = SkillLoader(skills_dir=Path("skills"))
    >>> tool = SkillTool(skill_loader=loader)
    >>> # Agent 调用
    >>> response = tool.run({"skill": "pdf"})
"""

from typing import Dict, Any, List
from ..base import Tool, ToolParameter
from ...skills.loader import SkillLoader
from ..response import ToolResponse
from ..errors import ToolErrorCode


class SkillTool(Tool):
    """
    技能工具

    允许模型按需加载领域知识。
    """

    def __init__(self, skill_loader: SkillLoader):
        """初始化技能工具

        Args:
            skill_loader: 技能加载器实例
        """
        # 生成动态描述
        descriptions = skill_loader.get_descriptions()

        super().__init__(
            name="Skill",
            description=f"""加载技能获取专业知识。

可用技能：
{descriptions}

何时使用：
- 任务明确匹配某个技能描述时，立即使用
- 开始领域特定工作之前
- 需要模型不具备的专业知识时

注意：加载技能后，请严格遵循技能说明来完成用户任务。""",
            expandable=False
        )
        self.skill_loader = skill_loader

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="skill",
                type="string",
                description="要加载的技能名称",
                required=True
            ),
            ToolParameter(
                name="args",
                type="string",
                description="可选参数，将替换 SKILL.md 中的 $ARGUMENTS 占位符",
                required=False,
                default=""
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行技能加载

        Args:
            parameters: 包含 skill 和可选 args 的参数字典

        Returns:
            ToolResponse: 包含完整技能内容的响应
        """
        skill_name = parameters.get("skill", "")
        args = parameters.get("args", "")

        if not skill_name:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="必须指定技能名称",
                context={"params_input": parameters}
            )

        try:
            # 按需加载技能
            skill = self.skill_loader.get_skill(skill_name)

            if not skill:
                available = ", ".join(self.skill_loader.list_skills())
                return ToolResponse.error(
                    code=ToolErrorCode.NOT_FOUND,
                    message=f"技能 '{skill_name}' 不存在。可用技能：{available}",
                    context={"params_input": parameters, "available_skills": self.skill_loader.list_skills()}
                )

            # 替换 $ARGUMENTS 占位符
            content = skill.body.replace("$ARGUMENTS", args)

            # 列出可用资源
            resources_hint = self._get_resources_hint(skill)

            # 构造完整技能内容（缓存友好的注入方式）
            full_content = f"""<skill-loaded name="{skill_name}">
{content}
{resources_hint}
</skill-loaded>

✅ 技能已加载：{skill.name}
📝 描述：{skill.description}

请严格遵循上述技能说明来完成用户任务。"""

            return ToolResponse.success(
                text=full_content,
                data={
                    "name": skill.name,
                    "description": skill.description,
                    "loaded": True,
                    "token_estimate": len(full_content),
                    "has_resources": bool(resources_hint)
                }
            )

        except Exception as e:
            return ToolResponse.error(
                code=ToolErrorCode.INTERNAL_ERROR,
                message=f"加载技能失败：{str(e)}",
                context={"params_input": parameters, "error": str(e)}
            )

    def _get_resources_hint(self, skill) -> str:
        """生成资源提示文本

        Args:
            skill: Skill 对象

        Returns:
            格式化的资源提示文本
        """
        resources = []

        for folder, label in [
            ("scripts", "脚本"),
            ("references", "参考文档"),
            ("assets", "资源"),
            ("examples", "示例")
        ]:
            folder_path = skill.dir / folder
            if folder_path.exists():
                files = list(folder_path.glob("*"))
                if files:
                    file_list = ", ".join(f.name for f in files[:5])  # 最多显示 5 个
                    if len(files) > 5:
                        file_list += f" 等 {len(files)} 个文件"
                    resources.append(f"  - {label}：{file_list}")

        if not resources:
            return ""

        return "\n\n**可用资源**：\n" + "\n".join(resources)

