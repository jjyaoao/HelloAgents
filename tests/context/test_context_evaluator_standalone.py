"""上下文质量评估器测试

运行方式:
1. 直接运行: py tests/test_context_evaluator_standalone.py
2. pytest: py -m pytest tests/test_context_evaluator.py -v
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from hello_agents.context.evaluator import (
    ContextEvaluator,
    QualityReport,
    QualityMetrics,
    evaluate_context,
)


class TestQualityLevel:
    """测试质量等级映射"""

    def setup_method(self):
        self.evaluator = ContextEvaluator()

    def test_excellent_level(self):
        assert self.evaluator._score_to_level(0.9).value == "excellent"

    def test_good_level(self):
        assert self.evaluator._score_to_level(0.75).value == "good"

    def test_fair_level(self):
        assert self.evaluator._score_to_level(0.55).value == "fair"

    def test_poor_level(self):
        assert self.evaluator._score_to_level(0.35).value == "poor"

    def test_insufficient_level(self):
        assert self.evaluator._score_to_level(0.15).value == "insufficient"

    def test_level_boundaries(self):
        assert self.evaluator._score_to_level(0.85).value == "excellent"
        assert self.evaluator._score_to_level(0.849).value == "good"
        assert self.evaluator._score_to_level(0.70).value == "good"
        assert self.evaluator._score_to_level(0.699).value == "fair"


class TestContextEvaluator:
    """测试上下文评估器"""

    def setup_method(self):
        self.evaluator = ContextEvaluator()

    def test_evaluate_empty_context(self):
        report = self.evaluator.evaluate("", "test query")
        assert report.metrics.information_density == 0.0
        assert report.metrics.overall_score < 0.5

    def test_evaluate_good_context(self):
        good_context = """[Role & Policies]
你是一位Python数据工程专家。

[Task]
用户问题：如何优化Pandas的内存占用?

[Evidence]
1. 使用低精度数据类型
2. 使用category类型

[Context]
用户正在开发数据分析工具
"""
        report = self.evaluator.evaluate(good_context, "优化Pandas内存", 200)
        assert report.metrics.overall_score >= 0.3
        assert all(report.sections_present.values())

    def test_evaluate_with_missing_sections(self):
        report = self.evaluator.evaluate("[Task] test", "test")
        assert not report.sections_present["role"]
        assert not report.sections_present["evidence"]
        assert len(report.missing_components) > 0

    def test_markdown_report_generation(self):
        report = self.evaluator.evaluate("[Role] test", "test", 50)
        md = report.to_markdown()
        assert "# 上下文质量评估报告" in md
        assert "## 整体评分" in md

    def test_code_detection(self):
        code_context = """[Evidence]
```python
import pandas as pd
```
"""
        report = self.evaluator.evaluate(code_context, "pandas")
        assert report.metrics.information_density > 0.2

    def test_chinese_keywords(self):
        report = self.evaluator.evaluate("用户询问pandas内存优化问题", "pandas内存优化")
        assert report.metrics.relevance_score > 0


class TestEvaluateContextFunction:
    """测试便捷函数"""

    def test_convenience_function(self):
        report = evaluate_context("[Task] test", "test", 50)
        assert isinstance(report, QualityReport)


class TestQualityMetrics:
    """测试质量指标"""

    def test_quality_metrics_creation(self):
        metrics = QualityMetrics(
            information_density=0.8,
            relevance_score=0.7,
            completeness_score=0.9,
            overall_score=0.8,
        )
        assert metrics.information_density == 0.8
        assert metrics.overall_score == 0.8

    def test_quality_report_structure(self):
        report = QualityReport(
            metrics=QualityMetrics(overall_score=0.5),
            sections_present={"role": True, "evidence": False},
            missing_components=["证据"],
            optimization_suggestions=["添加证据"],
        )
        assert report.sections_present["role"]

        assert "证据" in report.missing_components


class TestContextBuilderIntegration:
    """测试 ContextBuilder 集成"""

    def setup_method(self):
        self.evaluator = ContextEvaluator()

    def test_build_with_evaluation(self):
        context = "[Role] test\n[Task] test\n[Evidence] test"
        query = "test"

        report = self.evaluator.evaluate(context, query)
        result = (context, report)

        assert isinstance(result, tuple)
        assert isinstance(result[0], str)
        assert isinstance(result[1].metrics.overall_score, float)


class TestRealWorldScenarios:
    """真实场景测试"""

    def setup_method(self):
        self.evaluator = ContextEvaluator()

    def test_data_science_query(self):
        context = """[Role & Policies]
你是一位资深Python数据工程顾问。

[Task]
用户问题：如何优化Pandas内存?

[Evidence]
1. 使用int32代替int64
2. 使用category类型

[Context]
用户正在开发数据分析工具
"""
        report = self.evaluator.evaluate(context, "优化Pandas内存", 300)
        assert report.metrics.overall_score >= 0.3
        assert report.sections_present["role"]

    def test_poor_context_suggestions(self):
        poor_context = "嗯，那个，就是这样。"
        report = self.evaluator.evaluate(poor_context, "测试")
        assert len(report.optimization_suggestions) > 0


def run_standalone():
    """独立运行入口"""
    print("=" * 60)
    print("Running Context Evaluator Tests")
    print("=" * 60)

    e = ContextEvaluator()
    tests_passed = 0
    tests_failed = 0

    def test(name, condition):
        nonlocal tests_passed, tests_failed
        if condition:
            print(f"  [PASS] {name}")
            tests_passed += 1
        else:
            print(f"  [FAIL] {name}")
            tests_failed += 1

    print("\n[TestQualityLevel]")
    test("EXCELLENT", e._score_to_level(0.9).value == "excellent")
    test("GOOD", e._score_to_level(0.75).value == "good")
    test("FAIR", e._score_to_level(0.55).value == "fair")
    test("POOR", e._score_to_level(0.35).value == "poor")
    test("INSUFFICIENT", e._score_to_level(0.15).value == "insufficient")

    print("\n[TestEmptyContext]")
    report = e.evaluate("", "test")
    test("Density = 0", report.metrics.information_density == 0.0)

    print("\n[TestGoodContext]")
    good_context = "[Role & Policies]专家[Task]问题[Evidence]证据[Context]背景"
    report = e.evaluate(good_context, "测试", 50)
    test("Overall >= 0.3", report.metrics.overall_score >= 0.3)

    print("\n[TestMissingSections]")
    report = e.evaluate("[Task] test", "test")
    test("Missing > 0", len(report.missing_components) > 0)

    print("\n[TestMarkdownReport]")
    md = report.to_markdown()
    test("Has title", "# 上下文质量评估报告" in md)

    print("\n" + "=" * 60)
    print("评估报告示例")
    print("=" * 60)
    print(report.to_markdown())
    print("=" * 60)

    print("\n[TestOptimizationSuggestions]")
    poor_context = "嗯，那个。"
    report = e.evaluate(poor_context, "测试")
    test("Suggestions > 0", len(report.optimization_suggestions) > 0)

    print("\n" + "=" * 60)
    print(f"Tests Passed: {tests_passed}")
    print(f"Tests Failed: {tests_failed}")
    print("=" * 60)

    # ========== 评估报告完整示例 ==========
    print("\n" + "=" * 60)
    print("完整评估报告示例")
    print("=" * 60)

    # 使用完整的上下文示例
    complete_context = """[Role & Policies]
你是一位Python数据工程专家。

[Task]
用户问题：如何优化Pandas内存占用？

[Evidence]
1. 使用int32代替int64节省50%内存
2. 使用category类型处理字符串列
3. 使用copy=False避免不必要复制

[Context]
用户正在开发数据分析工具，已完成CSV读取模块。

[Output]
1. 结论：数据类型优化可显著降低内存
2. 建议：优先处理数值列和字符串列
"""

    # 生成完整报告
    example_report = e.evaluate(complete_context, "Pandas内存优化", 300)
    print(example_report.to_markdown())

    return tests_failed == 0


if __name__ == "__main__":
    success = run_standalone()

    sys.exit(0 if success else 1)
