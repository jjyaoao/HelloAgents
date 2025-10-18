# 训练器API文档

## 概述

`hello_agents.rl.trainers` 模块提供了SFT和GRPO训练器的封装,简化了模型训练流程。基于HuggingFace TRL库实现。

## 核心类

### SFTTrainerWrapper

SFT (Supervised Fine-Tuning) 训练器的封装类。

```python
from hello_agents.rl.trainers import SFTTrainerWrapper

trainer = SFTTrainerWrapper(
    model_name="Qwen/Qwen3-0.6B",
    dataset=dataset,
    output_dir="./output/sft",
    num_epochs=3,
    batch_size=4,
    learning_rate=2e-5,
    use_lora=True
)

trainer.train()
```

#### 参数

- **model_name** (`str`): 模型名称或路径
- **dataset**: 训练数据集(HuggingFace Dataset)
- **output_dir** (`str`): 输出目录
- **num_epochs** (`int`, 可选): 训练轮数, 默认 `3`
- **batch_size** (`int`, 可选): 批次大小, 默认 `4`
- **learning_rate** (`float`, 可选): 学习率, 默认 `2e-5`
- **use_lora** (`bool`, 可选): 是否使用LoRA, 默认 `False`
- **lora_config** (`dict`, 可选): LoRA配置, 默认 `None`

#### 方法

##### `train()`

开始训练。

**返回**: 训练结果字典

```python
result = trainer.train()
print(f"训练完成,模型保存在: {result['output_dir']}")
```

##### `save_model(path)`

保存模型到指定路径。

**参数**:
- **path** (`str`): 保存路径

```python
trainer.save_model("./my_model")
```

#### 示例

**基础SFT训练**:
```python
from hello_agents.rl import create_sft_dataset, SFTTrainerWrapper

# 加载数据集
dataset = create_sft_dataset(split="train", max_samples=1000)

# 创建训练器
trainer = SFTTrainerWrapper(
    model_name="Qwen/Qwen3-0.6B",
    dataset=dataset,
    output_dir="./output/sft",
    num_epochs=3,
    batch_size=4
)

# 训练
trainer.train()
```

**使用LoRA训练**:
```python
from hello_agents.rl import create_lora_config

# 创建LoRA配置
lora_config = create_lora_config(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05
)

# 创建训练器
trainer = SFTTrainerWrapper(
    model_name="Qwen/Qwen3-0.6B",
    dataset=dataset,
    output_dir="./output/sft_lora",
    use_lora=True,
    lora_config=lora_config
)

trainer.train()
```

### GRPOTrainerWrapper

GRPO (Group Relative Policy Optimization) 训练器的封装类。

```python
from hello_agents.rl.trainers import GRPOTrainerWrapper

trainer = GRPOTrainerWrapper(
    model_name="Qwen/Qwen3-0.6B",
    dataset=dataset,
    reward_fn=reward_fn,
    output_dir="./output/grpo",
    num_epochs=3,
    batch_size=2,
    learning_rate=1e-5,
    use_lora=True
)

trainer.train()
```

#### 参数

- **model_name** (`str`): 模型名称或路径
- **dataset**: 训练数据集(HuggingFace Dataset)
- **reward_fn**: 奖励函数
- **output_dir** (`str`): 输出目录
- **num_epochs** (`int`, 可选): 训练轮数, 默认 `3`
- **batch_size** (`int`, 可选): 批次大小, 默认 `2`
- **learning_rate** (`float`, 可选): 学习率, 默认 `1e-5`
- **use_lora** (`bool`, 可选): 是否使用LoRA, 默认 `False`
- **lora_config** (`dict`, 可选): LoRA配置, 默认 `None`

#### 方法

##### `train()`

开始训练。

**返回**: 训练结果字典

```python
result = trainer.train()
print(f"训练完成,模型保存在: {result['output_dir']}")
```

##### `save_model(path)`

保存模型到指定路径。

**参数**:
- **path** (`str`): 保存路径

```python
trainer.save_model("./my_model")
```

#### 示例

**基础GRPO训练**:
```python
from hello_agents.rl import (
    create_rl_dataset,
    create_accuracy_reward,
    GRPOTrainerWrapper
)

# 加载数据集
dataset = create_rl_dataset(
    split="train",
    max_samples=500,
    model_name="Qwen/Qwen3-0.6B"
)

# 创建奖励函数
reward_fn = create_accuracy_reward()

# 创建训练器
trainer = GRPOTrainerWrapper(
    model_name="Qwen/Qwen3-0.6B",
    dataset=dataset,
    reward_fn=reward_fn,
    output_dir="./output/grpo",
    num_epochs=3,
    batch_size=2
)

# 训练
trainer.train()
```

**使用SFT模型初始化**:
```python
# 先SFT训练
sft_trainer = SFTTrainerWrapper(
    model_name="Qwen/Qwen3-0.6B",
    dataset=sft_dataset,
    output_dir="./output/sft"
)
sft_trainer.train()

# 再GRPO训练
grpo_trainer = GRPOTrainerWrapper(
    model_name="./output/sft",  # 使用SFT模型
    dataset=rl_dataset,
    reward_fn=reward_fn,
    output_dir="./output/grpo"
)
grpo_trainer.train()
```

## 训练配置

### 通用配置

#### 学习率

**SFT**:
- 小模型(0.5B-1B): `2e-5`
- 中等模型(1B-7B): `1e-5`
- 大模型(7B+): `5e-6`

**GRPO**:
- 通常使用SFT的一半: `1e-5` (小模型)

#### 批次大小

**SFT**:
- 全参数训练: `4-8`
- LoRA训练: `8-16`

**GRPO**:
- 通常更小: `2-4`
- 需要生成样本,显存占用更大

#### 训练轮数

**SFT**:
- 快速测试: `1`
- 正常训练: `3-5`
- 充分训练: `10+`

**GRPO**:
- 快速测试: `1`
- 正常训练: `3-5`
- 过多可能过拟合

### LoRA配置

```python
from hello_agents.rl import create_lora_config

lora_config = create_lora_config(
    r=16,              # LoRA秩
    lora_alpha=32,     # LoRA alpha
    lora_dropout=0.05, # Dropout率
    target_modules=["q_proj", "v_proj"]  # 目标模块
)
```

#### 参数说明

- **r**: LoRA秩,越大模型容量越大,显存占用越多
  - 小任务: `8`
  - 中等任务: `16`
  - 复杂任务: `32-64`

- **lora_alpha**: 缩放因子,通常设为 `r * 2`

- **lora_dropout**: Dropout率,防止过拟合
  - 小数据集: `0.1`
  - 大数据集: `0.05`

- **target_modules**: 应用LoRA的模块
  - 最小: `["q_proj", "v_proj"]`
  - 推荐: `["q_proj", "k_proj", "v_proj", "o_proj"]`
  - 完整: 添加 `["gate_proj", "up_proj", "down_proj"]`

## 训练流程

### SFT训练流程

```
1. 加载预训练模型
   ↓
2. 加载SFT数据集
   ↓
3. 配置训练参数
   ↓
4. 开始训练
   ↓
5. 保存模型
```

### GRPO训练流程

```
1. 加载模型(通常是SFT后的模型)
   ↓
2. 加载RL数据集
   ↓
3. 配置奖励函数
   ↓
4. 开始训练
   ├─ 生成样本
   ├─ 计算奖励
   ├─ 更新策略
   └─ 重复
   ↓
5. 保存模型
```

## 完整训练示例

### 使用RLTrainingTool

**推荐方式**:

```python
from hello_agents.tools import RLTrainingTool

tool = RLTrainingTool()

# SFT训练
sft_result = tool.run({
    "action": "train",
    "algorithm": "sft",
    "model_name": "Qwen/Qwen3-0.6B",
    "max_samples": 1000,
    "num_epochs": 3,
    "output_dir": "./output/sft",
    "use_lora": True,
    "batch_size": 4
})

# GRPO训练
grpo_result = tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "./output/sft",
    "max_samples": 500,
    "num_epochs": 3,
    "output_dir": "./output/grpo",
    "use_lora": True,
    "batch_size": 2
})
```

### 直接使用训练器

**高级用法**:

```python
from hello_agents.rl import (
    create_sft_dataset,
    create_rl_dataset,
    create_accuracy_reward,
    create_lora_config,
    SFTTrainerWrapper,
    GRPOTrainerWrapper
)

# 准备数据
sft_dataset = create_sft_dataset(split="train", max_samples=1000)
rl_dataset = create_rl_dataset(split="train", max_samples=500, model_name="Qwen/Qwen3-0.6B")

# 准备奖励函数
reward_fn = create_accuracy_reward()

# 准备LoRA配置
lora_config = create_lora_config(r=16, lora_alpha=32)

# SFT训练
sft_trainer = SFTTrainerWrapper(
    model_name="Qwen/Qwen3-0.6B",
    dataset=sft_dataset,
    output_dir="./output/sft",
    num_epochs=3,
    batch_size=4,
    use_lora=True,
    lora_config=lora_config
)
sft_trainer.train()

# GRPO训练
grpo_trainer = GRPOTrainerWrapper(
    model_name="./output/sft",
    dataset=rl_dataset,
    reward_fn=reward_fn,
    output_dir="./output/grpo",
    num_epochs=3,
    batch_size=2,
    use_lora=True,
    lora_config=lora_config
)
grpo_trainer.train()
```

## 性能优化

### 显存优化

**使用LoRA**:
```python
use_lora=True  # 减少显存占用约50-70%
```

**减小批次大小**:
```python
batch_size=2  # GRPO推荐使用较小批次
```

**使用梯度累积**:
```python
gradient_accumulation_steps=4  # 模拟更大批次
```

### 速度优化

**使用混合精度**:
```python
fp16=True  # 自动启用
```

**增大批次大小**:
```python
batch_size=8  # 如果显存允许
```

## 常见问题

### Q: SFT和GRPO有什么区别?

A:
- **SFT**: 监督学习,直接学习(问题,答案)对
- **GRPO**: 强化学习,通过奖励信号优化策略

### Q: 什么时候使用LoRA?

A:
- 显存不足时
- 需要快速实验时
- 多任务微调时

### Q: 训练需要多长时间?

A: 取决于数据集大小和硬件:
- 10样本: 1-2分钟
- 100样本: 10-20分钟
- 1000样本: 1-2小时
- 全数据集: 5-10小时

### Q: 如何选择学习率?

A: 建议从默认值开始:
- SFT: `2e-5`
- GRPO: `1e-5`
- 如果loss不下降,尝试增大学习率
- 如果loss震荡,尝试减小学习率

## 相关文档

- [数据集API](datasets.md)
- [奖励函数API](rewards.md)
- [RLTrainingTool文档](rl_training_tool.md)

