# 流式输出与 SSE 指南（Streaming & SSE）

## 📖 概述

**流式输出**是 HelloAgents 框架的实时响应能力，支持 SSE（Server-Sent Events）协议，实现打字机效果和实时进度反馈。

### 核心特性

- ✅ **真正的异步流式**：使用 AsyncOpenAI 原生客户端
- ✅ **实时传输**：LLM 生成一个 token 就立即返回
- ✅ **SSE 标准协议**：完美兼容浏览器 EventSource API
- ✅ **8 种事件类型**：AGENT_START、STEP_START、TOOL_CALL、LLM_CHUNK 等

---

## 🚀 快速开始

### 1. 基本流式输出

```python
import asyncio
from hello_agents import ReActAgent, HelloAgentsLLM

async def main():
    agent = ReActAgent("assistant", HelloAgentsLLM())
    
    # 流式执行
    async for event in agent.arun_stream("分析项目结构"):
        if event.type == "LLM_CHUNK":
            print(event.data["content"], end="", flush=True)

asyncio.run(main())
```

### 2. FastAPI SSE 服务端

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from hello_agents import ReActAgent, HelloAgentsLLM
import asyncio

app = FastAPI()

@app.post("/chat/stream")
async def chat_stream(message: str):
    agent = ReActAgent("assistant", HelloAgentsLLM())
    
    async def event_generator():
        async for event in agent.arun_stream(message):
            # 转换为 SSE 格式
            yield event.to_sse()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

# 运行：uvicorn server:app --reload
```

### 3. 前端 EventSource 客户端

```html
<!DOCTYPE html>
<html>
<head>
    <title>HelloAgents Chat</title>
</head>
<body>
    <div id="output"></div>
    <input id="input" type="text" placeholder="输入消息...">
    <button onclick="sendMessage()">发送</button>

    <script>
        function sendMessage() {
            const message = document.getElementById('input').value;
            const output = document.getElementById('output');
            
            // 创建 SSE 连接
            const eventSource = new EventSource(`/chat/stream?message=${message}`);
            
            eventSource.addEventListener('LLM_CHUNK', (e) => {
                const data = JSON.parse(e.data);
                output.innerHTML += data.content;
            });
            
            eventSource.addEventListener('AGENT_FINISH', (e) => {
                eventSource.close();
            });
        }
    </script>
</body>
</html>
```

---

## 💡 核心概念

### 8 种流式事件

| 事件类型           | 描述         | 关键字段                  |
| ------------------ | ------------ | ------------------------- |
| `AGENT_START`      | Agent 开始   | input, config             |
| `AGENT_FINISH`     | Agent 结束   | result, duration          |
| `STEP_START`       | 步骤开始     | step, max_steps           |
| `STEP_FINISH`      | 步骤结束     | step, action              |
| `TOOL_CALL_START`  | 工具调用开始 | tool_name, parameters     |
| `TOOL_CALL_FINISH` | 工具调用结束 | tool_name, result, status |
| `LLM_CHUNK`        | LLM 输出块   | content, delta            |
| `THINKING`         | 思考过程     | content                   |
| `ERROR`            | 错误事件     | error_type, message       |

### StreamEvent 数据结构

```python
from hello_agents.core.streaming import StreamEvent, StreamEventType

event = StreamEvent(
    type=StreamEventType.LLM_CHUNK,
    data={"content": "Hello", "delta": "Hello"},
    timestamp="2026-02-21T10:30:45.123Z",
    metadata={"step": 1}
)

# 转换为 SSE 格式
sse_text = event.to_sse()
# event: LLM_CHUNK
# data: {"content": "Hello", "delta": "Hello"}
# id: evt-xxx
#
```

---

## 📝 使用指南

### 1. 完整的 FastAPI 示例

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from hello_agents import ReActAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools.builtin import ReadTool, SearchTool
import asyncio

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    stream: bool = True

# 创建 Agent（全局单例）
registry = ToolRegistry()
registry.register_tool(ReadTool(project_root="./"))
registry.register_tool(SearchTool())

agent = ReActAgent("assistant", HelloAgentsLLM(), tool_registry=registry)

@app.post("/chat")
async def chat(request: ChatRequest):
    if request.stream:
        # 流式响应
        async def event_generator():
            try:
                async for event in agent.arun_stream(request.message):
                    yield event.to_sse()
            except Exception as e:
                # 错误事件
                error_event = StreamEvent(
                    type="ERROR",
                    data={"error": str(e)}
                )
                yield error_event.to_sse()
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        # 非流式响应
        result = await agent.arun(request.message)
        return {"result": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2. 前端完整示例

```html
<!DOCTYPE html>
<html>
<head>
    <title>HelloAgents Chat</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
        }
        #output {
            border: 1px solid #ccc;
            padding: 20px;
            min-height: 400px;
            margin-bottom: 20px;
            white-space: pre-wrap;
        }
        #input {
            width: 70%;
            padding: 10px;
            font-size: 16px;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
        }
        .thinking {
            color: #666;
            font-style: italic;
        }
        .tool-call {
            color: #0066cc;
            font-weight: bold;
        }
        .error {
            color: #cc0000;
        }
    </style>
</head>
<body>
    <h1>HelloAgents Chat</h1>
    <div id="output"></div>
    <input id="input" type="text" placeholder="输入消息...">
    <button onclick="sendMessage()">发送</button>

    <script>
        let currentEventSource = null;

        function sendMessage() {
            const message = document.getElementById('input').value;
            if (!message) return;

            const output = document.getElementById('output');
            output.innerHTML += `\n\n<strong>用户:</strong> ${message}\n<strong>助手:</strong> `;

            // 关闭之前的连接
            if (currentEventSource) {
                currentEventSource.close();
            }

            // 创建新的 SSE 连接
            currentEventSource = new EventSource(
                `http://localhost:8000/chat?message=${encodeURIComponent(message)}&stream=true`
            );

            // 监听不同类型的事件
            currentEventSource.addEventListener('AGENT_START', (e) => {
                console.log('Agent 开始');
            });

            currentEventSource.addEventListener('STEP_START', (e) => {
                const data = JSON.parse(e.data);
                output.innerHTML += `\n[步骤 ${data.step}/${data.max_steps}]\n`;
            });

            currentEventSource.addEventListener('THINKING', (e) => {
                const data = JSON.parse(e.data);
                output.innerHTML += `<span class="thinking">💭 ${data.content}</span>\n`;
            });

            currentEventSource.addEventListener('TOOL_CALL_START', (e) => {
                const data = JSON.parse(e.data);
                output.innerHTML += `<span class="tool-call">🔧 ${data.tool_name}</span> `;
            });

            currentEventSource.addEventListener('TOOL_CALL_FINISH', (e) => {
                const data = JSON.parse(e.data);
                output.innerHTML += `<span class="tool-call">✅</span>\n`;
            });

            currentEventSource.addEventListener('LLM_CHUNK', (e) => {
                const data = JSON.parse(e.data);
                output.innerHTML += data.content;
                output.scrollTop = output.scrollHeight;
            });

            currentEventSource.addEventListener('AGENT_FINISH', (e) => {
                console.log('Agent 完成');
                currentEventSource.close();
                currentEventSource = null;
            });

            currentEventSource.addEventListener('ERROR', (e) => {
                const data = JSON.parse(e.data);
                output.innerHTML += `<span class="error">❌ 错误: ${data.error}</span>\n`;
                currentEventSource.close();
                currentEventSource = null;
            });

            // 清空输入框
            document.getElementById('input').value = '';
        }

        // 支持回车发送
        document.getElementById('input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    </script>
</body>
</html>
```

---

## 📊 实际案例

### 案例 1：实时代码分析

**场景：** 分析项目结构，实时显示进度

```python
async def analyze_project():
    agent = ReActAgent("assistant", llm, tool_registry=registry)
    
    print("🚀 开始分析项目...")
    
    async for event in agent.arun_stream("分析项目结构"):
        if event.type == "STEP_START":
            print(f"\n📍 步骤 {event.data['step']}")
        
        elif event.type == "TOOL_CALL_START":
            tool = event.data['tool_name']
            print(f"  🔧 {tool}...", end="", flush=True)
        
        elif event.type == "TOOL_CALL_FINISH":
            print(" ✅")
        
        elif event.type == "LLM_CHUNK":
            print(event.data["content"], end="", flush=True)
        
        elif event.type == "AGENT_FINISH":
            print("\n\n🎉 分析完成！")
```

**输出示例：**
```
🚀 开始分析项目...

📍 步骤 1
  🔧 Read... ✅
  🔧 Search... ✅

项目结构如下：
- hello_agents/
  - core/
  - tools/
  - agents/

📍 步骤 2
  🔧 Read... ✅

核心模块包括...

🎉 分析完成！
```

### 案例 2：聊天机器人

**场景：** 实时对话，打字机效果

```python
# 服务端
@app.post("/chat/stream")
async def chat_stream(message: str):
    agent = SimpleAgent("assistant", llm)
    
    async def event_generator():
        async for event in agent.arun_stream(message):
            if event.type == "LLM_CHUNK":
                yield event.to_sse()
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

```javascript
// 前端
const eventSource = new EventSource(`/chat/stream?message=${message}`);

eventSource.addEventListener('LLM_CHUNK', (e) => {
    const data = JSON.parse(e.data);
    output.innerHTML += data.content;  // 打字机效果
});
```

### 案例 3：多用户并发

**场景：** 支持多用户同时对话

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from hello_agents import ReActAgent, HelloAgentsLLM
import asyncio
import uuid

app = FastAPI()

# 为每个用户创建独立的 Agent
user_agents = {}

@app.post("/chat/stream")
async def chat_stream(message: str, user_id: str = None):
    # 生成或获取用户 ID
    if not user_id:
        user_id = str(uuid.uuid4())

    # 为新用户创建 Agent
    if user_id not in user_agents:
        user_agents[user_id] = ReActAgent("assistant", HelloAgentsLLM())

    agent = user_agents[user_id]

    async def event_generator():
        async for event in agent.arun_stream(message):
            yield event.to_sse()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## 🎯 最佳实践

### 1. 错误处理

```python
async def event_generator():
    try:
        async for event in agent.arun_stream(message):
            yield event.to_sse()
    except Exception as e:
        # 发送错误事件
        error_event = StreamEvent(
            type="ERROR",
            data={"error": str(e), "error_type": type(e).__name__}
        )
        yield error_event.to_sse()
```

### 2. 超时控制

```python
import asyncio

async def event_generator():
    try:
        async for event in asyncio.wait_for(
            agent.arun_stream(message),
            timeout=60.0
        ):
            yield event.to_sse()
    except asyncio.TimeoutError:
        error_event = StreamEvent(
            type="ERROR",
            data={"error": "请求超时"}
        )
        yield error_event.to_sse()
```

### 3. 心跳保活

```python
async def event_generator():
    last_event_time = time.time()

    async for event in agent.arun_stream(message):
        yield event.to_sse()
        last_event_time = time.time()

        # 每 30 秒发送心跳
        if time.time() - last_event_time > 30:
            yield ": heartbeat\n\n"
            last_event_time = time.time()
```

---

## 🔧 高级用法

### 1. 自定义事件过滤

```python
async def event_generator():
    async for event in agent.arun_stream(message):
        # 只发送 LLM 输出和工具调用
        if event.type in ["LLM_CHUNK", "TOOL_CALL_START", "TOOL_CALL_FINISH"]:
            yield event.to_sse()
```

### 2. 事件转换

```python
async def event_generator():
    async for event in agent.arun_stream(message):
        # 转换为自定义格式
        if event.type == "LLM_CHUNK":
            custom_event = {
                "type": "message",
                "content": event.data["content"],
                "timestamp": event.timestamp
            }
            yield f"data: {json.dumps(custom_event)}\n\n"
```

### 3. 进度追踪

```python
async def event_generator():
    total_steps = 0
    current_step = 0

    async for event in agent.arun_stream(message):
        if event.type == "AGENT_START":
            total_steps = event.data.get("max_steps", 10)

        elif event.type == "STEP_START":
            current_step = event.data["step"]
            progress = (current_step / total_steps) * 100

            # 发送进度事件
            progress_event = StreamEvent(
                type="PROGRESS",
                data={"progress": progress, "step": current_step, "total": total_steps}
            )
            yield progress_event.to_sse()

        yield event.to_sse()
```

---

## 🔗 相关文档

- [异步 Agent](./async-agent-guide.md) - arun_stream() 详细说明
- [可观测性](./observability-guide.md) - 追踪流式执行
- [Function Calling](./function-calling-architecture.md) - 流式工具调用

---

## ❓ 常见问题

**Q: SSE 和 WebSocket 的区别？**

A:
- **SSE**: 单向通信（服务端 → 客户端），自动重连，简单易用
- **WebSocket**: 双向通信，需要手动管理连接，更复杂

**Q: 如何处理连接中断？**

A: EventSource 会自动重连：
```javascript
eventSource.onerror = (e) => {
    console.log('连接中断，自动重连...');
};
```

**Q: 如何取消流式请求？**

A: 关闭 EventSource：
```javascript
eventSource.close();
```

**Q: 流式输出的延迟？**

A: 几乎无延迟：
- LLM 生成 token → 立即发送
- 网络传输 < 10ms
- 浏览器渲染 < 5ms

**Q: 如何在 React 中使用？**

A: 使用 useEffect 管理连接：
```javascript
useEffect(() => {
    const eventSource = new EventSource('/chat/stream?message=' + message);

    eventSource.addEventListener('LLM_CHUNK', (e) => {
        const data = JSON.parse(e.data);
        setOutput(prev => prev + data.content);
    });

    return () => eventSource.close();
}, [message]);
```

---

## 📈 性能指标

### 延迟对比

| 模式     | 首字延迟  | 总延迟 | 用户体验 |
| -------- | --------- | ------ | -------- |
| 非流式   | 5-10s     | 5-10s  | 等待     |
| 流式输出 | 200-500ms | 5-10s  | 实时     |

### 资源消耗

| 指标       | 非流式 | 流式 |
| ---------- | ------ | ---- |
| 内存占用   | 高     | 低   |
| 网络带宽   | 突发   | 平稳 |
| 服务器并发 | 低     | 高   |

---

**最后更新**: 2026-02-21
