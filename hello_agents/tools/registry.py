"""工具注册中心"""

from typing import Dict, List, Type
from .base import Tool

class ToolRegistry:
    """工具注册中心"""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """注册工具"""
        self._tools[tool.name] = tool
    
    def unregister(self, name: str) -> None:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
    
    def get(self, name: str) -> Tool:
        """获取工具"""
        if name not in self._tools:
            raise ValueError(f"工具 {name} 未注册")
        return self._tools[name]
    
    def list_tools(self) -> List[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())
    
    def get_all_tools(self) -> List[Tool]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()

# 全局工具注册中心
global_tool_registry = ToolRegistry()