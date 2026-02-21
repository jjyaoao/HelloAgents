"""配置管理"""

import os
from typing import Optional, Dict, Any
from pydantic import BaseModel

class Config(BaseModel):
    """HelloAgents配置类"""

    # LLM配置
    default_model: str = "gpt-3.5-turbo"
    default_provider: str = "openai"
    temperature: float = 0.7
    max_tokens: Optional[int] = None

    # 系统配置
    debug: bool = False
    log_level: str = "INFO"

    # 历史管理配置（向后兼容）
    max_history_length: int = 100

    # 上下文工程配置
    context_window: int = 128000  # 上下文窗口大小（tokens）
    compression_threshold: float = 0.8  # 压缩阈值（0.8 = 80%时触发压缩）
    min_retain_rounds: int = 10  # 压缩时保留的最小完整轮次数
    enable_smart_compression: bool = False  # 是否启用智能摘要（需要额外LLM调用）

    # 智能摘要配置
    summary_llm_provider: str = "deepseek"  # 摘要专用 LLM 提供商
    summary_llm_model: str = "deepseek-chat"  # 摘要专用 LLM 模型
    summary_max_tokens: int = 800  # 摘要最大 Token 数
    summary_temperature: float = 0.3  # 摘要生成温度（更确定性）

    # 工具输出截断配置
    tool_output_max_lines: int = 2000  # 工具输出最大行数
    tool_output_max_bytes: int = 51200  # 工具输出最大字节数（50KB）
    tool_output_dir: str = "tool-output"  # 完整输出保存目录
    tool_output_truncate_direction: str = "head"  # 截断方向：head/tail/head_tail

    # 可观测性配置
    trace_enabled: bool = True  # 是否启用 Trace 记录
    trace_dir: str = "memory/traces"  # Trace 文件保存目录
    trace_sanitize: bool = True  # 是否脱敏敏感信息
    trace_html_include_raw_response: bool = False  # HTML 是否包含原始响应

    # Skills 知识外化配置
    skills_enabled: bool = True  # 是否启用 Skills 系统
    skills_dir: str = "skills"  # Skills 目录路径
    skills_auto_register: bool = True  # 是否自动注册 SkillTool

    # 熔断器配置
    circuit_enabled: bool = True  # 是否启用熔断器
    circuit_failure_threshold: int = 3  # 连续失败多少次后熔断
    circuit_recovery_timeout: int = 300  # 熔断后恢复时间（秒）

    # 会话持久化配置
    session_enabled: bool = True  # 是否启用会话持久化
    session_dir: str = "memory/sessions"  # 会话文件保存目录
    auto_save_enabled: bool = False  # 是否启用自动保存
    auto_save_interval: int = 10  # 自动保存间隔（每N条消息）

    # 子代理机制配置
    subagent_enabled: bool = True  # 是否启用子代理机制
    subagent_max_steps: int = 15  # 子代理默认最大步数
    subagent_use_light_llm: bool = False  # 是否使用轻量模型（默认关闭，避免破坏现有行为）
    subagent_light_llm_provider: str = "deepseek"  # 轻量模型提供商
    subagent_light_llm_model: str = "deepseek-chat"  # 轻量模型名称

    # TodoWrite 进度管理配置
    todowrite_enabled: bool = True  # 是否启用 TodoWrite 工具
    todowrite_persistence_dir: str = "memory/todos"  # 任务列表持久化目录

    # DevLog 开发日志配置
    devlog_enabled: bool = True  # 是否启用 DevLog 工具
    devlog_persistence_dir: str = "memory/devlogs"  # 开发日志持久化目录

    # 异步生命周期配置
    async_enabled: bool = True  # 是否启用异步执行
    max_concurrent_tools: int = 3  # 最大并发工具数
    hook_timeout_seconds: float = 5.0  # 生命周期钩子超时时间（秒）
    llm_async_timeout: int = 120  # LLM 异步调用超时时间（秒）
    tool_async_timeout: int = 30  # 工具异步调用超时时间（秒）

    # 流式输出配置
    stream_enabled: bool = True  # 是否启用流式输出
    stream_buffer_size: int = 100  # 流式缓冲区大小
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
        return self.dict()
