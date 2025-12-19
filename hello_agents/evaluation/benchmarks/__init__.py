"""
Benchmarks 模块

包含各种智能体评估基准测试:
- BFCL: Berkeley Function Calling Leaderboard
- GAIA: General AI Assistants Benchmark
- Data Generation: 数据生成质量评估
  - AIME 版本: data_generation_AIME（专用于 AIME 数据集）
  - Universal 版本: data_generation_Universal（通用版本）
"""

from hello_agents.evaluation.benchmarks.bfcl.evaluator import BFCLEvaluator
from hello_agents.evaluation.benchmarks.gaia.evaluator import GAIAEvaluator

# Data Generation AIME 版本（原始版本）- 不带前缀
from hello_agents.evaluation.benchmarks.data_generation_AIME.llm_judge import LLMJudgeEvaluator
from hello_agents.evaluation.benchmarks.data_generation_AIME.win_rate import WinRateEvaluator

# Data Generation Universal 版本（通用版本）- 带前缀
from hello_agents.evaluation.benchmarks.data_generation_Universal.llm_judge import UniversalLLMJudgeEvaluator
from hello_agents.evaluation.benchmarks.data_generation_Universal.win_rate import UniversalWinRateEvaluator

__all__ = [
    "BFCLEvaluator",
    "GAIAEvaluator",
    # AIME 版本（不带前缀）
    "LLMJudgeEvaluator",
    "WinRateEvaluator",
    # Universal 版本（带前缀）
    "UniversalLLMJudgeEvaluator",
    "UniversalWinRateEvaluator",
]

