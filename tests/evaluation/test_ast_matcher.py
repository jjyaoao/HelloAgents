"""
测试改进后的 AST 匹配算法

覆盖：
1. 参数顺序无关比较
2. 等价表达式求值
3. 格式差异（空格、引号）
4. 参数别名
5. 浮点数容差
6. 字符串归一化
7. 假阳性预防（函数名不同）
8. 假阴性预防（语义等价）
"""

import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "evaluation", "benchmarks", "bfcl")
)
sys.path.insert(0, os.path.dirname(__file__))

# 直接导入，绕过 hello_agents 包
import importlib.util

spec = importlib.util.spec_from_file_location(
    "ast_matcher",
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "evaluation",
        "benchmarks",
        "bfcl",
        "ast_matcher.py",
    ),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
ASTMatcher = mod.ASTMatcher
create_default_matcher = mod.create_default_matcher


def test_param_order_independent():
    """参数顺序不同应匹配成功"""
    matcher = create_default_matcher()
    predicted = [
        {"name": "get_weather", "arguments": {"city": "Beijing", "unit": "celsius"}}
    ]
    expected = [{"get_weather": {"unit": ["celsius"], "city": ["Beijing"]}}]
    success, score = matcher.match(predicted, expected)
    assert success and score == 1.0, f"参数顺序无关匹配失败: {success}, {score}"
    print("[PASS] test_param_order_independent PASS")


def test_constant_folding():
    """常量表达式求值：2+3 -> 5"""
    matcher = ASTMatcher(float_tolerance=1e-9)
    predicted = [{"name": "calculate", "arguments": {"x": 5}}]
    expected = [{"calculate": {"x": [5]}}]
    success, score = matcher.match(predicted, expected)
    assert success, "常量求值匹配失败"
    print("[PASS] test_constant_folding PASS")


def test_format_differences():
    """格式差异（空格、引号）"""
    matcher = ASTMatcher(normalize_strings=True)
    predicted = [{"name": "search", "arguments": {"query": "hello world"}}]
    expected = [{"search": {"query": ["hello  world"]}}]
    success, score = matcher.match(predicted, expected)
    assert success, "格式差异匹配失败"
    print("[PASS] test_format_differences PASS")


def test_param_aliases():
    """参数别名：loc -> location"""
    matcher = ASTMatcher(param_aliases={"location": ["loc", "city"]})
    predicted = [{"name": "get_weather", "arguments": {"loc": "Beijing"}}]
    expected = [{"get_weather": {"location": ["Beijing"]}}]
    success, score = matcher.match(predicted, expected)
    assert success, "参数别名匹配失败"
    print("[PASS] test_param_aliases PASS")


def test_float_tolerance():
    """浮点数容差比较"""
    matcher = ASTMatcher(float_tolerance=1e-6)
    predicted = [{"name": "compute", "arguments": {"value": 0.30000001}}]
    expected = [{"compute": {"value": [0.3]}}]
    success, score = matcher.match(predicted, expected)
    assert success, "浮点数容差匹配失败"
    print("[PASS] test_float_tolerance PASS")


def test_string_normalization():
    """字符串归一化：大小写、空格"""
    matcher = ASTMatcher(normalize_strings=True)
    predicted = [{"name": "greet", "arguments": {"name": "Alice"}}]
    expected = [{"greet": {"name": ["  alice  "]}}]
    success, score = matcher.match(predicted, expected)
    assert success, "字符串归一化匹配失败"
    print("[PASS] test_string_normalization PASS")


def test_false_positive_prevention():
    """假阳性预防：函数名不同应失败"""
    matcher = create_default_matcher()
    predicted = [{"name": "get_temperature", "arguments": {"city": "Beijing"}}]
    expected = [{"get_weather": {"city": ["Beijing"]}}]
    success, score = matcher.match(predicted, expected)
    assert not success, f"函数名不同应匹配失败: {success}"
    print("[PASS] test_false_positive_prevention PASS")


def test_false_negative_prevention():
    """假阴性预防：语义等价应匹配"""
    matcher = ASTMatcher(normalize_strings=True)
    predicted = [{"name": "search", "arguments": {"query": "The United States"}}]
    expected = [{"search": {"query": ["united states"]}}]
    success, score = matcher.match(predicted, expected)
    assert success, "语义等价匹配失败"
    print("[PASS] test_false_negative_prevention PASS")


def test_missing_optional_param():
    """缺失可选参数（有默认值）应匹配"""
    matcher = ASTMatcher(default_params={"format_date": {"timezone": "UTC"}})
    predicted = [{"name": "format_date", "arguments": {"date": "2025-01-01"}}]
    expected = [{"format_date": {"date": ["2025-01-01"]}}]
    success, score = matcher.match(predicted, expected)
    assert success, "缺失可选参数匹配失败"
    print("[PASS] test_missing_optional_param PASS")


def test_list_comparison():
    """列表排序后比较"""
    matcher = create_default_matcher()
    predicted = [{"name": "process", "arguments": {"items": [3, 1, 2]}}]
    expected = [{"process": {"items": [[1, 2, 3]]}}]
    success, score = matcher.match(predicted, expected)
    assert success, "列表排序比较失败"
    print("[PASS] test_list_comparison PASS")


def test_empty_call():
    """空函数调用"""
    matcher = create_default_matcher()
    predicted = [{"name": "noop", "arguments": {}}]
    expected = [{"noop": {}}]
    success, score = matcher.match(predicted, expected)
    assert success, "空函数调用匹配失败"
    print("[PASS] test_empty_call PASS")


def test_string_format():
    """字符串格式的 ground truth"""
    matcher = create_default_matcher()
    predicted = [{"name": "get_weather", "arguments": {"city": "Beijing"}}]
    expected = ["get_weather(city='Beijing')"]
    success, score = matcher.match(predicted, expected)
    assert success, "字符串格式匹配失败"
    print("[PASS] test_string_format PASS")


def test_none_predicted():
    """无预测 vs 空期望"""
    matcher = create_default_matcher()
    success, score = matcher.match([], [])
    assert success and score == 1.0, "空列表匹配失败"
    print("[PASS] test_none_predicted PASS")


if __name__ == "__main__":
    test_param_order_independent()
    test_constant_folding()
    test_format_differences()
    test_param_aliases()
    test_float_tolerance()
    test_string_normalization()
    test_false_positive_prevention()
    test_false_negative_prevention()
    test_missing_optional_param()
    test_list_comparison()
    test_empty_call()
    test_string_format()
    test_none_predicted()
    print("\nAll tests passed!")
