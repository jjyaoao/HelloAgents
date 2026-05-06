"""
测试 BFCL 扩展评估功能（顺序验证、效率分析、错误报告）
"""

import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "evaluation", "benchmarks", "bfcl")
)

import importlib.util

_extended_spec = importlib.util.spec_from_file_location(
    "extended_evaluation",
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "evaluation",
        "benchmarks",
        "bfcl",
        "extended_evaluation.py",
    ),
)
mod = importlib.util.module_from_spec(_extended_spec)
_extended_spec.loader.exec_module(mod)

OrderValidator = mod.OrderValidator
EfficiencyAnalyzer = mod.EfficiencyAnalyzer
ErrorAnalyzer = mod.ErrorAnalyzer
DependencyRule = mod.DependencyRule


# ===== OrderValidator 测试 =====


def test_order_correct_sequence():
    """顺序正确：power → is_prime → factorize"""
    validator = OrderValidator(mode="strict")
    predicted = [
        {"name": "power", "arguments": {"base": 2, "exp": 10}},
        {"name": "is_prime", "arguments": {"n": 1024}},
        {"name": "factorize", "arguments": {"n": 1024}},
    ]
    expected = [
        {"power": {"base": [2], "exp": [10]}},
        {"is_prime": {"n": [1024]}},
        {"factorize": {"n": [1024]}},
    ]
    result = validator.validate(predicted, expected)
    assert result.correct, f"正确顺序应通过: {result.violations}"
    print("[PASS] test_order_correct_sequence")


def test_order_wrong_sequence():
    """顺序错误：factorize 在 power 之前"""
    validator = OrderValidator()
    predicted = [
        {"name": "factorize", "arguments": {"n": 1024}},
        {"name": "power", "arguments": {"base": 2, "exp": 10}},
    ]
    expected = [
        {"power": {"base": [2], "exp": [10]}},
        {"factorize": {"n": [1024]}},
    ]
    result = validator.validate(predicted, expected)
    assert not result.correct, "错误顺序应被检测到"
    print("[PASS] test_order_wrong_sequence")


def test_order_missing_producer():
    """缺少依赖提供者"""
    validator = OrderValidator(mode="strict")
    predicted = [
        {"name": "is_prime", "arguments": {"n": 1024}},
        {"name": "factorize", "arguments": {"n": 1024}},
    ]
    expected = [
        {"power": {"base": [2], "exp": [10]}},
        {"is_prime": {"n": [1024]}},
        {"factorize": {"n": [1024]}},
    ]
    result = validator.validate(predicted, expected)
    assert not result.correct, "strict 模式缺少 producer 应被检测到"
    violations_text = "; ".join(result.violations)
    assert "power" in violations_text, "应提示缺少 power"
    print("[PASS] test_order_missing_producer")


def test_order_no_rules():
    """没有依赖规则的单函数调用"""
    validator = OrderValidator()
    predicted = [{"name": "get_weather", "arguments": {"city": "Tokyo"}}]
    result = validator.validate(predicted, None)
    assert result.correct, "单函数无依赖应直接通过"
    print("[PASS] test_order_no_rules")


def test_order_strict_wrong():
    """strict 模式检查顺序：不同函数的顺序与 expected 不匹配"""
    validator = OrderValidator(mode="strict")
    predicted = [
        {
            "name": "search_flight",
            "arguments": {"origin": "NYC", "destination": "London"},
        },
        {
            "name": "book_seat",
            "arguments": {"flight_id": "FX123", "passenger_name": "Alice"},
        },
    ]
    expected = [
        {"book_seat": {"flight_id": ["FX123"], "passenger_name": ["Alice"]}},
        {"search_flight": {"origin": ["NYC"], "destination": ["London"]}},
    ]
    result = validator.validate(predicted, expected)
    assert not result.correct, "strict 模式应检测顺序差异"
    print("[PASS] test_order_strict_wrong")


# ===== EfficiencyAnalyzer 测试 =====


def test_efficiency_simple_optimal():
    """单个调用，最优"""
    analyzer = EfficiencyAnalyzer()
    predicted = [{"name": "get_weather", "arguments": {"city": "Tokyo"}}]
    expected = [{"get_weather": {"city": ["Tokyo"]}}]
    result = analyzer.analyze(predicted, expected)
    assert result.is_optimal, "单个调用应是最优"
    print("[PASS] test_efficiency_simple_optimal")


def test_efficiency_redundant_query():
    """重复查询同一纯函数，应检测为冗余"""
    analyzer = EfficiencyAnalyzer()
    predicted = [
        {"name": "get_weather", "arguments": {"city": "Tokyo"}},
        {"name": "get_weather", "arguments": {"city": "Tokyo"}},
    ]
    expected = [
        {"get_weather": {"city": ["Tokyo"]}},
    ]
    result = analyzer.analyze(predicted, expected)
    assert not result.is_optimal, "重复查询应被检测为冗余"
    assert any("被调用了 2 次" in r["reason"] for r in result.redundant_calls)
    print("[PASS] test_efficiency_redundant_query")


def test_efficiency_batch_alternative():
    """多次 send_email，应提示用 send_bulk_email"""
    analyzer = EfficiencyAnalyzer()
    predicted = [
        {"name": "send_email", "arguments": {"to": "a@x.com", "subject": "Hi"}},
        {"name": "send_email", "arguments": {"to": "b@x.com", "subject": "Hi"}},
    ]
    result = analyzer.analyze(predicted, [])
    assert not result.is_optimal, "多次单独 send_email 应提示批量"
    assert any("send_bulk_email" in r["reason"] for r in result.redundant_calls)
    print("[PASS] test_efficiency_batch_alternative")


def test_efficiency_no_redundancy():
    """不同函数调用，不应检测为冗余"""
    analyzer = EfficiencyAnalyzer()
    predicted = [
        {"name": "get_weather", "arguments": {"city": "Tokyo"}},
        {"name": "get_local_time", "arguments": {"city": "Tokyo"}},
    ]
    result = analyzer.analyze(predicted, [])
    assert result.is_optimal, "不同函数调用不应是冗余"
    print("[PASS] test_efficiency_no_redundancy")


def test_efficiency_count_mismatch():
    """调用次数多于期望"""
    analyzer = EfficiencyAnalyzer()
    predicted = [
        {"name": "get_weather", "arguments": {"city": "Tokyo"}},
        {"name": "get_weather", "arguments": {"city": "London"}},
        {"name": "get_weather", "arguments": {"city": "Paris"}},
    ]
    expected = [
        {"get_weather": {"city": ["Tokyo"]}},
        {"get_weather": {"city": ["London"]}},
    ]
    result = analyzer.analyze(predicted, expected)
    assert not result.is_optimal, "调用次数多于期望应被标记为非最优"
    print("[PASS] test_efficiency_count_mismatch")


# ===== ErrorAnalyzer 测试 =====


def test_error_missing_call():
    """遗漏调用"""
    analyzer = ErrorAnalyzer()
    result = {
        "success": False,
        "predicted": [{"name": "get_weather", "arguments": {"city": "Tokyo"}}],
        "expected": [
            {"get_weather": {"city": ["Tokyo"]}},
            {"get_weather": {"city": ["London"]}},
        ],
        "sample_id": "test_1",
        "question": "Get weather for Tokyo and London",
    }
    analyzer.analyze_result(result)
    assert analyzer.category_counts.get("missing_call", 0) == 1
    print("[PASS] test_error_missing_call")


def test_error_extra_call():
    """多余调用"""
    analyzer = ErrorAnalyzer()
    result = {
        "success": False,
        "predicted": [
            {"name": "get_weather", "arguments": {"city": "Tokyo"}},
            {"name": "get_weather", "arguments": {"city": "London"}},
            {"name": "get_weather", "arguments": {"city": "Paris"}},
        ],
        "expected": [
            {"get_weather": {"city": ["Tokyo"]}},
        ],
        "sample_id": "test_2",
        "question": "Get weather for Tokyo",
    }
    analyzer.analyze_result(result)
    assert analyzer.category_counts.get("extra_call", 0) == 1
    print("[PASS] test_error_extra_call")


def test_error_unnecessary_call():
    """不必要调用（irrelevance）"""
    analyzer = ErrorAnalyzer()
    result = {
        "success": False,
        "predicted": [
            {"name": "search_web", "arguments": {"query": "capital of France"}}
        ],
        "expected": [],
        "sample_id": "test_3",
        "question": "What is the capital of France?",
    }
    analyzer.analyze_result(result)
    assert analyzer.category_counts.get("unnecessary_call", 0) == 1
    print("[PASS] test_error_unnecessary_call")


def test_error_format_error():
    """格式解析错误"""
    analyzer = ErrorAnalyzer()
    result = {
        "success": False,
        "predicted": [],
        "expected": [{"get_weather": {"city": ["Tokyo"]}}],
        "sample_id": "test_4",
        "question": "Get weather for Tokyo",
    }
    analyzer.analyze_result(result)
    assert analyzer.category_counts.get("format_error", 0) == 1
    print("[PASS] test_error_format_error")


def test_error_report_generation():
    """生成完整错误报告"""
    analyzer = ErrorAnalyzer()
    fake_results = []
    for i in range(5):
        fake_results.append(
            {
                "success": i > 2,
                "predicted": [{"name": "get_weather", "arguments": {"city": "Tokyo"}}]
                if i > 0
                else None,
                "expected": [{"get_weather": {"city": ["Tokyo"]}}],
                "sample_id": f"sample_{i}",
                "question": f"Question {i}",
            }
        )
    report = analyzer.generate_report(10, fake_results)
    assert "错误类型分布" in report
    assert "改进建议" in report
    print("[PASS] test_error_report_generation")


# ===== 综合测试 =====


def test_integration_order_analysis():
    """综合测试：验证三个扩展组件的协同工作"""
    # 验证 evaluator.py 对扩展模块的导入
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "extended_eval_module",
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "evaluation",
            "benchmarks",
            "bfcl",
            "extended_evaluation.py",
        ),
    )
    if spec and spec.loader:
        mod2 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod2)
        assert hasattr(mod2, "OrderValidator")
        assert hasattr(mod2, "EfficiencyAnalyzer")
        assert hasattr(mod2, "ErrorAnalyzer")
        print("[PASS] test_integration_order_analysis (module structure)")


if __name__ == "__main__":
    test_order_correct_sequence()
    test_order_wrong_sequence()
    test_order_missing_producer()
    test_order_no_rules()
    test_order_strict_wrong()

    test_efficiency_simple_optimal()
    test_efficiency_redundant_query()
    test_efficiency_batch_alternative()
    test_efficiency_no_redundancy()
    test_efficiency_count_mismatch()

    test_error_missing_call()
    test_error_extra_call()
    test_error_unnecessary_call()
    test_error_format_error()
    test_error_report_generation()

    test_integration_order_analysis()

    print("\n[PASS] All extended evaluation tests passed!")
