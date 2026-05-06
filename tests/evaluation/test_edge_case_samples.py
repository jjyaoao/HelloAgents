"""
验证 BFCL 四类别边界测试样本的格式和 AST 匹配逻辑
"""

import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "evaluation", "benchmarks", "bfcl")
)

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

spec2 = importlib.util.spec_from_file_location(
    "edge_case_samples",
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "evaluation",
        "benchmarks",
        "bfcl",
        "edge_case_samples.py",
    ),
)
samples_mod = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(samples_mod)


def test_samples_have_required_fields():
    for name in [
        "SIMPLE_EDGE_CASES",
        "MULTIPLE_EDGE_CASES",
        "PARALLEL_EDGE_CASES",
        "IRRELEVANCE_EDGE_CASES",
    ]:
        samples = getattr(samples_mod, name)
        for s in samples:
            assert "id" in s, f"{name} sample missing id"
            assert "question" in s, f"{s['id']} missing question"
            assert "function" in s, f"{s['id']} missing function"
            assert "ground_truth" in s, f"{s['id']} missing ground_truth"
            assert isinstance(s["function"], list), f"{s['id']} function must be list"
            assert isinstance(s["ground_truth"], list), (
                f"{s['id']} ground_truth must be list"
            )
    print("[PASS] All samples have required fields")


def test_irrelevance_empty_ground_truth():
    for s in samples_mod.IRRELEVANCE_EDGE_CASES:
        assert s["ground_truth"] == [], f"{s['id']} should have empty ground_truth"
    print("[PASS] All irrelevance samples expect no function call")


def _gt_to_predicted_fn(gt_entry):
    """将单个 ground_truth dict 条目转为 predicted 格式

    BFCL v4 expected: {"func_name": {"param": [value1, value2]}}
    列表中的元素是此参数的可选值，取第一个即可。
    但如果值是列表嵌套，则表示值本身就是列表，不要 unwrap。
    """
    func_name = next(iter(gt_entry))
    params = gt_entry[func_name]
    args = {}
    for k, v in params.items():
        if isinstance(v, list):
            # 取第一个可接受值
            val = v[0] if v else None
            args[k] = val
        else:
            args[k] = v
    return {"name": func_name, "arguments": args}


def _gt_to_predicted(gt):
    """将 ground_truth dict 列表转为 predicted 格式"""
    return [_gt_to_predicted_fn(entry) for entry in gt]


def test_simple_ground_truth_matches_ast():
    matcher = create_default_matcher()
    for s in samples_mod.SIMPLE_EDGE_CASES:
        gt = s["ground_truth"]
        pred = _gt_to_predicted(gt)
        success, score = matcher.match(pred, gt)
        assert success and score == 1.0, (
            f"{s['id']} self-match should be 1.0, got {score}"
        )
    print("[PASS] All simple ground truths self-match correctly")


def test_multiple_ground_truth_matches_ast():
    matcher = create_default_matcher()
    for s in samples_mod.MULTIPLE_EDGE_CASES:
        gt = s["ground_truth"]
        pred = _gt_to_predicted(gt)
        success, score = matcher.match(pred, gt)
        assert success and score == 1.0, (
            f"{s['id']} self-match should be 1.0, got {score}"
        )
    print("[PASS] All multiple ground truths self-match correctly")


def test_parallel_ground_truth_matches_ast():
    matcher = create_default_matcher()
    for s in samples_mod.PARALLEL_EDGE_CASES:
        gt = s["ground_truth"]
        pred = _gt_to_predicted(gt)
        success, score = matcher.match(pred, gt)
        assert success and score == 1.0, (
            f"{s['id']} self-match should be 1.0, got {score}"
        )
    print("[PASS] All parallel ground truths self-match correctly")


def test_ground_truth_self_match():
    matcher = create_default_matcher()
    for name in [
        "SIMPLE_EDGE_CASES",
        "MULTIPLE_EDGE_CASES",
        "PARALLEL_EDGE_CASES",
        "IRRELEVANCE_EDGE_CASES",
    ]:
        samples = getattr(samples_mod, name)
        for s in samples:
            gt = s["ground_truth"]
            if not gt:
                pred = []
            else:
                pred = _gt_to_predicted(gt)
            success, score = matcher.match(pred, gt)
            assert success and score == 1.0, (
                f"{s['id']} self-match should be 1.0, got {score}"
            )
    print("[PASS] All ground truths self-match correctly")


def test_wrong_function_name_fails():
    matcher = create_default_matcher()
    gt = [{"get_weather": {"city": ["Tokyo"]}}]
    wrong = [{"name": "get_temperature", "arguments": {"city": "Tokyo"}}]
    success, _ = matcher.match(wrong, gt)
    assert not success, "Wrong function name should not match"
    print("[PASS] Wrong function name correctly rejected")


def test_missing_required_param_fails():
    matcher = create_default_matcher()
    gt = [{"create_user": {"name": ["Alice"], "profile": [{}], "tags": [[]]}}]
    missing = [{"name": "create_user", "arguments": {"name": "Alice"}}]
    success, _ = matcher.match(missing, gt)
    assert not success, "Missing required param should fail"
    print("[PASS] Missing required param correctly rejected")


def test_irrelevance_match_empty():
    matcher = create_default_matcher()
    gt = []
    predicted = []
    success, score = matcher.match(predicted, gt)
    assert success and score == 1.0, "Empty vs empty should match"
    print("[PASS] Irrelevance empty match works")


def test_irrelevance_unnecessary_call_fails():
    matcher = create_default_matcher()
    gt = []
    predicted = [{"name": "get_weather", "arguments": {"city": "Paris"}}]
    success, _ = matcher.match(predicted, gt)
    assert not success, "Calling a function when none expected should fail"
    print("[PASS] Unnecessary call correctly rejected")


def test_count_mismatch_fails():
    matcher = create_default_matcher()
    gt = [{"a": {"x": [1]}}, {"b": {"y": [2]}}]
    predicted = [{"name": "a", "arguments": {"x": 1}}]
    success, _ = matcher.match(predicted, gt)
    assert not success, "Count mismatch should fail"
    print("[PASS] Count mismatch correctly rejected")


def print_summary():
    print()
    total = (
        len(samples_mod.SIMPLE_EDGE_CASES)
        + len(samples_mod.MULTIPLE_EDGE_CASES)
        + len(samples_mod.PARALLEL_EDGE_CASES)
        + len(samples_mod.IRRELEVANCE_EDGE_CASES)
    )
    print(f"Total edge case samples: {total}")
    print(f"  Simple:      {len(samples_mod.SIMPLE_EDGE_CASES)}")
    print(f"  Multiple:    {len(samples_mod.MULTIPLE_EDGE_CASES)}")
    print(f"  Parallel:    {len(samples_mod.PARALLEL_EDGE_CASES)}")
    print(f"  Irrelevance: {len(samples_mod.IRRELEVANCE_EDGE_CASES)}")
    for s in samples_mod.SIMPLE_EDGE_CASES:
        print(f"    [{s['id']}] {s['_note']}")
    for s in samples_mod.MULTIPLE_EDGE_CASES:
        print(f"    [{s['id']}] {s['_note']}")
    for s in samples_mod.PARALLEL_EDGE_CASES:
        print(f"    [{s['id']}] {s['_note']}")
    for s in samples_mod.IRRELEVANCE_EDGE_CASES:
        print(f"    [{s['id']}] {s['_note']}")


if __name__ == "__main__":
    test_samples_have_required_fields()
    test_irrelevance_empty_ground_truth()
    test_simple_ground_truth_matches_ast()
    test_multiple_ground_truth_matches_ast()
    test_parallel_ground_truth_matches_ast()
    test_ground_truth_self_match()
    test_wrong_function_name_fails()
    test_missing_required_param_fails()
    test_irrelevance_match_empty()
    test_irrelevance_unnecessary_call_fails()
    test_count_mismatch_fails()
    print_summary()
    print("\n[PASS] All edge case tests passed!")
