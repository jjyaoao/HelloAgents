"""
Win Rate 评估脚本 - 本地数据加载

简化版本：仅支持本地 JSON/CSV 文件加载，保留字段映射功能
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from hello_agents.tools.builtin import WinRateEvaluationTool
from hello_agents.core.llm import HelloAgentsLLM


# 配置
GENERATED_DATA_PATH = "test_data.json"
REFERENCE_DATA_PATH = "test1_data.json"

# 字段映射：{标准字段 -> 源字段}
# 例：{"problem": "question"} 表示 "problem" 是标准字段，源数据中为 "question"
FIELD_MAPPING = {
    "problem": "problem",
    "answer": "answer",
}

TEMPLATE_NAME = "writing"
NUM_COMPARISONS = 100
OUTPUT_DIR = "evaluation_results"


def example_basic():
    """
    基础示例：使用相同数据源的本地数据加载

    """
    print("\n" + "="*70)
    print("📌 示例 1：基础本地加载")
    print("="*70)

    # 创建 LLM 实例
    llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
    
    # 创建评估器
    evaluator = WinRateEvaluationTool(template=TEMPLATE_NAME, llm=llm)

    result = evaluator.run({
        "generated_config": {"path": GENERATED_DATA_PATH},
        "generated_field_mapping": FIELD_MAPPING,

        "reference_config": {"path": REFERENCE_DATA_PATH},
        "reference_field_mapping": FIELD_MAPPING,

        "template": TEMPLATE_NAME,
        "num_comparisons": NUM_COMPARISONS,
        "output_dir": OUTPUT_DIR
    })

    print(f"✅ 评估完成！")


def example_different_fields():
    """
    字段映射示例：处理不同的源字段名

    用途：生成数据和参考数据的字段名不同时使用
    特点：演示字段映射的强大功能
    """
    print("\n" + "="*70)
    print("📌 示例 2：字段映射（不同字段名）")
    print("="*70)

    # 创建 LLM 实例
    llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
    
    # 创建评估器
    evaluator = WinRateEvaluationTool(template=TEMPLATE_NAME, llm=llm)

    result = evaluator.run({
        # 生成数据：字段名为 question, answer
        "generated_config": {"path": "generated_data_simple.json"},
        "generated_field_mapping": {
            "problem": "question",
            "answer": "answer"
        },

        # 参考数据：字段名为 query, standard_answer
        "reference_config": {"path": "reference_data_rich.json"},
        "reference_field_mapping": {
            "problem": "query",
            "answer": "standard_answer"
        },

        "template": TEMPLATE_NAME,
        "num_comparisons": NUM_COMPARISONS,
        "output_dir": OUTPUT_DIR
    })

    print(f"✅ 评估完成！")


def example_csv_data():
    """
    CSV 数据示例：加载本地 CSV 文件

    用途：当数据存储在 CSV 文件中时使用
    特点：自动检测 CSV 格式，支持字段映射
    """
    print("\n" + "="*70)
    print("📌 示例 3：CSV 文件加载")
    print("="*70)

    # 创建 LLM 实例
    llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
    
    # 创建评估器
    evaluator = WinRateEvaluationTool(template=TEMPLATE_NAME, llm=llm)

    result = evaluator.run({
        # 生成数据：CSV 格式
        "generated_config": {
            "path": "data_generated.csv",
            "format": "csv"
        },
        "generated_field_mapping": {
            "problem": "question",
            "answer": "answer"
        },

        # 参考数据：CSV 格式
        "reference_config": {
            "path": "data_reference.csv",
            "format": "csv"
        },
        "reference_field_mapping": {
            "problem": "q",
            "answer": "a"
        },

        "template": TEMPLATE_NAME,
        "num_comparisons": NUM_COMPARISONS,
        "output_dir": OUTPUT_DIR
    })

    print(f"✅ 评估完成！")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎯 Win Rate 评估工具")
    print("="*70)



    # 示例 1：基础本地加载
    example_basic()

    # 示例 2：字段映射
    # example_different_fields()

    # 示例 3：CSV 文件加载
    # example_csv_data()
