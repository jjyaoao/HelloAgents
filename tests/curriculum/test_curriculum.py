"""课程学习系统 - 完整单元测试

覆盖所有核心模块的功能测试。
"""

import sys
import os

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_dir = os.path.dirname(_test_dir)
sys.path.insert(0, _proj_dir)

from curriculum.types import (
    StageDefinition,
    StageType,
    ToolMetadata,
    StageProgress,
    CurriculumState,
)
from curriculum.planner import CurriculumPlanner
from curriculum.task_generator import TaskGenerator
from curriculum.evaluator import TransitionEvaluator
from curriculum.difficulty import DifficultyAdapter, DifficultyConfig
from curriculum.tracker import ProgressTracker
from curriculum.trainer import CurriculumTrainer
from curriculum.visualizer import CurriculumVisualizer


def test_stage_definition():
    """测试阶段定义"""
    stage = StageDefinition(
        stage_id="test_stage_1",
        stage_type=StageType.TOOL_INTRODUCTION,
        name="Introduce search",
        description="Learn to use search tool",
        tools=["search"],
        num_tasks=50,
    )
    assert stage.stage_id == "test_stage_1"
    assert stage.stage_type == StageType.TOOL_INTRODUCTION
    assert stage.tools == ["search"]
    assert stage.num_tasks == 50

    d = stage.to_dict()
    assert d["stage_type"] == "tool_introduction"

    stage2 = StageDefinition.from_dict(d)
    assert stage2.stage_id == stage.stage_id
    assert stage2.stage_type == stage.stage_type
    print(f"[PASS] StageDefinition: {stage.stage_id}")


def test_tool_metadata():
    """测试工具元数据"""
    registry = ToolMetadata.default_registry()
    assert len(registry) >= 5, f"Expected >=5 tools, got {len(registry)}"

    assert registry["search"].dependencies == []
    assert registry["calculator"].dependencies == []
    assert registry["file_writer"].dependencies == ["file_reader"]
    assert registry["data_analyzer"].dependencies == ["code_executor", "file_reader"]

    assert len(registry["search"].teaching_examples) >= 3
    print(f"[PASS] ToolMetadata: {len(registry)} tools, dependency graph valid")


def test_curriculum_planner():
    """测试课程规划器"""
    planner = CurriculumPlanner()
    stages = planner.plan_stages()

    assert len(stages) >= 4, f"Expected >=4 stages, got {len(stages)}"

    intro_stages = [s for s in stages if s.stage_type == StageType.TOOL_INTRODUCTION]
    assert len(intro_stages) >= 4, "Expected >=4 intro stages"

    compose_stages = [s for s in stages if s.stage_type == StageType.TOOL_COMPOSITION]
    assert len(compose_stages) >= 1

    conditional_stages = [
        s for s in stages if s.stage_type == StageType.CONDITIONAL_BRANCHING
    ]
    assert len(conditional_stages) == 1

    ids = [s.stage_id for s in stages]
    assert len(ids) == len(set(ids)), "Stage IDs should be unique"

    print(f"[PASS] CurriculumPlanner: {len(stages)} stages planned")


def test_task_generator():
    """测试任务生成"""
    generator = TaskGenerator(seed=42)

    stage = StageDefinition(
        stage_id="test_gen",
        stage_type=StageType.TOOL_INTRODUCTION,
        name="test",
        description="test",
        tools=["search", "calculator"],
        num_tasks=10,
    )
    tasks = generator.generate_tasks(stage, count=20)
    assert len(tasks) == 20, f"Expected 20 tasks, got {len(tasks)}"

    for t in tasks:
        assert t.question, "Task should have a question"
        assert t.required_tools, "Task should have required tools"
        assert 0 <= t.difficulty <= 1.0

    stage3 = StageDefinition(
        stage_id="test_multi",
        stage_type=StageType.TOOL_CHAINING,
        name="multi",
        description="test multi-tool",
        tools=["search", "calculator", "code_executor"],
        min_tools_per_task=3,
        max_tools_per_task=3,
        num_tasks=10,
    )
    tasks3 = generator.generate_tasks(stage3, count=5)
    assert len(tasks3) == 5

    print(f"[PASS] TaskGenerator: {len(tasks)} single-tool, {len(tasks3)} multi-tool")


def test_difficulty_adapter():
    """测试动态难度适配"""
    config = DifficultyConfig(
        target_success_rate=0.6,
        adjustment_rate=0.05,
        window_size=10,
        warmup_steps=5,
    )
    adapter = DifficultyAdapter(config)

    for _ in range(5):
        adapter.record_result(True, 0.5)
    assert adapter._current_difficulty == 0.5

    for _ in range(10):
        adapter.record_result(True, adapter._current_difficulty)
        adapter.get_adjusted_difficulty()
    assert adapter._current_difficulty > 0.5, "Difficulty should increase"

    for _ in range(15):
        adapter.record_result(False, adapter._current_difficulty)
        adapter.get_adjusted_difficulty()

    print("[PASS] DifficultyAdapter: adaptive adjustment works")


def test_transition_evaluator():
    """测试阶段过渡评估"""
    evaluator = TransitionEvaluator(consecutive_count=2)

    good_progress = StageProgress(
        stage_id="stage_test",
        tasks_completed=100,
        tasks_succeeded=85,
        total_steps=200,
        optimal_steps=150,
        tool_usage={"search": 50, "calculator": 50},
    )

    verdict = evaluator.evaluate_stage(good_progress)
    assert verdict.current_score >= 0.5

    bad_progress = StageProgress(
        stage_id="stage_test_bad",
        tasks_completed=100,
        tasks_succeeded=30,
        total_steps=500,
        optimal_steps=100,
        tool_usage={"search": 90, "calculator": 10},
    )
    verdict_bad = evaluator.evaluate_stage(bad_progress)
    assert verdict_bad.bottleneck is not None

    evaluator.reset_history()
    for _ in range(3):
        evaluator.evaluate_stage(good_progress)
    assert evaluator._check_can_advance(evaluator._history["stage_test"][-3:])

    print(
        f"[PASS] TransitionEvaluator: good={verdict.current_score:.2f}, "
        f"bad={verdict_bad.current_score:.2f}"
    )


def test_progress_tracker(tmpdir="./_test_curriculum_tmp"):
    """测试进度跟踪"""
    import shutil

    tracker = ProgressTracker(output_dir=tmpdir)

    state = CurriculumState(
        current_stage_index=2,
        stages=[
            StageProgress(stage_id="s1", tasks_completed=50, is_completed=True),
            StageProgress(stage_id="s2", tasks_completed=30, is_completed=True),
            StageProgress(stage_id="s3", tasks_completed=10),
        ],
        global_tasks_completed=90,
    )

    path = tracker.save_state(state)
    assert os.path.exists(path)

    loaded = tracker.load_state()
    assert loaded is not None
    assert loaded.current_stage_index == 2
    assert len(loaded.stages) == 3

    report_path = tracker.export_report(state)
    assert os.path.exists(report_path)

    shutil.rmtree(tmpdir, ignore_errors=True)
    print("[PASS] ProgressTracker: save/load/export OK")


def test_curriculum_trainer():
    """测试课程训练主循环"""
    trainer = CurriculumTrainer(auto_resume=False)

    call_count = [0]

    def mock_executor(task):
        call_count[0] += 1
        return {"success": True, "steps": 3, "reward": 1.0}

    trainer.set_task_executor(mock_executor)
    trainer.start()

    for _ in range(15):
        task = trainer.next_task()
        if task is None:
            break
        trainer.record_result(
            task_id=task.task_id,
            success=True,
            steps=3,
            optimal_steps=2,
            reward=1.0,
            tool_usage={"search": 2, "calculator": 1},
        )

    report = trainer.get_report()
    assert report["tasks_completed"] == 15
    assert report["status"] == "in_progress"

    print(
        f"[PASS] CurriculumTrainer: {report['tasks_completed']} tasks, "
        f"{report['total_stages']} stages"
    )


def test_visualizer():
    """测试可视化报告生成"""
    state = CurriculumState(
        current_stage_index=0,
        stages=[
            StageProgress(
                stage_id="s1",
                tasks_completed=50,
                tasks_succeeded=40,
                tool_usage={"search": 30, "calc": 20},
            ),
        ],
        global_tasks_completed=50,
        global_avg_reward=0.8,
        difficulty_level=0.6,
        all_tool_usage={"search": 30, "calc": 20},
    )

    report = CurriculumVisualizer.render_full_report(state, [], DifficultyAdapter())
    assert "CURRICULUM LEARNING REPORT" in report
    assert "s1" in report
    assert "search" in report
    assert len(report) > 100

    bar = CurriculumVisualizer.render_progress_bar(30, 100)
    assert "30/100" in bar

    heatmap = CurriculumVisualizer.render_tool_heatmap(state)
    assert "search" in heatmap
    assert "calc" in heatmap

    print("[PASS] CurriculumVisualizer: report generated")


if __name__ == "__main__":
    test_stage_definition()
    test_tool_metadata()
    test_curriculum_planner()
    test_task_generator()
    test_difficulty_adapter()
    test_transition_evaluator()
    test_progress_tracker()
    test_curriculum_trainer()
    test_visualizer()
    print("\n" + "=" * 50)
    print("ALL 9 TESTS PASSED!")
    print("=" * 50)
