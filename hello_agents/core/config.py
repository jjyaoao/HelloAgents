"""配置管理"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class Config:
    """HelloAgents配置类"""
    
    # LLM配置
    default_provider: str = "deepseek"
    default_model: Optional[str] = None
    
    # API密钥
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    deepseek_api_key: Optional[str] = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY"))
    dashscope_api_key: Optional[str] = field(default_factory=lambda: os.getenv("DASHSCOPE_API_KEY"))
    tavily_api_key: Optional[str] = field(default_factory=lambda: os.getenv("TAVILY_API_KEY"))
    
    # 其他配置
    debug: bool = False
    log_level: str = "INFO"
    
    # 自定义配置
    custom_config: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量创建配置"""
        return cls()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return getattr(self, key, self.custom_config.get(key, default))
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            self.custom_config[key] = value