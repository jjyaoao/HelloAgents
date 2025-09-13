# core/executor.py
from typing import AsyncGenerator
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.pregel import Pregel

# 定义 AgentExecutor 类，作为与编译好的 LangGraph 应用交互的高层接口。
class AgentExecutor:
    """
    一个灵活的 LangGraph Agent 执行器。
    它包装了一个编译好的 LangGraph 应用，简化了同步调用和异步流式处理的接口。
    """
    
    def __init__(self, app: Pregel):
        """
        初始化 AgentExecutor。
        Args:
            app (Pregel): 一个编译好的 LangGraph 应用实例。
        """
        self.app = app

    def invoke(self, query: str) -> str:
        """
        同步调用 Agent，执行流程并返回最终的 AI 报告。
        """
        initial_state = {"messages": [HumanMessage(content=query)]}
        final_state_result = self.app.invoke(initial_state)

        # invoke 的结果可能是包含多个步骤的列表，通常我们关心的是最后一个状态
        final_state = final_state_result if isinstance(final_state_result, dict) else final_state_result[-1]
        
        # 在最终状态的 messages 中查找最后一个 AIMessage
        ai_messages = [msg for msg in final_state.get('messages', []) if isinstance(msg, AIMessage)]
        if ai_messages:
            return ai_messages[-1].content
        return "错误：在最终状态中未找到 AI 信息。"

    async def stream(self, query: str) -> AsyncGenerator[str, None]:
        """
        以异步流的方式执行，并即时回传进度和最终的 LLM token 流。
        """
        initial_state = {"messages": [HumanMessage(content=query)]}
        
        # 使用 astream_events 确保可以捕捉到所有事件
        async for event in self.app.astream_events(initial_state, version="v2"):
            kind = event["event"]
            name = event.get("name")
            
            # 当一个节点开始执行时，打印进度信息
            if kind == "on_node_start":
                yield f"\n> **正在执行节点: {name}...**\n"
            
            # 当有 LLM token 产生时，将其流式传输出来
            # 这种方法是通用的，不依赖于任何特定的节点名称
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if content := chunk.content:
                    yield content