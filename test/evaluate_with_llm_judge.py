"""
LLM Judge 评估脚本 - 本地数据加载

简化版本：仅支持本地 JSON/CSV 文件加载，保留字段映射功能
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from hello_agents.tools.builtin import LLMJudgeEvaluationTool
from hello_agents.core.llm import HelloAgentsLLM


# 配置
DATA_PATH = "test_data.json"
OUTPUT_DIR = "evaluation_results"

# 字段映射：{标准字段 -> 源字段}
# 例：{"problem": "question"} 表示 "problem" 是标准字段，源数据中为 "question"
FIELD_MAPPING = {
    "problem": "problem",
    "answer": "answer"
}

TEMPLATE_NAME = "math"
MAX_SAMPLES = 100


def example_basic():
    """
    基础示例：本地数据评估

    用途：最简单的使用方式，评估本地 JSON/CSV 数据
    特点：简洁明了，适合快速测试
    """
    # 创建 LLM 实例
    llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
    
    # 创建评估器
    evaluator = LLMJudgeEvaluationTool(template=TEMPLATE_NAME, llm=llm)

    result = evaluator.run({
        "source_config": {"path": DATA_PATH},
        "field_mapping": FIELD_MAPPING,

        "template": TEMPLATE_NAME,
        "max_samples": MAX_SAMPLES,
        "output_dir": OUTPUT_DIR  # 时间戳会自动添加
    })

    print(f"✅ 评估完成！")


def example_with_field_mapping():
    """
    字段映射示例：处理不同的源字段名

    用途：源数据的字段名与标准字段名不同时使用
    特点：演示字段映射的强大功能
    """
    print("\n" + "="*70)
    
    # 创建 LLM 实例
    llm = HelloAgentsLLM(model="gpt-4o")
    
    # 创建评估器
    evaluator = LLMJudgeEvaluationTool(template=TEMPLATE_NAME, llm=llm)

    result = evaluator.run({
        # 评估数据：字段名为 question, answer
        "source_config": {"path": "generated_data_simple.json"},
        "field_mapping": {
            "problem": "question",
            "answer": "answer"
        },

        "template": TEMPLATE_NAME,
        "max_samples": MAX_SAMPLES,
        "output_dir": OUTPUT_DIR
    })

    print(f"✅ 评估完成！")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎯 LLM Judge 评估工具")
    print("="*70)


    # 示例 1：基础本地评估
    example_basic()

    # 示例 2：字段映射
    # example_with_field_mapping()
