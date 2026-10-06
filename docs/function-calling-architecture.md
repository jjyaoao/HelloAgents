# Function Calling：从模型请求到工具回执

Function Calling 让模型按照工具声明生成名称与参数。模型提出请求，运行程序执行工具，再把结果放入下一次输入。声明工具不等于调用已经发生，工具成功也不等于整个任务已经完成。

## 目录

- [运行一个完整循环](#运行一个完整循环)
- [直接检查请求与回执](#直接检查请求与回执)
- [接入真实模型](#接入真实模型)
- [四类 Agent 怎样使用工具](#四类-agent-怎样使用工具)
- [错误与执行边界](#错误与执行边界)

## 运行一个完整循环

在源码根目录安装后，先运行不需要密钥的例子：

```bash
python -m pip install -r requirements.txt
python -X utf8 -m examples.agents.runtime_features --workspace workspace/runtime-demo
```

其中 `ScriptedLLM` 只按序提供预设响应，工具、消息组装和持久化实际执行。查看 `result.json`：首轮两次模型接口调用、一次工具执行，工具结果包含虚构线路的三公里与七公里。真实模型的请求顺序不固定，应通过实际工具回执验证。

## 直接检查请求与回执

以下片段展示运行器使用的三个对象：Schema 字典、`ToolCall` 与 `ToolResponse`。不连接模型。

```python
import json
from hello_agents.tools import ToolRegistry
from hello_agents.core.llm_response import ToolCall
from examples.agents.runtime_features import RouteTool

registry = ToolRegistry()
tool = RouteTool()
registry.register_tool(tool)
schema = tool.to_openai_schema()
assert schema["function"]["parameters"]["properties"]["legs"]["items"]["type"] == "object"

request = ToolCall("route-1", "route_distance", '{"legs":[{"route":"museum"}]}')
arguments = json.loads(request.arguments)
result = registry.execute_tool(request.name, arguments)
assert result.data["routes"][0]["walking_km"] == 3

messages = [
    {"role": "user", "content": "查询博物馆线的步行距离"},
    {"role": "assistant", "content": None, "tool_calls": [{
        "id": request.id, "type": "function", "function": {
            "name": request.name, "arguments": request.arguments,
        },
    }]},
    {"role": "tool", "tool_call_id": request.id, "content": result.to_model_text()},
]
assert messages[-1]["tool_call_id"] == messages[-2]["tool_calls"][0]["id"]
print(result.to_dict())
```

`ToolCall.arguments` 是 JSON 字符串，执行前解析成对象。每条 `tool` 回执必须指向相应请求的 ID；一次模型响应可含多条请求。不要只追加结果文本而丢掉关联，也不要直接执行来源不明的名称。

`Tool.to_openai_schema()` 提供完整声明。对象数组、枚举和范围约束通过 `ToolParameter.json_schema` 表达；模型可见声明不替代工具执行时的验证。写入、查询、权限等业务语义应放在工具中。[自定义工具指南](custom_tools_guide.md)提供完整写法。

## 接入真实模型

本段需要真实服务。先配置 `LLM_MODEL_ID`、`LLM_API_KEY`、`LLM_BASE_URL`，选择支持工具调用的模型，再在前例已有 `tool`、`registry` 的基础上调用：

```python
from hello_agents import Config, HelloAgentsLLM, SimpleAgent

llm = HelloAgentsLLM()
agent = SimpleAgent("线路助手", llm, tool_registry=registry, config=Config(
    trace_enabled=False, session_enabled=False, skills_enabled=False,
    subagent_enabled=False, todowrite_enabled=False, devlog_enabled=False,
))
answer = agent.run("使用 route_distance 查询 museum 线路的步行距离")
print(answer, agent.last_run.status)
```

如果只想取得模型请求而不自动执行，可直接使用 `llm.invoke_with_tools(messages=[...], tools=[tool.to_openai_schema()], tool_choice="auto")`。`tools` 是 Schema 字典列表，不是 Tool 实例列表；返回 `LLMToolResponse`，包含 `content`、`tool_calls`、`usage` 和 `finish_reason`。直接调用 LLM 后的执行与回填由调用方负责。

## 四类 Agent 怎样使用工具

- SimpleAgent 根据当前消息调用模型，执行请求，回填结果，继续下一轮。
- ReActAgent 提供 `Thought` 与 `Finish`，与注册的业务工具一起参与循环。含结束请求的批次按顺序处理。
- ReflectionAgent 在执行、评审与改进阶段使用共同循环；评审文本是公开反馈，不是模型私有推理。
- PlanSolveAgent 先要求 `generate_plan` 返回步骤，再逐步执行。它不自动证明步骤结果正确，也没有额外的外部验收阶段。

四个入口 `run/arun/stream_run/arun_stream` 都执行工具，差别在调用方式和输出形式。最终结果与状态见[运行指南](runtime-guide.md)。

## 错误与执行边界

未知工具、参数错误和业务失败以 `ToolResponse` 返回；运行器把可处理错误交给模型，供下一轮调整。空或重复请求 ID 在执行前拒绝，输出被截断时不执行残缺请求。网络、模型或运行程序异常继续抛出，不包装成空回答成功。

工具循环达到上限后可请求一次无工具总结；`max_iterations` 表示上限结束，不代表任务已经通过验收。`tool_choice` 控制支持该参数的服务如何选择工具；无工具总结请求不携带它。

调用工具前仍应做参数校验和授权。Schema、工具名称过滤与提示词都不是执行沙箱。并发、超时、取消和未知执行结果见[异步指南](async-agent-guide.md)与[会话指南](session-persistence-guide.md)。不根据工具协议推导固定成功率、成本或延迟提升。
