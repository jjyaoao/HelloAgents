from dotenv import load_dotenv
load_dotenv()

import asyncio
from typing import Dict, Any

from langchain_core.messages import BaseMessage
from langgraph.graph import END
from langgraph.prebuilt import ToolNode

# 从 core 脚手架导入通用组件
from core.llms import get_llm
from core.state import BaseAgentState
from core.tool import agent_tools 
from core.graph import build_agent_app
from core.executor import AgentExecutor

# ==============================================================================
# 1. 定义 Agent 状态 (State)
#    对于这个通用的会话式 Agent，我们不需要任何额外的状态字段，因此，直接使用脚手架中提供的 BaseAgentState 即可。
# ==============================================================================
AgentState = BaseAgentState

# ==============================================================================
# 2. 定义 Agent 需要的所有节点 (Nodes)
# ==============================================================================

# --- 节点函数 ---

def agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Agent 决策节点：
    - 接收用户输入和历史消息。
    - 调用 LLM 进行思考和决策。
    - LLM 的响应可能是直接回答，也可能是调用工具的请求。
    """
    print("\n--- 🤔 节点: Agent (决策中) ---")
    
    # 1. 将完整的工具箱绑定到模型上，让模型知道它有哪些工具可用
    llm_with_tools = get_llm(provider="deepseek").bind_tools(agent_tools)
    
    # 2. 调用模型进行决策
    response = llm_with_tools.invoke(state["messages"])
    
    # 3. 返回模型的响应，更新到状态中
    return {"messages": [response]}


# --- 决策函数 ---

def should_continue(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        # 提取工具名称
        tool_names = ", ".join([call['name'] for call in last_message.tool_calls])
        # 打印带换行符和工具名的新日志
        print(f"\n💡 决策: 需要调用工具 -> [{tool_names}]")
        return "tools"
    else:
        # 这里也加上换行符，保持格式统一
        print("\n✅ 决策: 无需工具，直接输出。")
        return END

# ==============================================================================
# 3. 组装并运行 Agent
# ==============================================================================

if __name__ == "__main__":
    # a. 定义节点字典
    #    - agent: 我们的决策节点
    #    - tools: LangGraph 提供的预构建工具节点，它会自动执行 agent 请求的工具
    nodes = {
        "agent": agent_node,
        "tools": ToolNode(agent_tools)
    }

    # b. 使用脚手架构建 Agent 应用 (循环图)
    agent_graph = build_agent_app(
        state_schema=AgentState,
        nodes=nodes,
        entry_point="agent", # 入口是 agent 决策节点
        # Conditional Edges (条件边)
        # 条件边
        conditional_edges={
            "agent": {
                "path": should_continue,
                "path_map": {
                    "tools": "tools",  # 当返回 "tools" 时，转到 tools 节点
                    END: END           # 当返回 END 时，结束流程
                }
            }
        },
        # Normal Edges (普通边)
        edges=[
            ("tools", "agent"), # 工具执行完后，将结果返回给 agent 节点再次决策
        ]
    )

    # c. 初始化执行器
    agent = AgentExecutor(app=agent_graph)

    # d. 以交互式聊天方式运行 Agent
    async def chat():
        print("--- 🤖 通用会话助理已启动 ---")
        print("你好！我是你的通用助理。你可以问我问题，需要时我会使用工具。输入 'exit' 退出。")
        
        while True:
            query = input("\n👤 你: ")
            if query.lower() == "exit":
                print("👋 再见!")
                break
            
            print("🤖 AI助理: ", end="", flush=True)
            async for chunk in agent.stream(query):
                print(chunk, end="", flush=True)
            print()

    asyncio.run(chat())
