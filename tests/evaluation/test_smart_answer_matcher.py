"""
SmartAnswerMatcher 单元测试

直接运行：py -m pytest tests/test_smart_answer_matcher.py -v
"""

import sys
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "evaluation", "benchmarks", "gaia")
)

import pytest
from smart_answer_matcher import SmartAnswerMatcher


@pytest.fixture
def matcher():
    return SmartAnswerMatcher(llm=None, use_semantic=True, use_llm_judge=False)


class TestQuasiExactMatch:
    def test_exact_string(self, matcher):
        result = matcher.match("Paris", "Paris")
        assert result.match
        assert result.method == "quasi_exact"

    def test_case_insensitive(self, matcher):
        result = matcher.match("paris", "Paris")
        assert result.match

    def test_article_removal(self, matcher):
        result = matcher.match("the apple", "apple")
        assert result.match

    def test_currency_removal(self, matcher):
        result = matcher.match("$ 100", "100")
        assert result.match

    def test_trailing_punctuation(self, matcher):
        result = matcher.match("hello.", "hello")
        assert result.match

    def test_extra_spaces(self, matcher):
        result = matcher.match("hello   world", "hello world")
        assert result.match


class TestNumericEquivalence:
    def test_sci_notation(self, matcher):
        result = matcher.match("2.5e6", "2500000")
        assert result.match
        assert result.method == "numeric_equiv"

    @pytest.mark.parametrize(
        "a,b",
        [
            ("1/2", "0.5"),
            ("3/4", "0.75"),
            ("-1/2", "-0.5"),
        ],
    )
    def test_fraction(self, matcher, a, b):
        result = matcher.match(a, b)
        assert result.match

    @pytest.mark.parametrize(
        "a,b",
        [
            ("42", "四十二"),
            ("一百", "100"),
            ("三千零一", "3001"),
        ],
    )
    def test_chinese_number(self, matcher, a, b):
        result = matcher.match(a, b)
        assert result.match

    def test_percentage_decimal(self, matcher):
        result = matcher.match("50%", "0.5")
        assert result.match

    def test_float_equivalence(self, matcher):
        result = matcher.match("3.14", "3.1400001")
        assert result.match


class TestUnitConversion:
    @pytest.mark.parametrize(
        "a,b",
        [
            ("2 km", "2000 m"),
            ("1.5 kg", "1500 g"),
            ("12 inches", "1 foot"),
            ("3 feet", "1 yard"),
            ("1 hour", "3600 seconds"),
            ("60 minutes", "1 hour"),
        ],
    )
    def test_unit_equivalence(self, matcher, a, b):
        result = matcher.match(a, b)
        assert result.match

    @pytest.mark.parametrize(
        "a,b",
        [
            ("2 hours 30 minutes", "150 minutes"),
            ("1 hour 30 min", "90 minutes"),
            ("2h 30m", "9000 seconds"),
            ("90 min", "1.5 hours"),
        ],
    )
    def test_composite_time(self, matcher, a, b):
        result = matcher.match(a, b)
        assert result.match, f"composite time: {a} != {b}"

    @pytest.mark.parametrize(
        "a,b",
        [
            ("32 F", "0 C"),
            ("212 F", "100 C"),
            ("0 C", "32 F"),
            ("100 C", "212 F"),
            ("0 K", "-273.15 C"),
        ],
    )
    def test_temperature(self, matcher, a, b):
        result = matcher.match(a, b)
        assert result.match, f"temperature: {a} != {b}"


class TestMathExpression:
    @pytest.mark.parametrize(
        "a,b",
        [
            ("pi/2", "1.5708"),
            ("2*pi", "6.2832"),
            ("sqrt(4)", "2"),
            ("2+3", "5"),
            ("10/3", "3.3333"),
        ],
    )
    def test_math_expression(self, matcher, a, b):
        result = matcher.match(a, b)
        assert result.match, f"math: {a} != {b} (method={result.method})"


class TestSemanticEquivalence:
    def test_substring(self, matcher):
        result = matcher.match("Paris is the capital of France", "Paris")
        assert result.match
        assert result.method == "semantic_equiv_substring"

    def test_number_in_text(self, matcher):
        result = matcher.match("about 42", "42")
        assert result.match

    def test_high_jaccard(self, matcher):
        result = matcher.match("united states", "united states of america")
        assert result.match

    def test_no_match(self, matcher):
        result = matcher.match("apples are red", "the sky is blue")
        assert not result.match
        assert result.method == "no_match"


class TestEdgeCases:
    def test_empty_prediction(self, matcher):
        assert not matcher.match("", "42").match

    def test_empty_ground_truth(self, matcher):
        assert not matcher.match("42", "").match

    def test_both_empty(self, matcher):
        assert not matcher.match("", "").match

    def test_none_prediction(self, matcher):
        assert not matcher.match(None, "42").match

    def test_whitespace_only(self, matcher):
        assert not matcher.match("   ", "42").match


class TestBatch:
    def test_batch(self, matcher):
        results = matcher.match_batch(
            [
                ("42", "42"),
                ("1/2", "0.5"),
                ("2 km", "2000 m"),
                ("", "42"),
            ]
        )
        assert [r.match for r in results] == [True, True, True, False]

    def test_match_dict(self, matcher):
        out = matcher.match_dict(
            [
                {"task_id": "1", "predicted": "42", "expected": "42"},
                {"task_id": "2", "predicted": "1/2", "expected": "0.5"},
                {"task_id": "3", "predicted": "100", "expected": "999"},
            ]
        )
        assert out["total_samples"] == 3
        assert out["smart_match_rate"] == pytest.approx(2 / 3)
        assert out["improvement"]["new_correct"] == 2


class TestQuasiMissedCases:
    """GAIA 准精确匹配遗漏但 SmartMatcher 能捕获的案例"""

    def test_cases(self, matcher):
        cases = [
            ("42", "42", True, True),
            ("1/2", "0.5", False, True),
            ("2 km", "2000 m", False, True),
            ("pi", "3.14159", False, True),
            ("一百", "100", False, True),
            ("2 hours 30 minutes", "150 minutes", False, True),
            ("32 F", "0 C", False, True),
            ("Paris", "London", False, False),
        ]
        for pred, exp, eq, es in cases:
            q = matcher._quasi_exact_match(pred, exp)
            s = matcher.match(pred, exp)
            assert q == eq, f"quasi {pred} vs {exp}: exp {eq}, got {q}"
            assert s.match == es, (
                f"smart {pred} vs {exp}: exp {es}, got {s.match} ({s.method})"
            )
