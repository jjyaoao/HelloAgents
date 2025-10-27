"""
Data Generation Evaluation Module

评估数据生成质量的模块，包括：
- LLM Judge: 使用LLM作为评委评估生成质量
- Win Rate: 通过对比评估计算胜率
- 支持自定义维度和数据格式适配
"""

from hello_agents.evaluation.benchmarks.data_generation_Universal.llm_judge import LLMJudgeEvaluator
from hello_agents.evaluation.benchmarks.data_generation_Universal.win_rate import WinRateEvaluator
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import (
    EvaluationConfig,
    EvaluationDimension,
)
from hello_agents.evaluation.benchmarks.data_generation_Universal.universal_dataset import (
    UniversalDataset,
)

__all__ = [
    "LLMJudgeEvaluator",
    "WinRateEvaluator",
    "EvaluationConfig",
    "EvaluationDimension",
    "UniversalDataset",
]

