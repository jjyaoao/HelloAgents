# core/llms.py

import os
from typing import Literal
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek  
from langchain_community.chat_models import ChatTongyi

# 封装不同的LLM
# 使用 Literal 定义支持的 LLM 提供商，以获得更好的代码提示和类型检查。
SUPPORTED_PROVIDERS = Literal["openai", "deepseek", "qwen"]

def get_llm(
    provider: SUPPORTED_PROVIDERS = "deepseek",
    model_version: str = None,
    **kwargs,
) -> BaseChatModel:
    """
    LLM 工厂函数：根据指定的 provider 初始化并返回一个 LangChain 聊天模型实例。
    """
    # 默认参数
    default_kwargs = {"temperature": 0.7, "streaming": True}
    final_kwargs = {**default_kwargs, **kwargs}

    # OpenAI
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("错误：OPENAI_API_KEY 环境变量未设置！")
        model = model_version or "gpt-4o"
        return ChatOpenAI(model=model, **final_kwargs)

    # DeepSeek
    elif provider == "deepseek":
        if not os.getenv("DEEPSEEK_API_KEY"):
            raise ValueError("错误：DEEPSEEK_API_KEY 环境变量未设置！")
        model = model_version or "deepseek-chat"
        return ChatDeepSeek(model=model, **final_kwargs)

    # Qwen (通义千问)
    elif provider == "qwen":
        if not os.getenv("DASHSCOPE_API_KEY"):
            raise ValueError("错误：DASHSCOPE_API_KEY 环境变量未设置！(用于通义千问)")
        model = model_version or "qwen-turbo"
        return ChatTongyi(model_name=model, **final_kwargs)

    # 未知 Provider
    else:
        supported_list = ", ".join(SUPPORTED_PROVIDERS.__args__)
        raise ValueError(
            f"错误：不支持的 LLM provider: '{provider}'。"
            f"当前支持的 providers 包括: {supported_list}"
        )