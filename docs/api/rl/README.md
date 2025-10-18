# HelloAgents RL训练指南

本指南介绍如何使用HelloAgents的强化学习训练功能。

## 📚 详细文档

- **[数据集API](datasets.md)** - 数据集加载和处理
- **[奖励函数API](rewards.md)** - 奖励函数创建和使用
- **[训练器API](trainers.md)** - SFT和GRPO训练器
- **[RLTrainingTool](rl_training_tool.md)** - 统一训练工具(推荐)

## 目录

- [安装](#安装)
- [快速开始](#快速开始)
- [训练算法](#训练算法)
- [使用示例](#使用示例)
- [高级配置](#高级配置)
- [常见问题](#常见问题)

## 安装

### 方式1：安装完整的RL功能（推荐）

```bash
pip install hello-agents[rl]
```

这将安装以下依赖：
- `trl`: Transformer Reinforcement Learning库
- `transformers`: HuggingFace Transformers
- `torch`: PyTorch
- `datasets`: HuggingFace Datasets
- `accelerate`: 分布式训练加速
- `peft`: LoRA等参数高效微调
- `bitsandbytes`: 量化支持
- `wandb`: 训练监控（可选）
- `tensorboard`: TensorBoard支持（可选）

### 方式2：单独安装TRL

```bash
pip install trl
```

### 验证安装

```python
from hello_agents.rl import TRL_AVAILABLE

if TRL_AVAILABLE:
    print("✅ TRL已安装，可以开始训练")
else:
    print("❌ TRL未安装")
```

## 快速开始

### 使用工具接口

```python
from hello_agents.tools import RLTrainingTool

# 创建RL训练工具
rl_tool = RLTrainingTool()

# SFT训练
result = rl_tool.run({
    "algorithm": "sft",
    "model_name": "Qwen/Qwen2-0.5B-Instruct",
    "dataset": "gsm8k",
    "max_samples": 100,
    "num_epochs": 3,
    "output_dir": "./output/sft"
})

print(result)
```

### 加载数据集

```python
# 加载SFT格式数据集
result = rl_tool.run({
    "action": "load_dataset",
    "format": "sft",
    "split": "train",
    "max_samples": 100
})

# 加载RL格式数据集
result = rl_tool.run({
    "action": "load_dataset",
    "format": "rl",
    "split": "train",
    "max_samples": 100,
    "model_name": "Qwen/Qwen3-0.6B"
})
```

### 在Agent中使用

```python
from hello_agents.agents import SimpleAgent
from hello_agents.tools import RLTrainingTool
from hello_agents.core import LLMConfig

# 创建Agent
agent = SimpleAgent(
    name="TrainingAgent",
    llm_config=LLMConfig(model="gpt-4o-mini"),
    tools=[RLTrainingTool()]
)

# 让Agent执行训练任务
response = agent.run(
    "请用SFT算法训练一个Qwen2-0.5B模型，使用gsm8k数据集，训练3轮"
)
```

## 训练算法

### SFT (Supervised Fine-Tuning)

**监督微调**，让模型学会遵循指令和基本的推理格式。

**适用场景**：
- 模型初始对齐
- 学习特定任务格式
- 作为RL训练的基础

**示例**：
```python
rl_tool.run({
    "action": "train",
    "algorithm": "sft",
    "model_name": "Qwen/Qwen3-0.6B",
    "max_samples": 1000,
    "num_epochs": 3,
    "output_dir": "./output/sft",
    "use_lora": True,
    "batch_size": 4
})
```

### GRPO (Group Relative Policy Optimization)

**群体相对策略优化**，通过强化学习优化模型的推理能力。

**优势**：
- 不需要Value Model，更简单
- 内存占用更少
- 训练速度更快
- 性能接近PPO

**适用场景**：
- 优化推理能力
- 提高答案准确率
- Agentic RL训练

**示例**：
```python
rl_tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "Qwen/Qwen3-0.6B",
    "max_samples": 500,
    "num_epochs": 3,
    "output_dir": "./output/grpo",
    "use_lora": True,
    "batch_size": 2
})
```

### PPO (Proximal Policy Optimization)

**近端策略优化**，经典的强化学习算法。

**状态**：🚧 开发中

**说明**：PPO需要额外的Value Model，实现更复杂。建议使用GRPO作为替代。

## 使用示例

### 示例1：完整训练流程

推荐的训练流程：先SFT，再GRPO

```python
from hello_agents.tools import RLTrainingTool

rl_tool = RLTrainingTool()

# 步骤1：SFT训练
print("步骤1：SFT训练...")
sft_result = rl_tool.run({
    "action": "train",
    "algorithm": "sft",
    "model_name": "Qwen/Qwen3-0.6B",
    "max_samples": 1000,
    "num_epochs": 3,
    "output_dir": "./output/sft"
})

# 步骤2：GRPO训练（使用SFT后的模型）
print("步骤2：GRPO训练...")
grpo_result = rl_tool.run({
    "action": "train",
    "algorithm": "grpo",
    "model_name": "./output/sft",  # 使用SFT训练后的模型
    "max_samples": 500,
    "num_epochs": 3,
    "output_dir": "./output/grpo"
})

print("训练完成！最终模型: ./output/grpo")
```

### 示例2：快速测试

使用少量样本快速测试训练流程：

```python
# 快速SFT测试（10个样本，1轮）
rl_tool.run({
    "action": "train",
    "algorithm": "sft",
    "model_name": "Qwen/Qwen3-0.6B",
    "max_samples": 10,
    "num_epochs": 1,
    "output_dir": "./output/test_sft"
})
```

### 示例3：使用LoRA减少显存

```python
# 使用LoRA进行参数高效微调
rl_tool.run({
    "action": "train",
    "algorithm": "sft",
    "model_name": "Qwen/Qwen3-0.6B",
    "use_lora": True,  # 启用LoRA
    "batch_size": 2,   # 小批次
    "output_dir": "./output/sft_lora"
})
```

## 高级配置

### 使用底层API

如果需要更多控制，可以直接使用底层API：

```python
from hello_agents.rl import (
    SFTTrainerWrapper,
    GRPOTrainerWrapper,
    TrainingConfig,
    create_sft_dataset,
    create_rl_dataset,
    create_accuracy_reward
)

# 创建配置
config = TrainingConfig(
    model_name="Qwen/Qwen2-0.5B-Instruct",
    output_dir="./output/custom",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    learning_rate=5e-5,
    use_lora=True,
    lora_r=16,
    lora_alpha=32
)

# SFT训练
dataset = create_sft_dataset(max_samples=1000)
trainer = SFTTrainerWrapper(config=config, dataset=dataset)
trainer.train()
trainer.save_model()

# GRPO训练
rl_dataset = create_rl_dataset(max_samples=500)
reward_fn = create_accuracy_reward()
grpo_trainer = GRPOTrainerWrapper(
    config=config,
    dataset=rl_dataset,
    reward_fn=reward_fn
)
grpo_trainer.train()
grpo_trainer.save_model()
```

### 自定义奖励函数

```python
from hello_agents.rl import MathRewardFunction

# 创建自定义奖励函数
class CustomReward(MathRewardFunction):
    def __call__(self, completions: List[str], **kwargs) -> List[float]:
        ground_truths = kwargs.get("ground_truth", [])
        rewards = []
        for completion, truth in zip(completions, ground_truths):
            # 自定义奖励逻辑
            pred = self.extract_answer(completion)
            if pred and self.compare_answers(pred, truth):
                reward = 1.0
            else:
                reward = 0.0
            rewards.append(reward)
        return rewards

# 使用自定义奖励函数
reward_fn = CustomReward()
```

## 常见问题

### Q1: 训练需要多少显存？

**A**: 取决于模型大小和配置：

- **Qwen3-0.6B + LoRA**: 约4-6GB（单GPU可训练）
- **Qwen3-0.6B 全参数**: 约8-12GB
- **Qwen2-1.5B + LoRA**: 约8-12GB
- **Qwen2-7B + LoRA**: 约16-24GB

**建议**：
- 使用LoRA减少显存占用
- 减小batch_size
- 启用gradient_checkpointing

### Q2: 训练需要多长时间？

**A**: 取决于数据量和硬件：

- **100样本，1轮，单GPU**: 约5-10分钟
- **1000样本，3轮，单GPU**: 约30-60分钟
- **全量GSM8K（7.5K），3轮，单GPU**: 约3-6小时

### Q3: SFT和GRPO有什么区别？

**A**:
- **SFT**: 监督学习，直接学习正确答案的格式
- **GRPO**: 强化学习，通过奖励信号优化推理过程

**推荐流程**: 先SFT学习格式，再GRPO优化能力

### Q4: 为什么推荐GRPO而不是PPO？

**A**: GRPO的优势：
- 不需要Value Model，实现更简单
- 内存占用更少
- 训练速度更快
- 性能接近PPO（90%+）

### Q5: 如何评估训练效果？

**A**: 可以使用评估工具：

```python
from hello_agents.rl import evaluate_rewards, create_accuracy_reward

# 评估模型在测试集上的表现
test_dataset = create_rl_dataset(split="test", max_samples=100)
reward_fn = create_accuracy_reward()

# 生成预测并评估
# ... (需要加载训练后的模型并生成预测)
```

### Q6: 训练失败怎么办？

**A**: 常见问题和解决方案：

1. **显存不足**:
   - 启用LoRA: `use_lora=True`
   - 减小batch_size
   - 使用gradient_checkpointing

2. **TRL未安装**:
   ```bash
   pip install hello-agents[rl]
   ```

3. **数据集下载失败**:
   - 检查网络连接
   - 使用镜像源
   - 手动下载数据集

## 参考资源

- [TRL官方文档](https://huggingface.co/docs/trl)
- [GRPO论文](https://arxiv.org/abs/2402.03300)
- [GSM8K数据集](https://huggingface.co/datasets/openai/gsm8k)
- [Qwen模型](https://huggingface.co/Qwen)

## 下一步

- 查看完整示例: `examples/rl_training_example.py`
- 了解Agentic RL理论: `docs/chapter11/`
- 探索更多训练算法: DPO, KTO, ORPO等

