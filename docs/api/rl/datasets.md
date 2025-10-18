# 数据集API文档

## 概述

`hello_agents.rl.datasets` 模块提供了用于强化学习训练的数据集加载和处理功能。主要支持GSM8K数学推理数据集,并提供SFT和RL两种格式。

## 核心类

### GSM8KDataset

GSM8K数据集的封装类,提供数据加载和格式化功能。

```python
from hello_agents.rl.datasets import GSM8KDataset

dataset = GSM8KDataset(split="train", max_samples=100)
```

#### 参数

- **split** (`str`, 可选): 数据集分割,可选 `"train"` 或 `"test"`, 默认 `"train"`
- **max_samples** (`int`, 可选): 最大样本数,`None` 表示使用全部数据, 默认 `None`

#### 属性

- **dataset**: HuggingFace Dataset对象
- **split**: 当前使用的数据集分割
- **max_samples**: 最大样本数限制

#### 方法

##### `__len__()`

返回数据集大小。

```python
size = len(dataset)
```

##### `__getitem__(index)`

获取指定索引的样本。

**参数**:
- **index** (`int`): 样本索引

**返回**: 包含以下字段的字典:
- `question`: 问题文本
- `answer`: 完整答案(包含推理步骤)
- `ground_truth`: 最终答案(数值)

```python
sample = dataset[0]
print(sample['question'])
print(sample['answer'])
print(sample['ground_truth'])
```

##### `format_for_sft(example)`

将样本格式化为SFT训练格式。

**参数**:
- **example** (`dict`): 原始样本

**返回**: 包含以下字段的字典:
- `prompt`: 格式化的提示词(包含系统提示和问题)
- `completion`: 完整答案
- `text`: prompt + completion的组合

```python
sft_sample = dataset.format_for_sft(dataset[0])
print(sft_sample['prompt'])
print(sft_sample['completion'])
```

##### `format_for_rl(example, model_name)`

将样本格式化为RL训练格式。

**参数**:
- **example** (`dict`): 原始样本
- **model_name** (`str`): 模型名称,用于加载tokenizer

**返回**: 包含以下字段的字典:
- `prompt`: 应用chat template后的文本
- `ground_truth`: 最终答案

```python
rl_sample = dataset.format_for_rl(dataset[0], "Qwen/Qwen3-0.6B")
print(rl_sample['prompt'])
print(rl_sample['ground_truth'])
```

## 便捷函数

### create_sft_dataset

创建SFT格式的数据集。

```python
from hello_agents.rl import create_sft_dataset

dataset = create_sft_dataset(split="train", max_samples=100)
```

#### 参数

- **split** (`str`, 可选): 数据集分割, 默认 `"train"`
- **max_samples** (`int`, 可选): 最大样本数, 默认 `None`

#### 返回

HuggingFace Dataset对象,每个样本包含:
- `prompt`: 格式化的提示词
- `completion`: 完整答案
- `text`: prompt + completion

#### 示例

```python
# 加载训练集
train_dataset = create_sft_dataset(split="train", max_samples=1000)

# 查看样本
sample = train_dataset[0]
print(f"Prompt: {sample['prompt']}")
print(f"Completion: {sample['completion']}")

# 用于SFT训练
from hello_agents.tools import RLTrainingTool

tool = RLTrainingTool()
result = tool.run({
    "action": "train",
    "algorithm": "sft",
    "model_name": "Qwen/Qwen3-0.6B",
    "max_samples": 1000,
    "num_epochs": 3,
    "output_dir": "./output/sft"
})
```

### create_rl_dataset

创建RL格式的数据集。

```python
from hello_agents.rl import create_rl_dataset

dataset = create_rl_dataset(
    split="train",
    max_samples=100,
    model_name="Qwen/Qwen3-0.6B"
)
```

#### 参数

- **split** (`str`, 可选): 数据集分割, 默认 `"train"`
- **max_samples** (`int`, 可选): 最大样本数, 默认 `None`
- **model_name** (`str`, 可选): 模型名称, 默认 `"Qwen/Qwen3-0.6B"`

#### 返回

HuggingFace Dataset对象,每个样本包含:
- `prompt`: 应用chat template后的文本
- `ground_truth`: 最终答案(用于计算奖励)

#### 示例

```python
# 加载RL训练数据集
rl_dataset = create_rl_dataset(
    split="train",
    max_samples=500,
    model_name="Qwen/Qwen3-0.6B"
)

# 查看样本
sample = rl_dataset[0]
print(f"Prompt: {sample['prompt']}")
print(f"Ground Truth: {sample['ground_truth']}")

# 用于GRPO训练
from hello_agents.tools import RLTrainingTool

tool = RLTrainingTool()
result = tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "Qwen/Qwen3-0.6B",
    "max_samples": 500,
    "num_epochs": 3,
    "output_dir": "./output/grpo"
})
```

## 数据集格式

### GSM8K原始格式

```json
{
    "question": "Natalia sold clips to 48 of her friends in April, and then she sold half as many clips in May. How many clips did Natalia sell altogether in April and May?",
    "answer": "Natalia sold 48/2 = <<48/2=24>>24 clips in May.\nNatalia sold 48+24 = <<48+24=72>>72 clips altogether in April and May.\n#### 72"
}
```

### SFT格式

```json
{
    "prompt": "You are a helpful math tutor. Solve the following problem step by step.\n\nQuestion: Natalia sold clips to 48 of her friends in April...",
    "completion": "Natalia sold 48/2 = 24 clips in May.\nNatalia sold 48+24 = 72 clips altogether in April and May.\n#### 72",
    "text": "You are a helpful math tutor...[full text]"
}
```

### RL格式

```json
{
    "prompt": "<|im_start|>system\nYou are a helpful math tutor...<|im_end|>\n<|im_start|>user\nNatalia sold clips to 48 of her friends...<|im_end|>\n<|im_start|>assistant\n",
    "ground_truth": "72"
}
```

## 数据集统计

### GSM8K数据集

- **训练集**: 7,473 个样本
- **测试集**: 1,319 个样本
- **任务类型**: 数学推理
- **难度**: 小学数学水平
- **答案格式**: 包含推理步骤和最终答案

### 样本长度统计

- **问题长度**: 平均 ~100 字符
- **答案长度**: 平均 ~200 字符
- **总长度**: 平均 ~300 字符

## 使用建议

### 训练集大小选择

**快速测试**:
```python
dataset = create_sft_dataset(max_samples=10)  # 1-2分钟
```

**小规模训练**:
```python
dataset = create_sft_dataset(max_samples=100)  # 10-20分钟
```

**中等规模训练**:
```python
dataset = create_sft_dataset(max_samples=1000)  # 1-2小时
```

**完整训练**:
```python
dataset = create_sft_dataset(max_samples=None)  # 5-10小时
```

### 数据集分割

**训练**:
```python
train_dataset = create_sft_dataset(split="train")
```

**评估**:
```python
test_dataset = create_rl_dataset(split="test")
```

## 常见问题

### Q: 如何使用自定义数据集?

A: 可以继承 `GSM8KDataset` 类并重写相关方法:

```python
from hello_agents.rl.datasets import GSM8KDataset

class CustomDataset(GSM8KDataset):
    def __init__(self, data_path, split="train", max_samples=None):
        # 加载自定义数据
        self.dataset = load_custom_data(data_path)
        self.split = split
        self.max_samples = max_samples
```

### Q: 数据集加载很慢怎么办?

A: GSM8K数据集会自动缓存,第一次加载较慢,后续会很快。

### Q: 如何查看数据集样本?

A: 使用RLTrainingTool的load_dataset功能:

```python
from hello_agents.tools import RLTrainingTool

tool = RLTrainingTool()
result = tool.run({
    "action": "load_dataset",
    "format": "sft",
    "split": "train",
    "max_samples": 5
})
```

## 相关文档

- [奖励函数API](rewards.md)
- [训练器API](trainers.md)
- [RLTrainingTool文档](rl_training_tool.md)

