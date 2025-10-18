# RLTrainingTool API文档

## 概述

`RLTrainingTool` 是HelloAgents框架中用于强化学习训练的统一工具。它提供了简单易用的接口,支持数据集加载、模型训练、奖励函数创建和模型评估等功能。

## 基本用法

```python
from hello_agents.tools import RLTrainingTool

tool = RLTrainingTool()
result = tool.run(config)
```

## 支持的操作

RLTrainingTool支持4种操作,通过 `action` 参数指定:

1. **train**: 训练模型(SFT或GRPO)
2. **load_dataset**: 加载数据集
3. **create_reward**: 创建奖励函数
4. **evaluate**: 评估模型

## 1. 训练模型 (action="train")

### 参数

#### 必需参数

- **action** (`str`): 必须为 `"train"`
- **algorithm** (`str`): 训练算法,可选 `"sft"` 或 `"grpo"`
- **model_name** (`str`): 模型名称或路径
- **output_dir** (`str`): 输出目录

#### 可选参数

- **max_samples** (`int`, 可选): 最大样本数, 默认 `None` (使用全部数据)
- **num_epochs** (`int`, 可选): 训练轮数, 默认 `3`
- **batch_size** (`int`, 可选): 批次大小, 默认 `4` (SFT) 或 `2` (GRPO)
- **learning_rate** (`float`, 可选): 学习率, 默认 `2e-5` (SFT) 或 `1e-5` (GRPO)
- **use_lora** (`bool`, 可选): 是否使用LoRA, 默认 `False`
- **lora_r** (`int`, 可选): LoRA秩, 默认 `16`
- **lora_alpha** (`int`, 可选): LoRA alpha, 默认 `32`
- **lora_dropout** (`float`, 可选): LoRA dropout, 默认 `0.05`

### SFT训练示例

```python
from hello_agents.tools import RLTrainingTool

tool = RLTrainingTool()

# 基础SFT训练
result = tool.run({
    "action": "train",
    "algorithm": "sft",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./output/sft",
    "max_samples": 1000,
    "num_epochs": 3,
    "batch_size": 4,
    "use_lora": True
})

print(result)
```

### GRPO训练示例

```python
# 基础GRPO训练
result = tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./output/grpo",
    "max_samples": 500,
    "num_epochs": 3,
    "batch_size": 2,
    "use_lora": True
})

print(result)
```

### 完整训练流程

```python
# 步骤1: SFT训练
sft_result = tool.run({
    "action": "train",
    "algorithm": "sft",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./output/sft",
    "max_samples": 1000,
    "num_epochs": 3
})

# 步骤2: GRPO训练(使用SFT模型)
grpo_result = tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "./output/sft",  # 使用SFT训练后的模型
    "output_dir": "./output/grpo",
    "max_samples": 500,
    "num_epochs": 3
})
```

### 返回值

训练成功返回JSON字符串:

```json
{
    "status": "success",
    "algorithm": "sft",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./output/sft",
    "num_samples": 1000,
    "num_epochs": 3,
    "use_lora": true
}
```

## 2. 加载数据集 (action="load_dataset")

### 参数

- **action** (`str`): 必须为 `"load_dataset"`
- **format** (`str`, 可选): 数据格式,可选 `"sft"` 或 `"rl"`, 默认 `"sft"`
- **split** (`str`, 可选): 数据集分割,可选 `"train"` 或 `"test"`, 默认 `"train"`
- **max_samples** (`int`, 可选): 最大样本数, 默认 `100`
- **model_name** (`str`, 可选): 模型名称(仅RL格式需要), 默认 `"Qwen/Qwen3-0.6B"`

### 示例

```python
# 加载SFT格式数据集
result = tool.run({
    "action": "load_dataset",
    "format": "sft",
    "split": "train",
    "max_samples": 100
})

# 加载RL格式数据集
result = tool.run({
    "action": "load_dataset",
    "format": "rl",
    "split": "train",
    "max_samples": 100,
    "model_name": "Qwen/Qwen3-0.6B"
})
```

### 返回值

```json
{
    "status": "success",
    "format": "sft",
    "split": "train",
    "dataset_size": 100,
    "sample_keys": ["prompt", "completion", "text"]
}
```

## 3. 创建奖励函数 (action="create_reward")

### 参数

- **action** (`str`): 必须为 `"create_reward"`
- **reward_type** (`str`): 奖励类型,可选:
  - `"accuracy"`: 准确率奖励
  - `"length_penalty"`: 长度惩罚奖励
  - `"step"`: 步骤奖励
- **penalty_weight** (`float`, 可选): 长度惩罚权重, 默认 `0.001`
- **step_bonus** (`float`, 可选): 步骤奖励, 默认 `0.1`

### 示例

```python
# 创建准确率奖励
result = tool.run({
    "action": "create_reward",
    "reward_type": "accuracy"
})

# 创建长度惩罚奖励
result = tool.run({
    "action": "create_reward",
    "reward_type": "length_penalty",
    "penalty_weight": 0.001
})

# 创建步骤奖励
result = tool.run({
    "action": "create_reward",
    "reward_type": "step",
    "step_bonus": 0.1
})
```

### 返回值

```json
{
    "status": "success",
    "reward_type": "accuracy",
    "description": "准确率奖励函数: 正确答案得1分,错误答案得0分"
}
```

## 4. 评估模型 (action="evaluate")

### 参数

- **action** (`str`): 必须为 `"evaluate"`
- **model_path** (`str`): 模型路径
- **max_samples** (`int`, 可选): 测试样本数, 默认 `100`

### 示例

```python
# 评估SFT模型
result = tool.run({
    "action": "evaluate",
    "model_path": "./output/sft",
    "max_samples": 100
})

# 评估GRPO模型
result = tool.run({
    "action": "evaluate",
    "model_path": "./output/grpo",
    "max_samples": 100
})

# 评估基线模型
result = tool.run({
    "action": "evaluate",
    "model_path": "Qwen/Qwen3-0.6B",
    "max_samples": 50
})
```

### 返回值

```json
{
    "status": "success",
    "model_path": "./output/sft",
    "num_samples": 100,
    "accuracy": "45.00%",
    "average_reward": "0.4500",
    "device": "cuda"
}
```

## 完整使用示例

### 端到端训练和评估

```python
from hello_agents.tools import RLTrainingTool
import json

tool = RLTrainingTool()

# 1. 加载数据集
print("1. 加载数据集...")
dataset_result = tool.run({
    "action": "load_dataset",
    "format": "sft",
    "split": "train",
    "max_samples": 1000
})
print(dataset_result)

# 2. SFT训练
print("\n2. SFT训练...")
sft_result = tool.run({
    "action": "train",
    "algorithm": "sft",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./output/sft",
    "max_samples": 1000,
    "num_epochs": 3,
    "use_lora": True
})
print(sft_result)

# 3. GRPO训练
print("\n3. GRPO训练...")
grpo_result = tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "./output/sft",
    "output_dir": "./output/grpo",
    "max_samples": 500,
    "num_epochs": 3,
    "use_lora": True
})
print(grpo_result)

# 4. 评估模型
print("\n4. 评估模型...")
eval_result = tool.run({
    "action": "evaluate",
    "model_path": "./output/grpo",
    "max_samples": 100
})
eval_data = json.loads(eval_result)
print(f"准确率: {eval_data['accuracy']}")
```

### 快速测试

```python
# 快速测试(10个样本)
tool = RLTrainingTool()

# SFT训练
tool.run({
    "action": "train",
    "algorithm": "sft",
    "model_name": "Qwen/Qwen3-0.6B",
    "output_dir": "./output/quick_sft",
    "max_samples": 10,
    "num_epochs": 1
})

# GRPO训练
tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "./output/quick_sft",
    "output_dir": "./output/quick_grpo",
    "max_samples": 10,
    "num_epochs": 1
})

# 评估
result = tool.run({
    "action": "evaluate",
    "model_path": "./output/quick_grpo",
    "max_samples": 10
})
print(result)
```

## 配置建议

### 快速测试配置

```python
{
    "max_samples": 10,
    "num_epochs": 1,
    "batch_size": 2,
    "use_lora": True
}
```

**预计时间**: 1-2分钟

### 小规模训练配置

```python
{
    "max_samples": 100,
    "num_epochs": 3,
    "batch_size": 4,
    "use_lora": True
}
```

**预计时间**: 10-20分钟

### 中等规模训练配置

```python
{
    "max_samples": 1000,
    "num_epochs": 3,
    "batch_size": 4,
    "use_lora": True
}
```

**预计时间**: 1-2小时

### 完整训练配置

```python
{
    "max_samples": None,  # 使用全部数据
    "num_epochs": 5,
    "batch_size": 8,
    "use_lora": True
}
```

**预计时间**: 5-10小时

## 错误处理

### 常见错误

**缺少必需参数**:
```json
{
    "status": "error",
    "message": "缺少必需参数: action"
}
```

**不支持的算法**:
```json
{
    "status": "error",
    "message": "不支持的算法: ppo。支持的算法: sft, grpo"
}
```

**模型加载失败**:
```json
{
    "status": "error",
    "message": "模型加载失败: [错误详情]"
}
```

### 错误处理示例

```python
import json

result = tool.run(config)
result_dict = json.loads(result)

if result_dict["status"] == "error":
    print(f"错误: {result_dict['message']}")
else:
    print("成功!")
```

## 性能优化

### 显存优化

1. **使用LoRA**: `use_lora=True`
2. **减小批次**: `batch_size=2`
3. **减少样本**: `max_samples=100`

### 速度优化

1. **增大批次**: `batch_size=8` (如果显存允许)
2. **减少轮数**: `num_epochs=1` (快速测试)
3. **使用GPU**: 自动检测并使用

## 常见问题

### Q: 如何查看训练进度?

A: 训练过程会打印进度信息到控制台。

### Q: 训练可以中断吗?

A: 可以,使用 Ctrl+C 中断。模型会保存到output_dir。

### Q: 如何使用训练后的模型?

A: 模型保存在output_dir,可以用transformers加载:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("./output/sft")
tokenizer = AutoTokenizer.from_pretrained("./output/sft")
```

### Q: LoRA和全参数训练有什么区别?

A:
- **LoRA**: 只训练少量参数,显存占用小,速度快
- **全参数**: 训练所有参数,效果可能更好,但需要更多显存

## 相关文档

- [数据集API](datasets.md)
- [奖励函数API](rewards.md)
- [训练器API](trainers.md)
- [快速开始教程](../../tutorials/quickstart.md)

