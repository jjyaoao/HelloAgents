"""工具基类"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from langchain_core.tools import tool

class Tool(ABC):
    """工具基类"""
    
    def __init__(self, name: str, description: str):
        """
        初始化工具
        
        Args:
            name: 工具名称
            description: 工具描述
        """
        self.name = name
        self.description = description
    
    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """
        执行工具
        
        Returns:
            工具执行结果
        """
        pass
    
    def to_langchain_tool(self):
        """转换为LangChain工具"""
        @tool(name=self.name, description=self.description)
        def tool_func(*args, **kwargs):
            return self.run(*args, **kwargs)
        return tool_func
    
    def __str__(self) -> str:
        return f"Tool(name={self.name})"
    
    def __repr__(self) -> str:
        return self.__str__()