"""RL训练工具函数"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TrainingConfig:
    """训练配置类"""

    # 模型配置
    model_name: str = "Qwen/Qwen3-0.6B"
    model_revision: Optional[str] = None
    
    # 训练配置
    output_dir: str = "./output"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 5e-5
    warmup_steps: int = 100
    logging_steps: int = 10
    save_steps: int = 500
    eval_steps: int = 500
    
    # RL特定配置
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    
    # 硬件配置
    use_fp16: bool = True
    use_bf16: bool = False
    gradient_checkpointing: bool = True
    
    # LoRA配置
    use_lora: bool = True
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    lora_target_modules: list = field(default_factory=lambda: ["q_proj", "v_proj"])
    
    # 监控配置
    use_wandb: bool = False
    wandb_project: Optional[str] = None
    use_tensorboard: bool = True
    
    # 其他配置
    seed: int = 42
    max_length: int = 2048
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }


def setup_training_environment(config: TrainingConfig) -> None:
    """
    设置训练环境
    
    Args:
        config: 训练配置
    """
    # 创建输出目录
    os.makedirs(config.output_dir, exist_ok=True)
    
    # 设置随机种子
    import random
    import numpy as np
    try:
        import torch
        torch.manual_seed(config.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(config.seed)
    except ImportError:
        pass
    
    random.seed(config.seed)
    np.random.seed(config.seed)
    
    # 设置环境变量
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    # 设置wandb配置
    if config.use_wandb:
        if config.wandb_project:
            os.environ["WANDB_PROJECT"] = config.wandb_project
        os.environ["WANDB_LOG_MODEL"] = "false"  # 不上传模型文件

    print(f"✅ 训练环境设置完成")
    print(f"   - 输出目录: {config.output_dir}")
    print(f"   - 随机种子: {config.seed}")
    print(f"   - 模型: {config.model_name}")


def check_trl_installation() -> bool:
    """
    检查TRL是否已安装
    
    Returns:
        是否已安装TRL
    """
    try:
        import trl
        return True
    except ImportError:
        return False


def get_installation_guide() -> str:
    """
    获取TRL安装指南
    
    Returns:
        安装指南文本
    """
    return """
TRL (Transformer Reinforcement Learning) 未安装。

请使用以下命令安装：

方式1：安装HelloAgents的RL功能（推荐）
    pip install hello-agents[rl]

方式2：单独安装TRL
    pip install trl

方式3：从源码安装最新版本
    pip install git+https://github.com/huggingface/trl.git

安装完成后，您可以使用以下功能：
- SFT训练（监督微调）
- GRPO训练（群体相对策略优化）
- PPO训练（近端策略优化）
- DPO训练（直接偏好优化）
- Reward Model训练

更多信息请访问：https://huggingface.co/docs/trl
"""


def format_training_time(seconds: float) -> str:
    """
    格式化训练时间
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时间字符串
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def get_device_info() -> Dict[str, Any]:
    """
    获取设备信息
    
    Returns:
        设备信息字典
    """
    info = {
        "cuda_available": False,
        "cuda_device_count": 0,
        "cuda_device_name": None,
    }
    
    try:
        import torch
        info["cuda_available"] = torch.cuda.is_available()
        if info["cuda_available"]:
            info["cuda_device_count"] = torch.cuda.device_count()
            info["cuda_device_name"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    
    return info


def print_training_summary(
    algorithm: str,
    model_name: str,
    dataset_name: str,
    num_epochs: int,
    output_dir: str
) -> None:
    """
    打印训练摘要
    
    Args:
        algorithm: 算法名称
        model_name: 模型名称
        dataset_name: 数据集名称
        num_epochs: 训练轮数
        output_dir: 输出目录
    """
    device_info = get_device_info()
    
    print("\n" + "="*60)
    print(f"🚀 开始 {algorithm} 训练")
    print("="*60)
    print(f"📦 模型: {model_name}")
    print(f"📊 数据集: {dataset_name}")
    print(f"🔄 训练轮数: {num_epochs}")
    print(f"💾 输出目录: {output_dir}")
    print(f"🖥️  设备: {'GPU' if device_info['cuda_available'] else 'CPU'}")
    if device_info['cuda_available']:
        print(f"   - GPU数量: {device_info['cuda_device_count']}")
        print(f"   - GPU型号: {device_info['cuda_device_name']}")
    print("="*60 + "\n")

