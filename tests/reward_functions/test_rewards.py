"""
奖励函数测试
"""

import sys
import os

_test_dir = os.path.dirname(os.path.abspath(__file__))
_proj_dir = os.path.dirname(_test_dir)
sys.path.insert(0, _proj_dir)

from reward_functions.fine_grained_reward import (
    FineGrainedRewardFunction,
    RewardConfig as GSM8KConfig,
)
from reward_functions.code_gen_reward import (
    CodeGenRewardFunction,
    CodeGenRewardConfig,
)
from reward_functions.customer_support_reward import (
    CustomerSupportRewardFunction,
    CustomerSupportRewardConfig,
)
from reward_functions.game_ai_reward import GameAIRewardFunction, GameAIRewardConfig


def test_gsm8k_reward():
    """测试 GSM8K 奖励函数"""
    print("=" * 50)
    print("测试 GSM8K 奖励函数")
    print("=" * 50)

    config = GSM8KConfig()
    reward_fn = FineGrainedRewardFunction(config)

    completion1 = "Step 1: 48/2 = 24\nStep 2: 48 + 24 = 72\nFinal Answer: 72"
    r1 = reward_fn.compute_reward(completion1, "72")
    print(f"完全正确: total={r1['total']:.3f}, acc={r1['accuracy']:.3f}")
    assert r1["total"] > 0.5, "完全正确应该得到高奖励"

    completion2 = "Final Answer: 70"
    r2 = reward_fn.compute_reward(completion2, "72")
    print(f"部分正确: total={r2['total']:.3f}, acc={r2['accuracy']:.3f}")
    assert 0 < r2["total"] < 1, "部分正确应该有中间奖励"

    completion3 = "Final Answer: 100"
    r3 = reward_fn.compute_reward(completion3, "72")
    print(f"完全错误: total={r3['total']:.3f}, acc={r3['accuracy']:.3f}")
    assert r3["total"] < 0.5, "完全错误应该得到低奖励"

    completion4 = "I don't know"
    r4 = reward_fn.compute_reward(completion4, "72")
    print(f"无数字: total={r4['total']:.3f}")
    assert r4["total"] == 0.0, "无数字应该得到0奖励"

    print("✓ GSM8K 测试通过\n")


def test_code_gen_reward():
    """测试代码生成奖励函数"""
    print("=" * 50)
    print("测试代码生成奖励函数")
    print("=" * 50)

    config = CodeGenRewardConfig()
    reward_fn = CodeGenRewardFunction(config)

    code1 = '''
def add(a, b):
    """Add two numbers"""
    return a + b
'''
    test1 = {"passed": 5, "total": 5, "compile_error": False}
    perf1 = {"runtime_ms": 50, "memory_kb": 1024}
    r1 = reward_fn.compute_reward(code1, test1, perf1)
    print(
        f"好代码: total={r1['total']:.3f}, acc={r1['accuracy']:.3f}, read={r1['readability']:.3f}"
    )
    assert r1["total"] > 0.7, "好代码应该得到高奖励"

    code2 = "def add(a,b):return a+b"
    test2 = {"passed": 2, "total": 5, "compile_error": False}
    perf2 = {"runtime_ms": 50, "memory_kb": 1024}
    r2 = reward_fn.compute_reward(code2, test2, perf2)
    print(f"差代码: total={r2['total']:.3f}, acc={r2['accuracy']:.3f}")
    assert r2["total"] < 0.65, "差代码应该得到低奖励"

    code3 = "def add(a, b"
    test3 = {"passed": 0, "total": 0, "compile_error": True}
    perf3 = {"runtime_ms": 0, "memory_kb": 0}
    r3 = reward_fn.compute_reward(code3, test3, perf3)
    print(f"编译失败: total={r3['total']:.3f}, acc={r3['accuracy']:.3f}")
    assert r3["accuracy"] == 0.0, "编译失败准确率应为0"
    assert r3["total"] < 0.3, "编译失败总奖励应较低"

    print("✓ 代码生成测试通过\n")


def test_customer_support_reward():
    """测试客服对话奖励函数"""
    print("=" * 50)
    print("测试客服对话奖励函数")
    print("=" * 50)

    config = CustomerSupportRewardConfig()
    reward_fn = CustomerSupportRewardFunction(config)

    conv1 = [
        {"role": "user", "content": "我的订单在哪？"},
        {"role": "assistant", "content": "我帮您查一下"},
        {"role": "assistant", "content": "订单已发货，请问还有其他问题吗？"},
    ]
    feedback1 = {"solved": True, "rating": 5}
    r1 = reward_fn.compute_reward(conv1, feedback1, 1.5)
    print(
        f"好对话: total={r1['total']:.3f}, res={r1['resolution']:.3f}, sat={r1['satisfaction']:.3f}"
    )
    assert r1["total"] > 0.7, "好对话应该得到高奖励"

    conv2 = [
        {"role": "user", "content": "我的账户登录不了"},
        {"role": "assistant", "content": "抱歉，我不清楚"},
    ]
    feedback2 = {"solved": False, "rating": 1}
    r2 = reward_fn.compute_reward(conv2, feedback2, 10.0)
    print(
        f"差对话: total={r2['total']:.3f}, res={r2['resolution']:.3f}, sat={r2['satisfaction']:.3f}"
    )
    assert r2["total"] < 0.5, "差对话应该得到低奖励"

    conv3 = [
        {"role": "user", "content": "怎么退货？"},
        {"role": "assistant", "content": "请问还有其他问题吗？"},
    ]
    r3 = reward_fn.compute_reward(conv3, None, 2.0)
    print(f"无反馈: total={r3['total']:.3f}")
    assert 0 <= r3["total"] <= 1, "应该有中间奖励"

    print("✓ 客服对话测试通过\n")


def test_game_ai_reward():
    """测试游戏 AI 奖励函数"""
    print("=" * 50)
    print("测试游戏 AI 奖励函数")
    print("=" * 50)

    config = GameAIRewardConfig()
    reward_fn = GameAIRewardFunction(config)

    ep1 = {"win": True, "score": 100, "survival_time": 120}
    hist1 = ["attack", "defend", "move", "attack", "defend", "item"]
    opp1 = [{"win": True}, {"win": True}, {"win": False}, {"win": True}]
    r1 = reward_fn.compute_reward(ep1, hist1, opp1)
    print(
        f"赢对局: total={r1['total']:.3f}, win={r1['win']:.3f}, div={r1['diversity']:.3f}"
    )
    assert r1["total"] > 0.6, "好对局应该得到高奖励"

    ep2 = {"win": False, "score": 10, "survival_time": 30}
    hist2 = ["attack", "attack", "attack"]
    opp2 = [{"win": False}, {"win": False}, {"win": True}]
    r2 = reward_fn.compute_reward(ep2, hist2, opp2)
    print(
        f"输对局: total={r2['total']:.3f}, win={r2['win']:.3f}, div={r2['diversity']:.3f}"
    )
    assert r2["total"] < 0.5, "差对局应该得到低奖励"

    print("✓ 游戏 AI 测试通过\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("奖励函数单元测试")
    print("=" * 60 + "\n")

    test_gsm8k_reward()
    test_code_gen_reward()
    test_customer_support_reward()
    test_game_ai_reward()

    print("=" * 60)
    print("✓ 所有测试通过!")
    print("=" * 60)
