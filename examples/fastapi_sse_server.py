"""FastAPI SSE 流式输出服务端示例

演示如何使用 HelloAgents 的流式输出功能构建 SSE 服务

运行方式：
    uvicorn examples.fastapi_sse_server:app --reload

测试方式：
    curl -N http://localhost:8000/agent/stream -X POST -H "Content-Type: application/json" -d '{"input": "你好"}'
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio

from hello_agents import ReActAgent, SimpleAgent, ReflectionAgent, PlanSolveAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config
from hello_agents.tools.registry import ToolRegistry
from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="HelloAgents SSE Demo")

# 添加 CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化 LLM
config = Config(
    model="deepseek-chat",
    api_key="your-api-key",
    base_url="https://api.deepseek.com",
    stream_enabled=True
)
llm = HelloAgentsLLM(config=config)

# 初始化工具注册表
registry = ToolRegistry()

# 注册示例工具
class CalculatorTool(Tool):
    """计算器工具"""

    def __init__(self):
        super().__init__(
            name="Calculator",
            description="执行数学计算，支持加减乘除"
        )

    def run(self, parameters: dict) -> ToolResponse:
        expression = parameters.get("expression", "") or parameters.get("input", "")
        try:
            result = eval(expression)
            return ToolResponse.success(
                text=f"计算结果: {result}",
                data={"expression": expression, "result": result}
            )
        except Exception as e:
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"计算错误: {str(e)}"
            )

    def get_parameters(self):
        return [
            ToolParameter(
                name="expression",
                type="string",
                description="数学表达式",
                required=True
            )
        ]

registry.register_tool(CalculatorTool())

# 初始化 Agent
react_agent = ReActAgent(
    name="ReActAssistant",
    llm=llm,
    tool_registry=registry,
    config=config
)

simple_agent = SimpleAgent(
    name="SimpleAssistant",
    llm=llm,
    config=config
)

reflection_agent = ReflectionAgent(
    name="ReflectionAssistant",
    llm=llm,
    config=config,
    max_iterations=2
)

plan_agent = PlanSolveAgent(
    name="PlanAssistant",
    llm=llm,
    config=config
)

# 请求模型
class AgentRequest(BaseModel):
    input: str
    agent_type: str = "react"  # react, simple, reflection, plan

@app.post("/agent/stream")
async def agent_stream(request: AgentRequest):
    """Agent 流式输出端点"""
    
    # 选择 Agent
    agent_map = {
        "react": react_agent,
        "simple": simple_agent,
        "reflection": reflection_agent,
        "plan": plan_agent
    }
    
    agent = agent_map.get(request.agent_type)
    if not agent:
        raise HTTPException(status_code=400, detail=f"未知的 agent_type: {request.agent_type}")
    
    async def event_generator():
        """SSE 事件生成器"""
        try:
            async for event in agent.arun_stream(request.input):
                # 转换为 SSE 格式
                yield event.to_sse()
                
                # 添加小延迟，避免前端处理不过来
                await asyncio.sleep(0.01)
        
        except Exception as e:
            # 发送错误事件
            error_sse = f"event: error\ndata: {{\"error\": \"{str(e)}\"}}\n\n"
            yield error_sse
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        }
    )

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "HelloAgents SSE Demo",
        "endpoints": {
            "stream": "/agent/stream",
            "docs": "/docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

