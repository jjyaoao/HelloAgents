# 奖励函数API文档

## 概述

`hello_agents.rl.rewards` 模块提供了用于强化学习训练的奖励函数。奖励函数用于评估模型生成的答案质量,是GRPO等RL算法的核心组件。

## 核心类

### MathRewardFunction

数学任务奖励函数的基类,提供答案提取和比较功能。

```python
from hello_agents.rl.rewards import MathRewardFunction

class CustomReward(MathRewardFunction):
    def __call__(self, completions: List[str], **kwargs) -> List[float]:
        # 实现自定义奖励逻辑
        pass
```

#### 方法

##### `extract_answer(text)`

从文本中提取最终答案。

**参数**:
- **text** (`str`): 包含答案的文本

**返回**: 提取的答案字符串,如果未找到则返回 `None`

**支持的格式**:
- `#### 42` (GSM8K标准格式)
- `答案是 42`
- `最终答案: 42`
- `= 42`

```python
reward_fn = MathRewardFunction()
answer = reward_fn.extract_answer("计算结果是 #### 42")
print(answer)  # "42"
```

##### `compare_answers(pred, truth)`

比较预测答案和真实答案是否相等。

**参数**:
- **pred** (`str`): 预测答案
- **truth** (`str`): 真实答案

**返回**: `True` 如果答案相等,否则 `False`

**比较规则**:
- 去除空格
- 转换为小写
- 数值比较(支持整数和浮点数)

```python
reward_fn = MathRewardFunction()
is_correct = reward_fn.compare_answers("42", "42.0")
print(is_correct)  # True
```

##### `__call__(completions, **kwargs)`

计算奖励值。子类需要实现此方法。

**参数**:
- **completions** (`List[str]`): 模型生成的答案列表
- **kwargs**: 其他参数,通常包含 `ground_truth`

**返回**: 奖励值列表 (`List[float]`)

## 内置奖励函数

### AccuracyReward

基于准确率的奖励函数,正确答案得1分,错误答案得0分。

```python
from hello_agents.rl.rewards import AccuracyReward

reward_fn = AccuracyReward()
rewards = reward_fn(
    completions=["答案是 42", "答案是 43"],
    ground_truth=["42", "42"]
)
print(rewards)  # [1.0, 0.0]
```

#### 特点

- ✅ 简单直观
- ✅ 适合分类任务
- ✅ 奖励值为0或1
- ❌ 无法区分部分正确

### LengthPenaltyReward

带长度惩罚的奖励函数,鼓励生成简洁的答案。

```python
from hello_agents.rl.rewards import LengthPenaltyReward, AccuracyReward

base_reward = AccuracyReward()
reward_fn = LengthPenaltyReward(
    base_reward_fn=base_reward,
    penalty_weight=0.001
)

rewards = reward_fn(
    completions=["答案是 42", "经过复杂计算,最终答案是 42"],
    ground_truth=["42", "42"]
)
# 第二个答案虽然正确,但因为更长所以奖励更低
```

#### 参数

- **base_reward_fn**: 基础奖励函数
- **penalty_weight** (`float`, 可选): 惩罚权重, 默认 `0.001`

#### 奖励计算

```
reward = base_reward - penalty_weight * len(completion)
```

#### 特点

- ✅ 鼓励简洁答案
- ✅ 避免冗长输出
- ⚠️ 需要调整penalty_weight

### StepReward

带步骤奖励的奖励函数,鼓励生成详细的推理步骤。

```python
from hello_agents.rl.rewards import StepReward, AccuracyReward

base_reward = AccuracyReward()
reward_fn = StepReward(
    base_reward_fn=base_reward,
    step_bonus=0.1
)

rewards = reward_fn(
    completions=[
        "42",  # 无步骤
        "第一步: 48/2=24\n第二步: 48+24=72\n答案: 72"  # 有步骤
    ],
    ground_truth=["42", "72"]
)
# 第二个答案因为有推理步骤所以奖励更高
```

#### 参数

- **base_reward_fn**: 基础奖励函数
- **step_bonus** (`float`, 可选): 每个步骤的奖励, 默认 `0.1`

#### 奖励计算

```
num_steps = count_steps(completion)
reward = base_reward + step_bonus * num_steps
```

#### 步骤识别

识别以下模式为推理步骤:
- `第一步:`, `第二步:`, ...
- `Step 1:`, `Step 2:`, ...
- `1.`, `2.`, `3.`, ...

#### 特点

- ✅ 鼓励详细推理
- ✅ 提高可解释性
- ⚠️ 可能导致冗长输出

## 便捷函数

### create_accuracy_reward

创建准确率奖励函数。

```python
from hello_agents.rl import create_accuracy_reward

reward_fn = create_accuracy_reward()
```

#### 返回

`AccuracyReward` 实例

#### 示例

```python
reward_fn = create_accuracy_reward()
rewards = reward_fn(
    completions=["42", "43", "42"],
    ground_truth=["42", "42", "42"]
)
print(rewards)  # [1.0, 0.0, 1.0]
```

### create_length_penalty_reward

创建带长度惩罚的奖励函数。

```python
from hello_agents.rl import create_length_penalty_reward, create_accuracy_reward

base_fn = create_accuracy_reward()
reward_fn = create_length_penalty_reward(
    base_reward_fn=base_fn,
    penalty_weight=0.001
)
```

#### 参数

- **base_reward_fn**: 基础奖励函数
- **penalty_weight** (`float`, 可选): 惩罚权重, 默认 `0.001`

#### 返回

`LengthPenaltyReward` 实例

#### 示例

```python
base_fn = create_accuracy_reward()
reward_fn = create_length_penalty_reward(base_fn, penalty_weight=0.001)

rewards = reward_fn(
    completions=["42", "答案是42"],
    ground_truth=["42", "42"]
)
# 第一个答案更短,奖励更高
```

### create_step_reward

创建带步骤奖励的奖励函数。

```python
from hello_agents.rl import create_step_reward, create_accuracy_reward

base_fn = create_accuracy_reward()
reward_fn = create_step_reward(
    base_reward_fn=base_fn,
    step_bonus=0.1
)
```

#### 参数

- **base_reward_fn**: 基础奖励函数
- **step_bonus** (`float`, 可选): 每个步骤的奖励, 默认 `0.1`

#### 返回

`StepReward` 实例

#### 示例

```python
base_fn = create_accuracy_reward()
reward_fn = create_step_reward(base_fn, step_bonus=0.1)

rewards = reward_fn(
    completions=[
        "42",
        "第一步: 计算\n第二步: 验证\n答案: 42"
    ],
    ground_truth=["42", "42"]
)
# 第二个答案有步骤,奖励更高
```

### evaluate_rewards

评估奖励函数的性能。

```python
from hello_agents.rl import evaluate_rewards

stats = evaluate_rewards(
    reward_fn=reward_fn,
    completions=completions,
    ground_truths=ground_truths
)
```

#### 参数

- **reward_fn**: 奖励函数
- **completions** (`List[str]`): 生成的答案列表
- **ground_truths** (`List[str]`): 真实答案列表

#### 返回

包含以下统计信息的字典:
- `mean`: 平均奖励
- `std`: 标准差
- `min`: 最小奖励
- `max`: 最大奖励
- `accuracy`: 准确率(奖励>0的比例)

#### 示例

```python
reward_fn = create_accuracy_reward()
stats = evaluate_rewards(
    reward_fn=reward_fn,
    completions=["42", "43", "42"],
    ground_truths=["42", "42", "42"]
)
print(stats)
# {
#     'mean': 0.667,
#     'std': 0.471,
#     'min': 0.0,
#     'max': 1.0,
#     'accuracy': 0.667
# }
```

## 自定义奖励函数

### 基本模板

```python
from hello_agents.rl.rewards import MathRewardFunction
from typing import List

class CustomReward(MathRewardFunction):
    def __call__(self, completions: List[str], **kwargs) -> List[float]:
        ground_truths = kwargs.get("ground_truth", [])
        rewards = []
        
        for completion, truth in zip(completions, ground_truths):
            # 提取答案
            pred = self.extract_answer(completion)
            
            # 计算奖励
            if pred and self.compare_answers(pred, truth):
                reward = 1.0
            else:
                reward = 0.0
            
            rewards.append(reward)
        
        return rewards
```

### 高级示例

```python
class DetailedReward(MathRewardFunction):
    """综合考虑准确率、长度和步骤的奖励函数"""
    
    def __init__(self, length_weight=0.001, step_bonus=0.1):
        super().__init__()
        self.length_weight = length_weight
        self.step_bonus = step_bonus
    
    def __call__(self, completions: List[str], **kwargs) -> List[float]:
        ground_truths = kwargs.get("ground_truth", [])
        rewards = []
        
        for completion, truth in zip(completions, ground_truths):
            # 基础准确率奖励
            pred = self.extract_answer(completion)
            if pred and self.compare_answers(pred, truth):
                reward = 1.0
            else:
                reward = 0.0
            
            # 长度惩罚
            reward -= self.length_weight * len(completion)
            
            # 步骤奖励
            num_steps = self._count_steps(completion)
            reward += self.step_bonus * num_steps
            
            rewards.append(reward)
        
        return rewards
    
    def _count_steps(self, text: str) -> int:
        """计算推理步骤数"""
        import re
        patterns = [
            r'第[一二三四五六七八九十]+步',
            r'Step \d+',
            r'^\d+\.',
        ]
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text, re.MULTILINE))
        return count
```

## 使用建议

### 选择合适的奖励函数

**准确率任务**:
```python
reward_fn = create_accuracy_reward()
```

**需要简洁答案**:
```python
base_fn = create_accuracy_reward()
reward_fn = create_length_penalty_reward(base_fn, penalty_weight=0.001)
```

**需要详细推理**:
```python
base_fn = create_accuracy_reward()
reward_fn = create_step_reward(base_fn, step_bonus=0.1)
```

### 调整奖励参数

**长度惩罚权重**:
- 太小(0.0001): 几乎无效果
- 适中(0.001): 平衡准确率和长度
- 太大(0.01): 过度惩罚,可能影响准确率

**步骤奖励**:
- 太小(0.01): 激励不足
- 适中(0.1): 鼓励详细推理
- 太大(1.0): 可能导致过度冗长

## 常见问题

### Q: 奖励函数的签名为什么是 `**kwargs`?

A: 为了兼容TRL库的接口,奖励函数需要接受可变参数。`ground_truth` 通过kwargs传递。

### Q: 如何调试奖励函数?

A: 使用 `evaluate_rewards` 函数查看统计信息:

```python
stats = evaluate_rewards(reward_fn, completions, ground_truths)
print(f"平均奖励: {stats['mean']}")
print(f"准确率: {stats['accuracy']}")
```

### Q: 奖励值的范围是多少?

A: 取决于奖励函数:
- `AccuracyReward`: [0, 1]
- `LengthPenaltyReward`: 可能为负数
- `StepReward`: [0, 1 + step_bonus * max_steps]

## 相关文档

- [数据集API](datasets.md)
- [训练器API](trainers.md)
- [RLTrainingTool文档](rl_training_tool.md)

