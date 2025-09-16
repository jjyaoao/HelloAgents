"""Agent基类"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from .llm import HelloAgentsLLM
from .message import Message
from .config import Config
from .exceptions import AgentException

class Agent(ABC):
    """Agent基类"""
    
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None
    ):
        """
        初始化Agent
        
        Args:
            name: Agent名称
            llm: LLM实例
            system_prompt: 系统提示词
            config: 配置实例
        """
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt or f"你是一个名为{name}的AI助手。"
        self.config = config or Config()
        
        # 内部状态
        self._history: List[Message] = []
        self._metadata: Dict[str, Any] = {}
    
    @abstractmethod
    def run(self, input_text: str, **kwargs) -> str:
        """
        运行Agent
        
        Args:
            input_text: 输入文本
            **kwargs: 其他参数
            
        Returns:
            Agent的响应
        """
        pass
    
    def add_message(self, message: Message) -> None:
        """添加消息到历史记录"""
        self._history.append(message)
    
    def get_history(self) -> List[Message]:
        """获取历史记录"""
        return self._history.copy()
    
    def clear_history(self) -> None:
        """清空历史记录"""
        self._history.clear()
    
    def set_metadata(self, key: str, value: Any) -> None:
        """设置元数据"""
        self._metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self._metadata.get(key, default)
    
    def __str__(self) -> str:
        return f"Agent(name={self.name}, provider={self.llm.provider})"
    
    def __repr__(self) -> str:
        return self.__str__()