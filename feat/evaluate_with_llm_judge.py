"""
LLM Judge 通用评估器 - 真实场景两层级对比测试

本脚本展示通用 LLM Judge 评估器在实际应用中的各种使用方式。

关键特点：
1. 多模板支持：math, code, writing, qa
2. 字段映射：处理不同数据格式的自适应对齐
3. 自定义维度：根据模板自动调整评估维度
4. 真实场景：模拟实际使用中的各种情况

案例 1：直接使用评估器（三个真实场景）
  场景 A：数学题评估（标准字段 + math 模板）
  场景 B：代码评估（字段映射 + code 模板）
  场景 C：写作评估（字段映射 + writing 模板）

案例 2：使用高级工具（一行搞定）
  自动处理数据加载、字段映射、模板切换、报告生成
"""

import sys
import os
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from hello_agents import (
    HelloAgentsLLM,
    UniversalLLMJudgeEvaluator,
    UniversalLLMJudgeTool,
)
from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import (
    EvaluationConfig,
)

# ============================================================================
# 测试数据准备（真实场景数据，包含不同字段名）
# ============================================================================


def prepare_test_data():
    """准备三种不同模板的测试数据"""

    # 场景 A：数学题（标准字段名）
    math_problems = [
        {
            "id": "math_001",
            "problem": "Find the number of positive integers $n$ such that $n^2 + 19n + 92$ is a perfect square.",
            "answer": "4",
            "solution": "Let $n^2 + 19n + 92 = m^2$. Completing the square: $(2n+19)^2 - 4m^2 = -7$. This gives us the Pell-like equation with limited solutions."
        },
        {
            "id": "math_002",
            "problem": "In triangle ABC with sides AB=13, BC=14, CA=15, find the area.",
            "answer": "84",
            "solution": "Using Heron's formula: $s=21$, Area $= \\sqrt{21 \\cdot 8 \\cdot 7 \\cdot 6} = 84$."
        }
    ]

    # 场景 B：代码评估（非标准字段：code, expected_output）
    code_problems = [
        {
            "id": "code_001",
            "code": """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
            """,
            "expected_output": "Returns correct fibonacci numbers",
            "context": "Write an optimized solution"
        },
        {
            "id": "code_002",
            "code": """
def sort_array(arr):
    for i in range(len(arr)):
        for j in range(len(arr)-1-i):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
            """,
            "expected_output": "Correctly sorted array in ascending order",
            "context": "Bubble sort implementation"
        }
    ]

    # 场景 C：写作评估（非标准字段：content, target）
    writing_problems = [
        {
            "id": "writing_001",
            "content": "Python is a high-level, interpreted programming language known for its simplicity and readability. It supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
            "target": "Technical article about Python",
            "length": "short"
        },
        {
            "id": "writing_002",
            "content": "Machine learning is revolutionizing how we approach data analysis. With algorithms that can learn patterns from data, ML enables computers to make predictions without explicit programming.",
            "target": "Educational blog post about ML",
            "length": "medium"
        }
    ]

    return math_problems, code_problems, writing_problems


def save_test_data():
    """保存测试数据到文件"""
    math_data, code_data, writing_data = prepare_test_data()

    os.makedirs("./test_data", exist_ok=True)

    with open("./test_data/math_problems.json", 'w', encoding='utf-8') as f:
        json.dump(math_data, f, indent=2, ensure_ascii=False)

    with open("./test_data/code_problems.json", 'w', encoding='utf-8') as f:
        json.dump(code_data, f, indent=2, ensure_ascii=False)

    with open("./test_data/writing_problems.json", 'w', encoding='utf-8') as f:
        json.dump(writing_data, f, indent=2, ensure_ascii=False)

    return math_data, code_data, writing_data


# ============================================================================
# 案例 1：直接使用评估器（三个真实场景）
# ============================================================================


def example_scene_a_math():
    """
    场景 A：数学题评估

    特点：
    - 使用 "math" 模板
    - 标准字段名（problem, answer, solution）
    - 无需字段映射
    - 维度：correctness, clarity, completeness, difficulty_match, originality
    """
    print("\n" + "="*70)
    print("📌 案例 1 - 场景 A：数学题评估（标准字段 + math 模板）")
    print("="*70)

    from hello_agents import HelloAgentsLLM, UniversalLLMJudgeEvaluator
    from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import (
        EvaluationConfig,
    )

    math_data, _, _ = save_test_data()

    # 创建 LLM 和评估器（使用 math 模板）
    print("\n[初始化] 创建 LLM 和评估器...")
    llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
    eval_config = EvaluationConfig.load_template("math")
    evaluator = UniversalLLMJudgeEvaluator(llm=llm, eval_config=eval_config)
    print(f"✓ 评估器已初始化（模板: math）")
    print(f"✓ 评估维度: {', '.join(eval_config.get_dimension_names())}")

    # 评估数学题
    print("\n[评估] 开始评估数学题...")
    print("="*70)
    print("🎯 Math 题目评估")
    print("="*70)

    all_scores = []

    for i, problem in enumerate(math_data, 1):
        print(f"\n评估题目 {i}/{len(math_data)}")
        print(f"题目ID: {problem['id']}")
        print(f"题目: {problem['problem'][:60]}...")

        result = evaluator.evaluate_single(problem)

        print(f"\n评估结果:")
        for dim, score in result['scores'].items():
            print(f"  {dim}: {score:.1f}/5")
        print(f"  平均分: {result['total_score']:.2f}/5")

        all_scores.append(result)

    # 统计
    print("\n" + "="*70)
    print("总体统计")
    print("="*70)

    avg_total = sum(s['total_score'] for s in all_scores) / len(all_scores)
    print(f"\n平均总分: {avg_total:.2f}/5")

    # 保存结果
    print("\n[保存] 保存评估结果...")
    os.makedirs("./evaluation_results", exist_ok=True)
    with open("./evaluation_results/scene_a_math.json", 'w', encoding='utf-8') as f:
        json.dump({
            'scenario': 'A_Math_Standard',
            'template': 'math',
            'field_mapping': 'None (standard fields)',
            'data': math_data,
            'results': all_scores,
            'avg_total_score': avg_total
        }, f, indent=2, ensure_ascii=False)

    print("✓ 结果已保存到 ./evaluation_results/scene_a_math.json")
    print("\n✅ 场景 A 完成！")


def example_scene_b_code():
    """
    场景 B：代码评估

    特点：
    - 使用 "code" 模板
    - 非标准字段名（code, expected_output）
    - 需要字段映射：code → problem, expected_output → answer
    - 维度：correctness, robustness, efficiency, readability, style_compliance
    """
    print("\n" + "="*70)
    print("📌 案例 1 - 场景 B：代码评估（字段映射 + code 模板）")
    print("="*70)

    from hello_agents import HelloAgentsLLM, UniversalLLMJudgeEvaluator
    from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import (
        EvaluationConfig,
    )

    _, code_data, _ = save_test_data()

    # 创建 LLM 和评估器（使用 code 模板 + 字段映射）
    print("\n[初始化] 创建 LLM 和评估器...")
    llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
    eval_config = EvaluationConfig.load_template("code")

    # 定义字段映射（自适应处理不同数据格式）
    field_mapping = {
        "problem": "code",                # 源数据中的 "code" 字段映射到 "problem"
        "answer": "expected_output",      # 源数据中的 "expected_output" 字段映射到 "answer"
    }

    evaluator = UniversalLLMJudgeEvaluator(
        llm=llm,
        eval_config=eval_config,
        field_mapping=field_mapping
    )
    print(f"✓ 评估器已初始化（模板: code）")
    print(f"✓ 评估维度: {', '.join(eval_config.get_dimension_names())}")
    print(f"✓ 字段映射: {field_mapping}")

    # 评估代码
    print("\n[评估] 开始评估代码...")
    print("="*70)
    print("🎯 Code 代码评估")
    print("="*70)

    all_scores = []

    for i, problem in enumerate(code_data, 1):
        print(f"\n评估代码 {i}/{len(code_data)}")
        print(f"代码ID: {problem['id']}")
        print(f"代码: {problem['code'][:40]}...")

        result = evaluator.evaluate_single(problem)

        print(f"\n评估结果:")
        for dim, score in result['scores'].items():
            print(f"  {dim}: {score:.1f}/5")
        print(f"  平均分: {result['total_score']:.2f}/5")

        all_scores.append(result)

    # 统计
    print("\n" + "="*70)
    print("总体统计")
    print("="*70)

    avg_total = sum(s['total_score'] for s in all_scores) / len(all_scores)
    print(f"\n平均总分: {avg_total:.2f}/5")

    # 保存结果
    print("\n[保存] 保存评估结果...")
    os.makedirs("./evaluation_results", exist_ok=True)
    with open("./evaluation_results/scene_b_code.json", 'w', encoding='utf-8') as f:
        json.dump({
            'scenario': 'B_Code_FieldMapping',
            'template': 'code',
            'field_mapping': field_mapping,
            'data': code_data,
            'results': all_scores,
            'avg_total_score': avg_total
        }, f, indent=2, ensure_ascii=False)

    print("✓ 结果已保存到 ./evaluation_results/scene_b_code.json")
    print("\n✅ 场景 B 完成！")


def example_scene_c_writing():
    """
    场景 C：写作评估

    特点：
    - 使用 "writing" 模板
    - 非标准字段名（content, target）
    - 需要字段映射：content → problem, target → answer
    - 维度：accuracy, coherence, richness, creativity_style, engagement
    """
    print("\n" + "="*70)
    print("📌 案例 1 - 场景 C：写作评估（字段映射 + writing 模板）")
    print("="*70)

    from hello_agents import HelloAgentsLLM, UniversalLLMJudgeEvaluator
    from hello_agents.evaluation.benchmarks.data_generation_Universal.evaluation_config import (
        EvaluationConfig,
    )

    _, _, writing_data = save_test_data()

    # 创建 LLM 和评估器（使用 writing 模板 + 字段映射）
    print("\n[初始化] 创建 LLM 和评估器...")
    llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
    eval_config = EvaluationConfig.load_template("writing")

    # 定义字段映射（自适应处理不同数据格式）
    field_mapping = {
        "problem": "content",           # 源数据中的 "content" 字段映射到 "problem"
        "answer": "target",             # 源数据中的 "target" 字段映射到 "answer"
    }

    evaluator = UniversalLLMJudgeEvaluator(
        llm=llm,
        eval_config=eval_config,
        field_mapping=field_mapping
    )
    print(f"✓ 评估器已初始化（模板: writing）")
    print(f"✓ 评估维度: {', '.join(eval_config.get_dimension_names())}")
    print(f"✓ 字段映射: {field_mapping}")

    # 评估写作
    print("\n[评估] 开始评估写作...")
    print("="*70)
    print("🎯 Writing 写作评估")
    print("="*70)

    all_scores = []

    for i, problem in enumerate(writing_data, 1):
        print(f"\n评估写作 {i}/{len(writing_data)}")
        print(f"写作ID: {problem['id']}")
        print(f"内容: {problem['content'][:40]}...")

        result = evaluator.evaluate_single(problem)

        print(f"\n评估结果:")
        for dim, score in result['scores'].items():
            print(f"  {dim}: {score:.1f}/5")
        print(f"  平均分: {result['total_score']:.2f}/5")

        all_scores.append(result)

    # 统计
    print("\n" + "="*70)
    print("总体统计")
    print("="*70)

    avg_total = sum(s['total_score'] for s in all_scores) / len(all_scores)
    print(f"\n平均总分: {avg_total:.2f}/5")

    # 保存结果
    print("\n[保存] 保存评估结果...")
    os.makedirs("./evaluation_results", exist_ok=True)
    with open("./evaluation_results/scene_c_writing.json", 'w', encoding='utf-8') as f:
        json.dump({
            'scenario': 'C_Writing_FieldMapping',
            'template': 'writing',
            'field_mapping': field_mapping,
            'data': writing_data,
            'results': all_scores,
            'avg_total_score': avg_total
        }, f, indent=2, ensure_ascii=False)

    print("✓ 结果已保存到 ./evaluation_results/scene_c_writing.json")
    print("\n✅ 场景 C 完成！")


# ============================================================================
# 案例 2：使用高级工具（一行搞定）
# ============================================================================


def example_high_level_tool():
    """
    案例 2：使用高级工具

    优点：
    - 一行代码搞定完整流程
    - 自动处理数据加载、字段映射、报告生成
    - 支持多模板和多数据源
    """
    print("\n" + "="*70)
    print("📌 案例 2：使用高级工具（UniversalLLMJudgeTool）")
    print("="*70)

    from hello_agents import HelloAgentsLLM, UniversalLLMJudgeTool

    math_data, _, _ = save_test_data()

    print("\n[初始化] 创建 LLM 和工具...")
    llm = HelloAgentsLLM(provider="deepseek", model="deepseek-chat")
    tool = UniversalLLMJudgeTool(template="math", llm=llm)
    print("✓ 工具已初始化")

    print("\n[运行] 调用 run() 方法进行完整评估...")

    # 保存数据到临时文件
    temp_data_path = "./test_data/temp_math_data.json"
    os.makedirs(os.path.dirname(temp_data_path), exist_ok=True)
    with open(temp_data_path, 'w', encoding='utf-8') as f:
        json.dump(math_data, f, indent=2, ensure_ascii=False)

    result = tool.run({
        "source_config": {"path": temp_data_path},
        "field_mapping": {"problem": "problem", "answer": "answer"},
        "template": "math",
        "max_samples": 2,
        "output_dir": "evaluation_results/case2_high_level"
    })

    print("\n" + "="*70)
    print("评估完成（高级工具自动生成报告和统计）")
    print("="*70)
    print(f"\n评估结果:\n{result}")

    print("\n✅ 案例 2 完成！")


# ============================================================================
# 主程序
# ============================================================================


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🎯 LLM Judge 通用评估器 - 真实场景两层级对比测试")
    print("="*70)

    # print("\n本脚本演示通用评估器在真实场景中的应用：")
    # print("\n📌 案例 1：直接使用评估器（灵活、透明）")
    # print("  场景 A：数学题 - 标准字段 + math 模板")
    # print("  场景 B：代码   - 字段映射 + code 模板")
    # print("  场景 C：写作   - 字段映射 + writing 模板")
    # print("\n📌 案例 2：使用高级工具（简洁、自动化）")

    # 运行案例 1 的三个场景
    print("\n" + "="*70)
    print("开始案例 1：直接使用评估器")
    print("="*70)

    example_scene_a_math()
    # example_scene_b_code()      # 取消注释来运行场景 B
    # example_scene_c_writing()   # 取消注释来运行场景 C

    # 运行案例 2
    print("\n" + "="*70)
    print("开始案例 2：使用高级工具")
    print("="*70)
    # example_high_level_tool()   # 取消注释来运行案例 2

    # 总结
    # print("\n" + "="*70)
    # print("📊 关键要点总结")
    # print("="*70)

    # print("\n🔑 通用评估器的核心能力：")
    # print("\n1. 多模板支持（Flexible）")
    # print("   ✓ math：数学题 - 重视正确性、难度匹配、创意解法")
    # print("   ✓ code：代码   - 重视鲁棒性、效率、代码风格")
    # print("   ✓ writing：写作 - 重视准确性、连贯性、创意表达")
    # print("   ✓ qa：问答   - 重视准确性、完整性、有用性")

    # print("\n2. 字段映射（Adaptive）")
    # print("   ✓ 自动处理不同数据格式")
    # print("   ✓ 支持非标准字段名")
    # print("   ✓ 无需修改源数据")

    # print("\n3. 两层级使用（Flexible Hierarchy）")
    # print("   低层级：UniversalLLMJudgeEvaluator - 灵活定制")
    # print("   高层级：UniversalLLMJudgeTool - 快速部署")

    # print("\n✅ 根据你的需求选择合适的使用方式！")
