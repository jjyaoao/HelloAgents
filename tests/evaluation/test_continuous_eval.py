"""持续评估系统 + 报告生成系统 单元测试"""

import sys
import os
from pathlib import Path

root = str(Path(__file__).resolve().parent.parent.parent)
sys.path.insert(0, root)
os.environ["PYTHONPATH"] = root

# 直接导入核心模块（跳过 evaluation/__init__.py 的顶级导入）
import importlib.util

spec_db = importlib.util.spec_from_file_location(
    "eval_db", os.path.join(root, "evaluation", "continuous_eval", "db.py")
)
mod_db = importlib.util.module_from_spec(spec_db)
spec_db.loader.exec_module(mod_db)

spec_gen = importlib.util.spec_from_file_location(
    "report_gen", os.path.join(root, "evaluation", "report_generator", "generator.py")
)
mod_gen = importlib.util.module_from_spec(spec_gen)
spec_gen.loader.exec_module(mod_gen)


def test_db_basic():
    from datetime import datetime

    now = datetime.now()
    db = mod_db.EvalDB(db_path="data/eval_data/test_ce_basic.db")
    db.save_snapshot(
        {
            "level": "quick",
            "timestamp": now.isoformat(),
            "metrics": {"bfcl_simple_accuracy": 0.92},
            "details": {},
        }
    )
    baseline = db.get_baseline("bfcl_simple_accuracy", days=30)
    print(f"   基线值: {baseline}")
    assert baseline is not None
    assert 0.9 <= baseline <= 1.0, f"基线={baseline}"
    print(f"  [PASS] test_db_basic: 基线={baseline:.2%}")


def test_trend_detector():
    import os
    from datetime import datetime, timedelta

    db_path = "data/eval_data/test_ce_trend3.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    now = datetime.now()
    db = mod_db.EvalDB(db_path=db_path)
    acc_values = [0.93, 0.92, 0.91, 0.88, 0.85, 0.82, 0.78]
    for i, acc in enumerate(acc_values):
        db.save_snapshot(
            {
                "level": "quick",
                "timestamp": (now - timedelta(hours=len(acc_values) - i)).isoformat(),
                "metrics": {"bfcl_simple_accuracy": acc},
                "details": {},
            }
        )

    detector = mod_db.TrendDetector(db)
    trend = db.get_trend("bfcl_simple_accuracy", days=30)
    baseline = db.get_baseline("bfcl_simple_accuracy", days=7)
    print(
        f"   趋势数据: {len(trend)} 条, 最后3个值: {[round(t[1], 2) for t in trend[-3:]]}"
    )
    print(f"   7天基线: {baseline}")
    # trend_down 检测最近3次: 0.85 -> 0.82 -> 0.78 全部下降，应触发 Warning
    latest = {
        "level": "quick",
        "timestamp": now.isoformat(),
        "metrics": {"bfcl_simple_accuracy": 0.78},
        "details": {},
    }
    alerts = detector.check(latest)
    print(f"   告警数: {len(alerts)}")
    for a in alerts:
        print(f"    [{a.severity}] {a.message}")
    assert len(alerts) >= 1, "trend_down 应触发告警"
    print(f"  [PASS] test_trend_detector: {len(alerts)} 条告警")
    for a in alerts:
        print(f"    [{a.severity}] {a.message}")


def test_report_generator():
    data = {
        "agent_version": "v2.3.1",
        "level": "standard",
        "duration_min": 45,
        "metrics": {
            "bfcl_simple_accuracy": 0.92,
            "bfcl_multiple_accuracy": 0.85,
            "bfcl_parallel_accuracy": 0.78,
            "bfcl_irrelevance_accuracy": 0.95,
        },
        "baseline": {
            "bfcl_simple_accuracy": 0.93,
            "bfcl_multiple_accuracy": 0.86,
            "bfcl_parallel_accuracy": 0.82,
            "bfcl_irrelevance_accuracy": 0.94,
        },
        "details": {
            "bfcl_details": [
                {
                    "sample_id": "s1",
                    "question": "test",
                    "predicted": "{}",
                    "expected": "{}",
                    "success": True,
                }
            ],
            "error_types": {"参数错误": 3, "函数名错误": 2},
            "sample_summary": {"查找天气": True},
        },
    }
    for audience in ["developer", "product", "user"]:
        gen = mod_gen.ReportGenerator(output_dir="data/eval_reports")
        report = gen.generate(data, audience)
        assert len(report) > 50, f"{audience} 报告为空"
        print(f"  [PASS] {audience} 报告: {len(report)} 字符")

    reports = mod_gen.ReportGenerator(output_dir="data/eval_reports").generate_all(data)
    assert len(reports) == 3
    print("  [PASS] generate_all: 3份报告")


if __name__ == "__main__":
    test_db_basic()
    test_trend_detector()
    test_report_generator()
    print("\n=== 全部测试通过 ===")
