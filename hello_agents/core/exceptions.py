"""异常体系"""

class HelloAgentsException(Exception):
    """HelloAgents基础异常类"""
    pass

class LLMException(HelloAgentsException):
    """LLM相关异常"""
    pass

class AgentException(HelloAgentsException):
    """Agent相关异常"""
    pass

class ToolException(HelloAgentsException):
    """工具相关异常"""
    pass

class MemoryException(HelloAgentsException):
    """记忆相关异常"""
    pass

class OrchestrationException(HelloAgentsException):
    """编排相关异常"""
    pass