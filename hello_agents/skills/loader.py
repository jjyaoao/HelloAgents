"""Skills 加载器

实现渐进式披露机制：
- Layer 1: Metadata（启动时加载，~100 tokens/skill）
- Layer 2: SKILL.md body（按需加载，~2000+ tokens）
- Layer 3: Resources（可选，按需）
"""

from pathlib import Path
from typing import Dict, List, Optional
import re
import yaml
from dataclasses import dataclass


@dataclass
class Skill:
    """技能数据类"""

    name: str
    description: str
    body: str
    path: Path
    dir: Path

    @property
    def scripts(self) -> List[Path]:
        """获取 scripts/ 目录下的所有文件"""
        scripts_dir = self.dir / "scripts"
        if not scripts_dir.exists():
            return []
        return [f for f in scripts_dir.rglob("*") if f.is_file()]

    @property
    def examples(self) -> List[Path]:
        """获取 examples/ 目录下的所有文件"""
        examples_dir = self.dir / "examples"
        if not examples_dir.exists():
            return []
        return [f for f in examples_dir.rglob("*") if f.is_file()]

    @property
    def references(self) -> List[Path]:
        """获取 references/ 目录下的所有文件"""
        references_dir = self.dir / "references"
        if not references_dir.exists():
            return []
        return [f for f in references_dir.rglob("*") if f.is_file()]


class SkillLoader:
    """
    技能加载器

    特性：
    - 启动时仅加载元数据
    - 按需加载完整技能
    - 扫描 skills/ 目录
    - 支持热重载

    使用示例：
        >>> loader = SkillLoader(skills_dir=Path("skills"))
        >>> # 获取所有技能描述
        >>> descriptions = loader.get_descriptions()
        >>> # 按需加载完整技能
        >>> skill = loader.get_skill("pdf")
        >>> print(skill.body)
    """

    def __init__(self, skills_dir: Path):
        """初始化技能加载器

        Args:
            skills_dir: 技能目录路径
        """
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        # 完整技能缓存
        self.skills_cache: Dict[str, Skill] = {}

        # 仅元数据缓存（启动时加载）
        self.metadata_cache: Dict[str, Dict] = {}
        self.diagnostics: List[Dict[str, str]] = []

        # 启动时扫描并加载元数据
        self._scan_skills()

    def _scan_skills(self):
        """扫描 skills/ 目录，加载元数据"""
        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            # 只读取 frontmatter（元数据）
            metadata = self._parse_frontmatter_only(skill_md)
            if not metadata:
                continue

            name = metadata.get("name", skill_dir.name)
            if name in self.metadata_cache:
                self._diagnose(skill_md, f"重复的技能名称 {name}，保留先扫描的定义")
                continue
            self.metadata_cache[name] = {
                "name": name,
                "description": metadata.get("description", ""),
                "path": skill_md,
                "dir": skill_dir,
            }

    def _parse_frontmatter_only(self, path: Path) -> Optional[Dict]:
        """仅解析 YAML frontmatter

        Args:
            path: SKILL.md 文件路径

        Returns:
            解析后的元数据字典，如果解析失败则返回 None
        """
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            self._diagnose(path, f"无法读取技能文件: {exc}")
            return None

        # 匹配 --- 分隔符之间的内容
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)

        if not match:
            self._diagnose(path, "缺少有效的 YAML frontmatter")
            return None

        yaml_str = match.group(1)

        return self._parse_metadata(yaml_str, path)

    def _diagnose(self, path: Path, message: str):
        self.diagnostics.append({"path": str(path), "message": message})

    def _parse_metadata(self, yaml_str: str, path: Path) -> Optional[Dict]:
        """扫描与按需加载共用的结构校验；错误隔离到单个 Skill。"""
        try:
            metadata = yaml.safe_load(yaml_str) or {}
        except yaml.YAMLError as exc:
            self._diagnose(path, f"YAML 解析失败: {exc}")
            return None

        if not isinstance(metadata, dict):
            self._diagnose(path, "frontmatter 必须是包含 name 和 description 的对象")
            return None
        if not all(
            isinstance(metadata.get(key), str) and metadata[key].strip()
            for key in ("name", "description")
        ):
            self._diagnose(path, "name 和 description 必须是非空字符串")
            return None

        return metadata

    def get_descriptions(self) -> str:
        """获取所有技能的元数据描述（用于系统提示词）

        Returns:
            格式化的技能描述列表
        """
        if not self.metadata_cache:
            return "（暂无可用技能）"

        return "\n".join(
            f"- {name}: {skill['description']}"
            for name, skill in self.metadata_cache.items()
        )

    def get_skill(self, name: str) -> Optional[Skill]:
        """
        按需加载完整技能

        Args:
            name: 技能名称

        Returns:
            Skill 对象，如果不存在则返回 None
        """
        if not isinstance(name, str) or not name.strip():
            return None
        # 检查缓存
        if name in self.skills_cache:
            return self.skills_cache[name]

        # 检查元数据
        if name not in self.metadata_cache:
            return None

        metadata = self.metadata_cache[name]

        # 读取完整内容
        try:
            content = metadata["path"].read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            self._diagnose(metadata["path"], f"无法读取技能文件: {exc}")
            return None

        # 提取 frontmatter 和 body
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)

        if not match:
            self._diagnose(metadata["path"], "缺少有效的 YAML frontmatter")
            return None

        frontmatter, body = match.groups()

        # 解析 frontmatter（验证一致性）
        parsed_metadata = self._parse_metadata(frontmatter, metadata["path"])
        if parsed_metadata is None:
            return None
        if parsed_metadata["name"] != name:
            self._diagnose(metadata["path"], "技能名称自扫描后发生改变，请先 reload")
            return None

        # 创建 Skill 对象
        skill = Skill(
            name=parsed_metadata.get("name", name),
            description=parsed_metadata.get("description", ""),
            body=body.strip(),
            path=metadata["path"],
            dir=metadata["dir"],
        )

        # 缓存
        self.skills_cache[name] = skill

        return skill

    def list_skills(self) -> List[str]:
        """列出所有可用技能

        Returns:
            技能名称列表
        """
        return list(self.metadata_cache.keys())

    def reload(self):
        """重新扫描技能目录（热重载）"""
        self.skills_cache.clear()
        self.metadata_cache.clear()
        self.diagnostics.clear()
        self._scan_skills()
