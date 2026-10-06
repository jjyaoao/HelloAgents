"""配置管理"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class Config(BaseModel):
    """HelloAgents配置类"""

    model_config = ConfigDict(allow_inf_nan=False)

    # LLM配置
    default_model: Optional[str] = None
    default_provider: str = "openai"
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    # 系统配置
    debug: bool = False
    log_level: str = "INFO"

    # 上下文工程配置
    context_window: int = Field(default=128000, gt=0)
    compression_threshold: float = Field(default=0.8, gt=0, le=1)
    min_retain_rounds: int = Field(default=10, gt=0)
    enable_smart_compression: bool = False  # 是否启用智能摘要（需要额外LLM调用）

    # 智能摘要配置
    summary_llm_provider: Optional[str] = None  # 摘要专用 LLM 提供商
    summary_llm_model: Optional[str] = None  # 摘要专用 LLM 模型
    summary_max_tokens: int = Field(default=800, gt=0)  # 摘要最大 Token 数
    summary_temperature: float = 0.3  # 摘要生成温度（更确定性）

    # 工具输出截断配置
    tool_output_max_lines: int = Field(default=2000, gt=0)
    tool_output_max_bytes: int = Field(default=51200, gt=0)
    tool_output_dir: str = "tool-output"  # 完整输出保存目录
    tool_output_truncate_direction: str = "head"  # 截断方向：head/tail/head_tail

    # 可观测性配置
    trace_enabled: bool = False  # 是否启用 Trace 记录
    trace_dir: str = "memory/traces"  # Trace 文件保存目录
    trace_sanitize: bool = True  # 是否脱敏敏感信息
    trace_html_include_raw_response: bool = False  # HTML 是否包含原始响应

    # Skills 知识外化配置
    skills_enabled: bool = False  # 是否启用 Skills 系统
    skills_dir: str = "skills"  # Skills 目录路径
    skills_auto_register: bool = True  # 是否自动注册 SkillTool

    # 熔断器配置
    circuit_enabled: bool = True  # 是否启用熔断器
    circuit_failure_threshold: int = Field(default=3, gt=0)  # 连续失败多少次后熔断
    circuit_recovery_timeout: int = Field(default=300, gt=0)  # 熔断后恢复时间（秒）

    # 会话持久化配置
    session_enabled: bool = False  # 是否启用会话持久化
    session_dir: str = "memory/sessions"  # 会话文件保存目录
    auto_save_enabled: bool = False  # 是否启用自动保存
    auto_save_interval: int = Field(default=10, gt=0)

    # 子代理机制配置
    subagent_enabled: bool = False  # 是否启用子代理机制
    subagent_max_steps: int = Field(default=15, gt=0)  # 子代理默认最大步数
    subagent_use_light_llm: bool = False  # 是否使用轻量模型（默认关闭，沿用主模型）
    subagent_light_llm_provider: Optional[str] = None  # 轻量模型提供商
    subagent_light_llm_model: Optional[str] = None  # 轻量模型名称

    # TodoWrite 进度管理配置
    todowrite_enabled: bool = False  # 是否启用 TodoWrite 工具
    todowrite_persistence_dir: str = "memory/todos"  # 任务列表持久化目录

    # DevLog 开发日志配置
    devlog_enabled: bool = False  # 是否启用 DevLog 工具
    devlog_persistence_dir: str = "memory/devlogs"  # 开发日志持久化目录

    # 异步生命周期配置
    max_concurrent_tools: int = Field(default=3, gt=0)
    hook_timeout_seconds: float = Field(default=5.0, gt=0)
    llm_async_timeout: float = Field(default=120, gt=0)
    tool_async_timeout: float = Field(default=30, gt=0)

    # 流式输出配置
    stream_include_thinking: bool = True  # 是否包含思考过程
    stream_include_tool_calls: bool = True  # 是否包含工具调用

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量创建配置"""
        return cls(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS")) if os.getenv("MAX_TOKENS") else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
