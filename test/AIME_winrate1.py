"""
第十二章示例9：Win Rate评估

对应文档：12.4.4 Win Rate评估

这个示例展示如何使用Win Rate评估生成的AIME题目质量。

Win Rate评估通过对比生成题目和真题，评估生成质量：
- Win Rate = 50%：生成质量与真题相当（理想情况）
- Win Rate > 50%：生成质量优于真题（可能是评估偏差）
- Win Rate < 50%：生成质量低于真题（需要改进）
"""

import sys
import os
import json

# 添加HelloAgents路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "HelloAgents"))

from hello_agents import HelloAgentsLLM
from hello_agents.evaluation import WinRateEvaluator, AIDataset

# 1. 准备生成的题目数据
generated_problems = [
    {
        "problem_id": "generated_001",
        "problem": "Find the number of positive integers $n$ such that $n^2 + 19n + 92$ is a perfect square.",
        "answer": "4"
    },
    {
        "problem_id": "generated_002",
        "problem": "In triangle $ABC$, $AB = 13$, $BC = 14$, and $CA = 15$. Find the area of the triangle.",
        "answer": "84"
    },
    {
        "problem_id": "generated_003",
        "problem": "How many positive integers less than 1000 are divisible by 7 but not by 11?",
        "answer": "129"
    }
]

# 2. 加载参考数据集（AIME真题）
print("="*60)
print("Win Rate评估")
print("="*60)

print("\n加载参考数据集...")
dataset = AIDataset()
reference_problems = dataset.load()
print(f"✅ 已加载 {len(reference_problems)} 道AIME真题")

# 3. 创建Win Rate评估器
llm = HelloAgentsLLM(model_name="deepseek-chat")
evaluator = WinRateEvaluator(
    llm=llm,
    reference_problems=reference_problems
)

# 4. 运行Win Rate评估
print(f"\n开始Win Rate评估...")
print(f"  生成题目数: {len(generated_problems)}")
print(f"  对比数量: 20")

results = evaluator.evaluate(
    generated_problems=generated_problems,
    num_comparisons=20  # 进行20次对比
)

# 5. 显示评估结果
print("\n" + "="*60)
print("评估结果")
print("="*60)

print(f"\nWin Rate: {results['win_rate']:.2%}")
print(f"Tie Rate: {results['tie_rate']:.2%}")
print(f"Loss Rate: {results['loss_rate']:.2%}")

print(f"\n详细统计:")
print(f"  总对比数: {results['total_comparisons']}")
print(f"  生成题目胜: {results['wins']}")
print(f"  平局: {results['ties']}")
print(f"  真题胜: {results['losses']}")

# 6. 质量评估
print(f"\n质量评估:")
win_rate = results['win_rate']

if 0.45 <= win_rate <= 0.55:
    print("✅ 优秀 - 生成质量接近AIME真题水平")
elif 0.35 <= win_rate < 0.45:
    print("⚠️ 良好 - 生成质量可用，但略低于真题")
elif 0.25 <= win_rate < 0.35:
    print("⚠️ 一般 - 生成质量一般，需要改进")
else:
    print("❌ 较差 - 生成质量差，需要大幅改进")

# 7. 查看部分对比详情
print("\n" + "="*60)
print("对比详情（前5个）")
print("="*60)

for i, comparison in enumerate(results['comparisons'][:5], 1):
    print(f"\n对比 {i}:")
    print(f"  生成题目: {comparison['generated_problem'][:60]}...")
    print(f"  真题: {comparison['reference_problem'][:60]}...")
    print(f"  结果: {comparison['result']}")
    if 'reason' in comparison:
        print(f"  理由: {comparison['reason'][:100]}...")

# 8. 保存评估结果
output_file = "./evaluation_results/win_rate_results.json"
os.makedirs(os.path.dirname(output_file), exist_ok=True)

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n✅ 评估结果已保存到 {output_file}")

# 运行输出示例：
# ============================================================
# Win Rate评估
# ============================================================
# 
# 加载参考数据集...
# ✅ 已加载 963 道AIME真题
# 
# 开始Win Rate评估...
#   生成题目数: 3
#   对比数量: 20
# 
# Win Rate评估: 100%|██████████| 20/20 [01:00<00:00,  3.01s/对比]
# 
# ============================================================
# 评估结果
# ============================================================
# 
# Win Rate: 45.00%
# Tie Rate: 10.00%
# Loss Rate: 45.00%
# 
# 详细统计:
#   总对比数: 20
#   生成题目胜: 9
#   平局: 2
#   真题胜: 9
# 
# 质量评估:
# ✅ 优秀 - 生成质量接近AIME真题水平
# 
# ============================================================
# 对比详情（前5个）
# ============================================================
# 
# 对比 1:
#   生成题目: Find the number of positive integers $n$ such that $n^2 + 19...
#   真题: Let $N$ be the number of consecutive $0$'s at the right end...
#   结果: generated
#   理由: The generated problem has a clearer problem statement and a mo...
# 
# 对比 2:
#   生成题目: In triangle $ABC$, $AB = 13$, $BC = 14$, and $CA = 15$. F...
#   真题: Find the number of ordered pairs $(m,n)$ of positive integers...
#   结果: reference
#   理由: The reference problem is more challenging and requires deeper...
# 
# ...
# 
# ✅ 评估结果已保存到 ./evaluation_results/win_rate_results.json
