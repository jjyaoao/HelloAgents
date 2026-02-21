"""工具过滤器

用于子代理机制，控制不同类型的 Agent 可以访问哪些工具。
"""

from abc import ABC, abstractmethod
from typing import List, Set, Optional


class ToolFilter(ABC):
    """工具过滤器基类
    
    用于在子代理运行时限制可用工具集合。
    """
    
    @abstractmethod
    def filter(self, all_tools: List[str]) -> List[str]:
        """过滤工具列表
        
        Args:
            all_tools: 所有可用工具名称列表
            
        Returns:
            过滤后的工具名称列表
        """
        pass
    
    @abstractmethod
    def is_allowed(self, tool_name: str) -> bool:
        """检查单个工具是否允许
        
        Args:
            tool_name: 工具名称
            
        Returns:
            是否允许使用该工具
        """
        pass


class ReadOnlyFilter(ToolFilter):
    """只读工具过滤器
    
    只允许使用只读工具，适用于：
    - explore（探索代码库）
    - plan（规划任务）
    - summary（归纳信息）
    """
    
    # 只读工具白名单
    READONLY_TOOLS: Set[str] = {
        "Read", "ReadTool",
        "LS", "LSTool",
        "Glob", "GlobTool",
        "Grep", "GrepTool",
        "Skill", "SkillTool",
    }
    
    def __init__(self, additional_allowed: Optional[List[str]] = None):
        """初始化只读过滤器
        
        Args:
            additional_allowed: 额外允许的工具名称列表
        """
        self.allowed_tools = self.READONLY_TOOLS.copy()
        if additional_allowed:
            self.allowed_tools.update(additional_allowed)
    
    def filter(self, all_tools: List[str]) -> List[str]:
        """只保留只读工具"""
        return [tool for tool in all_tools if self.is_allowed(tool)]
    
    def is_allowed(self, tool_name: str) -> bool:
        """检查是否为只读工具"""
        return tool_name in self.allowed_tools


class FullAccessFilter(ToolFilter):
    """完全访问过滤器
    
    允许使用所有工具（除了明确禁止的危险工具），适用于：
    - code（代码实现）
    """
    
    # 危险工具黑名单
    DENIED_TOOLS: Set[str] = {
        "Bash", "BashTool",
        "Terminal", "TerminalTool",
        "Execute", "ExecuteTool",
    }
    
    def __init__(self, additional_denied: Optional[List[str]] = None):
        """初始化完全访问过滤器
        
        Args:
            additional_denied: 额外禁止的工具名称列表
        """
        self.denied_tools = self.DENIED_TOOLS.copy()
        if additional_denied:
            self.denied_tools.update(additional_denied)
    
    def filter(self, all_tools: List[str]) -> List[str]:
        """排除危险工具"""
        return [tool for tool in all_tools if self.is_allowed(tool)]
    
    def is_allowed(self, tool_name: str) -> bool:
        """检查是否允许（不在黑名单中）"""
        return tool_name not in self.denied_tools


class CustomFilter(ToolFilter):
    """自定义工具过滤器
    
    用户可以明确指定允许或禁止的工具列表。
    """
    
    def __init__(
        self,
        allowed: Optional[List[str]] = None,
        denied: Optional[List[str]] = None,
        mode: str = "whitelist"
    ):
        """初始化自定义过滤器
        
        Args:
            allowed: 允许的工具名称列表（白名单模式）
            denied: 禁止的工具名称列表（黑名单模式）
            mode: 过滤模式，"whitelist"（白名单）或 "blacklist"（黑名单）
        """
        self.allowed = set(allowed) if allowed else set()
        self.denied = set(denied) if denied else set()
        self.mode = mode
        
        if mode not in ("whitelist", "blacklist"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'whitelist' or 'blacklist'")
    
    def filter(self, all_tools: List[str]) -> List[str]:
        """根据模式过滤工具"""
        return [tool for tool in all_tools if self.is_allowed(tool)]
    
    def is_allowed(self, tool_name: str) -> bool:
        """检查是否允许"""
        if self.mode == "whitelist":
            return tool_name in self.allowed
        else:  # blacklist
            return tool_name not in self.denied

