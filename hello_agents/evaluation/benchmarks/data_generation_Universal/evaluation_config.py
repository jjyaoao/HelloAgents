"""
评估维度配置管理

支持自定义评估维度和评分规则
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class EvaluationDimension:
    """评估维度定义"""
    name: str                          # 维度名称，如 "correctness"
    description: str                   # 维度描述
    scale: int = 5                     # 评分范围 (1-scale)
    prompt_instruction: Optional[str] = None  # 自定义评估指令

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvaluationConfig:
    """评估配置管理"""

    # 预定义的标准维度
    STANDARD_DIMENSIONS = {
        "correctness": EvaluationDimension(
            name="correctness",
            description="数学逻辑是否正确，答案是否准确",
            scale=5
        ),
        "clarity": EvaluationDimension(
            name="clarity",
            description="问题表述是否清晰，解答是否易懂",
            scale=5
        ),
        "completeness": EvaluationDimension(
            name="completeness",
            description="解答步骤是否完整，推理是否充分",
            scale=5
        ),
    }

    # 预定义的评估模板
    TEMPLATES = {
        "math": {
            "correctness": "数学逻辑是否正确，最终答案是否准确无误。",
            "clarity": "问题表述是否清晰易懂，解题步骤的呈现是否逻辑分明。",
            "completeness": "解答步骤是否完整，推理过程是否严密且充分。",
            "difficulty_match": "问题的难度是否符合其声明或预期的标准。",
            "originality": "解答是否提供了多种解法，或展示了非标准但高效的、具有启发性的解题思路。"
        },
        "code": {
            "correctness": "代码逻辑是否正确，能否在典型用例下编译/运行并产出预期结果。",
            "robustness": "代码是否健壮，能否妥善处理异常输入和边界情况。",
            "efficiency": "算法的时间和空间复杂度是否合理，是否存在明显的性能瓶颈。",
            "readability": "代码是否清晰易懂，注释是否恰当，命名是否规范。",
            "style_compliance": "代码是否遵循了相应语言的最佳实践和通用编码规范（如PEP 8）。"
        },
        "writing": {
            "accuracy": "内容中的事实、数据和引用是否准确无误。",
            "coherence": "文章结构是否清晰，逻辑是否连贯，段落衔接是否自然。",
            "richness": "信息量是否丰富，论证是否充分，细节是否饱满。",
            "creativity_style": "语言运用是否生动、有文采，内容是否有新意和深度。",
            "engagement": "内容是否能引起读者兴趣，是否具有感染力或说服力。"
        },
        "qa": {
            "correctness": "答案是否准确，是否符合问题意图",
            "clarity": "答案是否清晰明了，表述是否准确",
            "completeness": "答案是否全面，是否涵盖关键信息",
            "helpfulness": "答案是否有帮助，是否解决了问题"
        }
    }

    def __init__(self, dimensions: Optional[List[EvaluationDimension]] = None):
        """
        初始化评估配置

        Args:
            dimensions: 自定义评估维度列表
                      如果为None，使用默认的4个维度
        """
        if dimensions is None:
            # 使用默认维度
            self.dimensions = list(self.STANDARD_DIMENSIONS.values())
        else:
            self.dimensions = dimensions

    @classmethod
    def load_template(cls, template_name: str) -> "EvaluationConfig":
        """
        从预定义模板加载评估配置

        Args:
            template_name: 模板名称，如 "math", "code", "writing", "qa"

        Returns:
            评估配置对象

        Raises:
            ValueError: 如果模板不存在
        """
        if template_name not in cls.TEMPLATES:
            available = list(cls.TEMPLATES.keys())
            raise ValueError(f"Unknown template: '{template_name}'. Available templates: {available}")
        return cls.custom(**cls.TEMPLATES[template_name])

    @classmethod
    def from_names(cls, dimension_names: List[str]) -> "EvaluationConfig":
        """
        从维度名称列表创建配置

        Args:
            dimension_names: 维度名称列表，如 ["correctness", "clarity"]

        Returns:
            评估配置对象
        """
        dimensions = []
        for name in dimension_names:
            if name in cls.STANDARD_DIMENSIONS:
                dimensions.append(cls.STANDARD_DIMENSIONS[name])
            else:
                # 如果不在标准维度中，创建一个基础的
                dimensions.append(EvaluationDimension(
                    name=name,
                    description=f"Custom dimension: {name}"
                ))
        return cls(dimensions)

    @classmethod
    def custom(cls, **kwargs) -> "EvaluationConfig":
        """
        创建自定义维度配置

        Args:
            **kwargs: 维度定义，格式为
                correctness="数学逻辑是否正确"
                clarity="表述是否清晰"
                custom_metric="自定义指标说明"

        Returns:
            评估配置对象
        """
        dimensions = [
            EvaluationDimension(name=name, description=desc, scale=5)
            for name, desc in kwargs.items()
        ]
        return cls(dimensions)

    def get_dimension_names(self) -> List[str]:
        """获取所有维度名称"""
        return [d.name for d in self.dimensions]

    def get_dimension(self, name: str) -> Optional[EvaluationDimension]:
        """获取指定维度"""
        for dim in self.dimensions:
            if dim.name == name:
                return dim
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "dimensions": [d.to_dict() for d in self.dimensions],
            "num_dimensions": len(self.dimensions)
        }

    @classmethod
    def get_available_templates(cls) -> List[str]:
        """获取所有可用的模板名称"""
        return list(cls.TEMPLATES.keys())

    @classmethod
    def get_template_dimensions(cls, template_name: str) -> Dict[str, str]:
        """获取模板中的维度信息"""
        if template_name not in cls.TEMPLATES:
            raise ValueError(f"Unknown template: '{template_name}'")
        return cls.TEMPLATES[template_name]
