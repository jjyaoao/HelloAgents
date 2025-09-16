"""简单Agent实现"""

from typing import Optional
from langchain_core.messages import HumanMessage, SystemMessage

from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.message import Message

class SimpleAgent(Agent):
    """简单的对话Agent"""
    
    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None
    ):
        super().__init__(name, llm, system_prompt, config)
    
    def run(self, input_text: str, **kwargs) -> str:
        """
        运行简单Agent
        
        Args:
            input_text: 用户输入
            **kwargs: 其他参数
            
        Returns:
            Agent响应
        """
        # 构建消息列表
        messages = []
        
        # 添加系统消息
        if self.system_prompt:
            messages.append(SystemMessage(content=self.system_prompt))
        
        # 添加历史消息
        for msg in self._history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            # 可以添加更多消息类型的处理
        
        # 添加当前用户消息
        messages.append(HumanMessage(content=input_text))
        
        # 调用LLM
        response = self.llm.llm.invoke(messages)
        
        # 保存到历史记录
        self.add_message(Message(input_text, "user"))
        self.add_message(Message(response.content, "assistant"))
        
        return response.content