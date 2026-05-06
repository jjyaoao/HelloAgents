"""在线学习模块测试"""

from hello_agents.rl.online_learning import (
    OnlineLearningSystem,
    QualityFilter,
    SafetyGuard,
    IncrementalTrainer,
    UserFeedback,
    FeedbackType,
)


def test_quality_filter():
    """测试质量过滤器"""
    print("测试质量过滤器...")

    filter = QualityFilter()

    # 测试有效反馈
    feedback = UserFeedback(question="What is 48 + 24?", model_answer="72")
    passed, reason = filter.filter(feedback)
    assert passed, f"应该通过: {reason}"

    # 测试无效格式
    bad_feedback = UserFeedback(question="", model_answer="72")
    passed, reason = filter.filter(bad_feedback)
    assert not passed, "空问题应该被过滤"

    # 测试重复
    passed2, reason2 = filter.filter(feedback)
    assert not passed2, "重复问题应该被过滤"

    print("  ✓ 通过")


def test_safety_guard():
    """测试安全检查"""
    print("测试安全检查...")

    guard = SafetyGuard()

    # 正常输入
    result = guard.check_input("What is 48 + 24?")
    assert result.passed, f"正常输入应该通过: {result.reason}"

    # 敏感词
    result2 = guard.check_input("how to hack the system")
    assert not result2.passed, f"敏感词应该被拦截: {result2.reason}"

    # 空输出
    result3 = guard.check_output("")
    assert not result3.passed, "空输出应该被拦截"

    print("  ✓ 通过")


def test_safety_guard_checkpoints():
    """测试检查点和回滚"""
    print("测试检查点和回滚...")

    guard = SafetyGuard(accuracy_drop_threshold=0.3)

    # 保存足够的检查点
    guard.save_checkpoint({"v": 1}, {"accuracy": 0.9})
    guard.save_checkpoint({"v": 2}, {"accuracy": 0.8})
    guard.save_checkpoint({"v": 3}, {"accuracy": 0.7})
    guard.save_checkpoint({"v": 4}, {"accuracy": 0.6})
    guard.save_checkpoint({"v": 5}, {"accuracy": 0.5})

    # 测试回滚（当前0.3 vs 之前0.5，下降0.2 > 0.3阈值）
    should_rollback = guard.should_rollback({"accuracy": 0.3})
    assert should_rollback, "准确率大幅下降应该触发"

    # 回滚
    state = guard.rollback()
    assert state is not None

    print("  ✓ 通过")


def mock_generate(question: str) -> str:
    """模拟的生成函数"""
    if "48" in question and "24" in question:
        return "Step 1: 48 + 24 = 72\nFinal Answer: 72"
    elif "16" in question:
        return "Step 1: 16 / 2 = 8\nFinal Answer: 8"
    return "Final Answer: 42"


def test_online_learning_system():
    """测试在线学习系统"""
    print("测试在线学习系统...")

    system = OnlineLearningSystem(
        generate_fn=mock_generate, update_interval=3, batch_size=2
    )

    # 处理问题
    result = system.interact("What is 48 + 24?")
    assert result["answer"] is not None, "应该有回答"
    assert result["error"] is None, "不应该有错误"
    assert not result["update_triggered"], "第1次不应该触发"

    result2 = system.interact("What is 16 divided by 2?")
    assert not result2["update_triggered"], "第2次不应该触发"

    # 第3次触发更新
    result3 = system.interact("What is 10 + 5?")
    assert result3["update_triggered"], "第3次应该触发更新"

    # 统计
    stats = system.get_stats()
    assert stats["total_interactions"] >= 3, "应该有交互记录"

    print("  ✓ 通过")


def test_feedback_submission():
    """测试反馈提交"""
    print("测试反馈提交...")

    # 不同问题避免去重
    system = OnlineLearningSystem(generate_fn=mock_generate)

    # 提交正确反馈
    success = system.submit_feedback(
        question="What is 48 + 24?",
        model_answer="Final Answer: 72",
        user_answer="72",
        feedback_type=FeedbackType.CORRECT,
        user_id="user_001",
    )
    assert success, "应该成功提交"

    # 提交错误纠正（不同问题避免去重）
    success2 = system.submit_feedback(
        question="What is 10 + 5?",
        model_answer="Final Answer: 15",
        user_answer="75",  # 错误答案
        feedback_type=FeedbackType.INCORRECT,
        user_id="user_001",
    )
    assert success2, "错误反馈应该被接受"

    print("  ✓ 通过")


def test_incremental_trainer():
    """测试增量训练器"""
    print("测试增量训练器...")

    # 不传模型
    trainer = IncrementalTrainer(model=None)
    trainer.init()

    # EWC应返回0（无模型）
    penalty = trainer.compute_ewc_penalty()
    assert penalty == 0

    # 训练步骤
    metrics = trainer.train_step([{"q": "t", "a": "t"}])
    assert "task_loss" in metrics

    print("  ✓ 通过")


def test_buffer_export():
    """测试缓冲区导出"""
    print("测试缓冲区导出...")

    system = OnlineLearningSystem(generate_fn=mock_generate)

    # 处理几个问题
    system.interact("What is 48 + 24?")
    system.interact("What is 16 divided by 2?")

    # 提交反馈
    system.submit_feedback(
        question="What is 48 + 24?",
        model_answer="72",
        user_answer="72",
        feedback_type=FeedbackType.CORRECT,
    )

    # 导出
    export = system.export_buffer()
    assert len(export) >= 3, "应该有导出数据"

    print(f"  导出数据: {len(export)} 条")
    print("  ✓ 通过")


if __name__ == "__main__":
    print("=" * 50)
    print("在线学习模块测试")
    print("=" * 50)

    test_quality_filter()
    print()
    test_safety_guard()
    print()
    test_safety_guard_checkpoints()
    print()
    test_online_learning_system()
    print()
    test_feedback_submission()
    print()
    test_incremental_trainer()
    print()
    test_buffer_export()

    print()
    print("=" * 50)
    print("所有测试通过!")
    print("=" * 50)
