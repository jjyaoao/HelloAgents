"""泛化能力评估测试"""

from hello_agents.rl.generalization import (
    GeneralizationEvaluator,
    GeneralizationMetrics,
    DataAugmentor,
    NumberTransformer,
    QuestionParaphraser,
    DifficultyAnalyzer,
    DifficultyLevel,
)


def test_number_transformer():
    """测试数值变换器"""
    print("测试数值变换器...")

    transformer = NumberTransformer(seed=42)

    text = "Natalia sold 48 clips in April and 24 in May. Total: 72"
    transformed = transformer.transform(text, 2.0)

    print(f"  原始: {text}")
    print(f"  变换(×2): {transformed}")

    assert "96" in transformed, "数值应该被乘以2"
    print("  ✓ 通过")


def test_question_paraphraser():
    """测试问题改写器"""
    print("测试问题改写器...")

    paraphraser = QuestionParaphraser(seed=42)

    question = "What is 48 + 24?"
    paraphrased = paraphraser.paraphrase(question)

    print(f"  原始: {question}")
    print(f"  改写: {paraphrased}")

    assert paraphrased != question, "改写后应该与原问题不同"
    print("  ✓ 通过")


def test_difficulty_analyzer():
    """测试难度分析器"""
    print("测试难度分析器...")

    analyzer = DifficultyAnalyzer()

    # 测试不同答案的步骤数
    # EASY: 1-2步
    easy_answer = "#### 24"  # 1步
    # MEDIUM: 3-4步 - 需要3个以上步骤
    medium_answer = "Step 1: 48/2 = 24\nStep 2: compute 48+24\nStep 3: 48+24 = 72\nFinal Answer: 72"  # 3步
    # HARD: 5-6步
    hard_answer = "Step 1: x = 48/2\nStep 2: y = 24+48\nStep 3: z = 72*2\nStep 4: result = 144\nStep 5: final = 288\n#### 288"  # 5步

    easy_steps = analyzer.count_reasoning_steps(easy_answer)
    medium_steps = analyzer.count_reasoning_steps(medium_answer)
    hard_steps = analyzer.count_reasoning_steps(hard_answer)

    print(f"  简单题步骤: {easy_steps} -> {analyzer.classify_difficulty(easy_steps)}")
    print(
        f"  中等题步骤: {medium_steps} -> {analyzer.classify_difficulty(medium_steps)}"
    )
    print(f"  困难题步骤: {hard_steps} -> {analyzer.classify_difficulty(hard_steps)}")

    # 验证分类
    assert analyzer.classify_difficulty(easy_steps) == DifficultyLevel.EASY
    assert analyzer.classify_difficulty(medium_steps) == DifficultyLevel.MEDIUM
    assert analyzer.classify_difficulty(hard_steps) == DifficultyLevel.HARD
    print("  ✓ 通过")


def mock_generate(question: str) -> str:
    """模拟的生成函数"""
    # 简单模拟：如果问题包含简单数值，返回正确答案
    # 如果是变换后的问题，可能返回错误（模拟过拟合）
    if "96" in question or "48 + 48" in question:
        # 变换后的问题答错（模拟过拟合）
        return "Final Answer: 100"
    elif "48" in question and "24" in question:
        return "Step 1: 48 + 24 = 72\nFinal Answer: 72"
    elif "32" in question:
        return "Step 1: 32 / 2 = 16\nFinal Answer: 16"
    else:
        return "Final Answer: 42"


def test_generalization_evaluator():
    """测试泛化能力评估器"""
    print("测试泛化能力评估器...")

    evaluator = GeneralizationEvaluator(generate_fn=mock_generate)

    test_data = [
        {"question": "What is 48 + 24?", "answer": "72"},
        {"question": "What is 32 divided by 2?", "answer": "16"},
        {"question": "Maria has 20 apples...", "answer": "35"},
    ]

    metrics = evaluator.evaluate(test_data)

    print(f"  基础准确率: {metrics.base_accuracy:.1%}")
    print(f"  数值鲁棒性: {metrics.numerical_robustness:.1%}")
    print(f"  结构鲁棒性: {metrics.structural_robustness:.1%}")
    print(f"  综合泛化得分: {metrics.generalization_score:.1%}")

    # 检测过拟合
    warnings = evaluator.detect_overfitting(metrics, train_accuracy=0.95)

    print(f"  过拟合警告数: {len(warnings)}")
    for w in warnings:
        print(f"    - [{w.level}] {w.message}")

    assert metrics.base_accuracy >= 0, "准确率应该非负"
    print("  ✓ 通过")


def test_data_augmentor():
    """测试数据增强器"""
    print("测试数据增强器...")

    augmentor = DataAugmentor(seed=42)

    data = [
        {"question": "What is 10 + 5?", "answer": "15"},
        {"question": "What is 20 divided by 4?", "answer": "5"},
    ]

    augmented = augmentor.augment(
        data, num_augmentations=2, strategies=["number", "paraphrase"]
    )

    print(f"  原始数据: {len(data)}")
    print(f"  增强后: {len(augmented)}")

    # 检查增强数据
    new_items = [x for x in augmented if x.get("augmented")]
    print(f"  新增样本: {len(new_items)}")

    for item in augmented:
        print(f"    Q: {item['question']}")
        if item.get("augmented"):
            print(f"      (策略: {item.get('strategy')})")

    assert len(augmented) > len(data), "应该生成更多数据"
    print("  ✓ 通过")


def test_overfit_detection():
    """测试过拟合检测"""
    print("测试过拟合检测...")

    evaluator = GeneralizationEvaluator(generate_fn=mock_generate)

    # 模拟一个过拟合的场景
    metrics = GeneralizationMetrics(
        base_accuracy=0.65,
        easy_accuracy=0.80,
        medium_accuracy=0.60,
        hard_accuracy=0.30,
        expert_accuracy=0.10,
        difficulty_slope=0.25,
        numerical_robustness=0.35,
        structural_robustness=0.40,
        generalization_score=0.45,
    )

    warnings = evaluator.detect_overfitting(metrics, train_accuracy=0.95)

    print(f"  检测到警告: {len(warnings)}")
    for w in warnings:
        print(f"    - [{w.level.upper()}] {w.message}")
        for s in w.suggestions:
            print(f"      建议: {s}")

    # 应该有多个警告
    assert len(warnings) >= 2, "应该检测到过拟合"
    print("  ✓ 通过")


if __name__ == "__main__":
    print("=" * 60)
    print("泛化能力评估模块测试")
    print("=" * 60)

    test_number_transformer()
    print()
    test_question_paraphraser()
    print()
    test_difficulty_analyzer()
    print()
    test_generalization_evaluator()
    print()
    test_data_augmentor()
    print()
    test_overfit_detection()

    print()
    print("=" * 60)
    print("所有测试通过!")
    print("=" * 60)
