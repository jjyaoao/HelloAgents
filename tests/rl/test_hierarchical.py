"""分层强化学习模块单元测试"""

import sys
import os
import types

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_dir = os.path.dirname(_test_dir)
if _proj_dir not in sys.path:
    sys.path.insert(0, os.path.dirname(_proj_dir))

# Mock external dependencies
datasets_mod = types.ModuleType("datasets")
datasets_mod.load_dataset = lambda *a, **kw: None
datasets_mod.Dataset = type("Dataset", (), {})
sys.modules["datasets"] = datasets_mod

trl_mod = types.ModuleType("trl")
trl_mod.SFTConfig = type("SFTConfig", (), {})
trl_mod.SFTTrainer = type("SFTTrainer", (), {})
trl_mod.GRPOConfig = type("GRPOConfig", (), {})
trl_mod.GRPOTrainer = type("GRPOTrainer", (), {})
trl_mod.apply_chat_template = lambda *a, **kw: ""
sys.modules["trl"] = trl_mod


from hello_agents.rl.hierarchical.high_level_policy import (
    HighLevelPolicy,
    SubgoalType,
    Subgoal,
)
from hello_agents.rl.hierarchical.low_level_policy import (
    LowLevelPolicy,
    ToolCall,
)
from hello_agents.rl.hierarchical.reward import (
    HierarchicalReward,
    create_hierarchical_reward_function,
)
from hello_agents.rl.hierarchical.coordinator import PolicyCoordinator, ExecutionStatus
from hello_agents.rl.hierarchical.curriculum import (
    CurriculumTaskGenerator,
    StageReadinessEvaluator,
    ToolDependencyGraph,
    StageID,
)
from hello_agents.rl.hierarchical.trainer import HierarchicalTrainingConfig


def test_high_level_policy():
    """测试高层策略：子目标规划"""
    hp = HighLevelPolicy()
    task = "Search for the population of Japan, then calculate 5% of it."
    subgoals = hp.generate(task, tool_descriptions="search, calculator")
    assert len(subgoals) > 0, "Should generate at least 1 subgoal"
    assert all(isinstance(sg, Subgoal) for sg in subgoals), (
        "All items should be Subgoal"
    )
    assert all(sg.type in SubgoalType for sg in subgoals), "Valid subgoal types"
    print(f"[PASS] HighLevelPolicy: generated {len(subgoals)} subgoals")


def test_low_level_policy_tool_call():
    """测试低层策略：工具调用解析"""
    tc_text = (
        "Thought: I need to search first\nAction: search[query=population of Japan]"
    )
    tc = ToolCall.from_string(tc_text)
    assert tc is not None, "Should parse valid tool call"
    assert tc.tool_name == "search", f"Expected 'search', got '{tc.tool_name}'"
    assert tc.arguments.get("query") == "population of Japan", (
        "Should extract arguments"
    )

    serialized = tc.to_string()
    tc2 = ToolCall.from_string(serialized)
    assert tc2 is not None, "Should parse serialized form"
    assert tc2.tool_name == tc.tool_name, "Round-trip preserve tool name"
    print(
        f"[PASS] LowLevelPolicy ToolCall: parsed '{tc.tool_name}' args={tc.arguments}"
    )


def test_hierarchical_reward():
    """测试分层奖励函数"""
    reward = HierarchicalReward()

    subgoals = [
        Subgoal(SubgoalType.SEARCH, "Search for info"),
        Subgoal(SubgoalType.CALCULATE, "Calculate result", depends_on=[0]),
    ]
    high_r = reward.compute_high_reward(
        predicted_subgoals=subgoals,
        task_success=True,
    )
    assert "completeness" in high_r
    assert "dependency" in high_r
    assert "granularity" in high_r
    assert "task_success" in high_r

    low_r = reward.compute_low_reward(
        trajectory=[
            {"type": "tool_call", "tool_call": None, "observation": "Success"},
            {"type": "finish", "result": "42"},
        ],
        subgoal_success=True,
    )
    assert "tool_correctness" in low_r
    assert "parameter_quality" in low_r
    assert "efficiency" in low_r

    result = reward.compute_total_reward(high_r, low_r)
    assert 0 <= result.total <= 2.0, f"Total reward {result.total} should be in [0, 2]"
    print(
        f"[PASS] HierarchicalReward: total={result.total:.3f}, high={sum(high_r.values()) / 4:.2f}"
    )


def test_policy_coordinator():
    """测试策略协调器"""
    hp = HighLevelPolicy()
    lp = LowLevelPolicy()
    coord = PolicyCoordinator(hp, lp)

    report = coord.execute_task(
        "Find the capital of France and calculate its population density.",
        tool_descriptions="search, calculator",
    )
    assert report.task is not None
    assert isinstance(report.subgoals, list)
    assert report.total_steps >= 0

    high_r = coord.compute_high_reward_from_report(report)
    assert "completeness" in high_r
    print(
        f"[PASS] PolicyCoordinator: {len(report.subgoals)} subgoals, task_success={report.task_success}"
    )


def test_tool_dependency_graph():
    """测试工具依赖图"""
    graph = ToolDependencyGraph()
    stages = graph.get_stages()
    assert len(stages) > 0, "Should generate stages"
    assert all(s.stage_id in StageID for s in stages), "Valid stage IDs"
    print(f"[PASS] ToolDependencyGraph: {len(stages)} stages generated")


def test_curriculum_generator():
    """测试课程任务生成器"""
    gen = CurriculumTaskGenerator()
    stages = gen.get_stages()

    all_tasks = []
    for stage in stages:
        tasks = gen.generate_tasks(stage, count=5)
        all_tasks.extend(tasks)
        assert len(tasks) > 0, f"Stage {stage.stage_id.value} should generate tasks"
        for t in tasks:
            assert isinstance(t, str) and len(t) > 10, "Task should be meaningful text"

    print(
        f"[PASS] CurriculumTaskGenerator: {sum(len(gen.generate_tasks(s, 3)) for s in stages)} tasks from {len(stages)} stages"
    )


def test_readiness_evaluator():
    """测试阶段过渡评估器"""
    evaluator = StageReadinessEvaluator(consecutive_count=2)

    score = evaluator.evaluate(
        success_rate=0.8,
        steps_taken=10,
        optimal_steps=8,
        tool_usage_counts={"search": 5, "calc": 5},
        total_attempts=10,
        held_out_success_rate=0.7,
    )
    assert score.overall >= 0.6, (
        f"Good scores should yield overall >= 0.6, got {score.overall}"
    )
    assert score.bottleneck is not None, "Should identify bottleneck"

    assert not evaluator.should_advance(), "Should not advance after 1 eval"

    evaluator.evaluate(
        success_rate=0.85,
        steps_taken=9,
        optimal_steps=8,
        tool_usage_counts={"search": 6, "calc": 4},
        total_attempts=10,
        held_out_success_rate=0.8,
    )
    ready = evaluator.should_advance()
    print(
        f"[PASS] StageReadinessEvaluator: overall={score.overall:.3f}, ready={ready}, bottleneck={score.bottleneck}"
    )


def test_training_config():
    """测试训练配置"""
    config = HierarchicalTrainingConfig()
    assert config.high_model_name == "Qwen/Qwen3-0.6B"
    assert config.low_learning_rate == 5e-5
    assert config.joint_batch_size == 4
    assert config.use_lora
    print("[PASS] HierarchicalTrainingConfig: defaults OK")


def test_reward_function_factory():
    """测试奖励函数工厂"""
    reward_fn = create_hierarchical_reward_function()
    result = reward_fn(["test completion"], ground_truth=["42"])
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], float)
    print(
        f"[PASS] create_hierarchical_reward_function: returns callable, result={result}"
    )


def test_coordinator_high_low_reward_extraction():
    """测试协调器从执行报告提取高层/低层奖励"""
    hp = HighLevelPolicy()
    lp = LowLevelPolicy()
    coord = PolicyCoordinator(hp, lp)

    from hello_agents.rl.hierarchical.coordinator import ExecutionReport, SubgoalResult

    report = ExecutionReport(
        task="test task",
        subgoals=[
            SubgoalResult(
                index=0,
                description="search info",
                status=ExecutionStatus.SUCCESS,
                trajectory=[
                    {"type": "tool_call", "tool_call": None, "observation": "ok"}
                ],
                summary="Done",
                steps_taken=1,
            ),
            SubgoalResult(
                index=1,
                description="calculate",
                status=ExecutionStatus.SUCCESS,
                trajectory=[
                    {"type": "tool_call", "tool_call": None, "observation": "42"}
                ],
                summary="Done",
                steps_taken=1,
            ),
        ],
        total_steps=2,
        task_success=True,
    )

    high_r = coord.compute_high_reward_from_report(report)
    low_r = coord.compute_low_reward_from_report(report)

    assert high_r["completeness"] == 1.0, "All subgoals succeeded"
    assert high_r["task_success"] == 1.0, "Task success"
    assert low_r["tool_correctness"] >= 0.5, "Tool correctness"

    print(
        f"[PASS] Reward extraction: high_completeness={high_r['completeness']}, low_correctness={low_r['tool_correctness']}"
    )


if __name__ == "__main__":
    test_high_level_policy()
    test_low_level_policy_tool_call()
    test_hierarchical_reward()
    test_policy_coordinator()
    test_tool_dependency_graph()
    test_curriculum_generator()
    test_readiness_evaluator()
    test_training_config()
    test_reward_function_factory()
    test_coordinator_high_low_reward_extraction()
    print("\n" + "=" * 50)
    print("ALL 10 TESTS PASSED!")
    print("=" * 50)
