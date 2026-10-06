# LLM 消息输入与流式响应

`HelloAgentsLLM` 负责模型调用与响应适配。直接调用它时，应用自行组织消息；使用 SimpleAgent 时，运行器还会处理工具请求、回执和下一轮调用。先分清这两层，才能决定使用哪一种入口。

## 📚 目录

- [快速开始](#快速开始)
- [选择调用入口](#选择调用入口)
- [消息输入](#消息输入)
- [入参检查](#入参检查)
- [流式结束分片](#流式结束分片)
- [本地验证](#本地验证)
- [保留工具请求与结果的关联](#保留工具请求与结果的关联)
- [常见问题](#常见问题)

## 快速开始

从源码根目录安装基础依赖，在应用 `.env` 中填写 `LLM_MODEL_ID`、`LLM_API_KEY`、`LLM_BASE_URL`。下面调用真实模型，运行前应确认服务可用。

```python
from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM

load_dotenv()
with HelloAgentsLLM() as llm:
    messages = [
        {"role": "system", "content": "用简洁中文回答，只依据已提供的信息。"},
        {"role": "user", "content": "旅行预算是1500元，住宿600元，还剩多少？"},
    ]
    first = llm.invoke(messages)
    print(first.content)
    messages.append({"role": "assistant", "content": first.content})
    messages.append({"role": "user", "content": "如果再预留180元交通费呢？"})
    second = llm.invoke(messages)
    print(second.content)
```

第二次调用能看到预算，是因为应用再次传入了此前消息。模型客户端本身不会自动把第一次请求追加成会话历史。`with` 在结束时关闭客户端；服务返回内容可能不同，例子不预设固定措辞。

## 选择调用入口

| 入口 | 返回内容 | 由谁组织后续步骤 |
| --- | --- | --- |
| `invoke(messages)` | `LLMResponse` | 应用读取 `.content` 并维护消息 |
| `invoke_with_tools(messages, tools)` | `LLMToolResponse` | 应用检查工具请求并回传结果 |
| `stream_invoke(messages)` | 文本增量迭代器 | 应用消费或及时关闭迭代器 |
| `SimpleAgent.run(text)` | 本轮结果文本 | Agent Loop 负责工具循环 |

异步环境可使用对应的 `ainvoke`、`ainvoke_with_tools`、`astream_invoke`。工具调用协议的完整例子见 [Function Calling](function-calling-architecture.md)；流式 Agent 事件与模型文本分片不同，见 [流式输出](streaming-sse-guide.md)。

## 消息输入

`HelloAgentsLLM` 的消息接口接收字典列表。它与 LangChain 的消息对象接口不同，不需要安装 LangChain。

```python
from hello_agents import HelloAgentsLLM

llm = HelloAgentsLLM()  # 从环境变量读取模型、地址和密钥
understand_prompt = "分析用户的旅行需求，并给出可用于检索的关键词。"
response = llm.invoke([
    {"role": "user", "content": understand_prompt}
])
print(response.content)
```

不要直接传入 `HumanMessage(content=understand_prompt)`。对于已知的单条用户文本，可显式写为 `{"role": "user", "content": message.content}`。完整会话的转换还要保留各条消息的角色、工具调用及结果关联，不能把所有消息一律改成 user。

框架自身用于历史管理的 `Message` 也不同于模型请求字典。其 `to_dict()` 包含时间戳和存储元数据，不能作为所有模型服务都接受的请求格式。单条普通文本可明确选取 `role` 和 `content`；内部 `summary` 角色应在上下文层转换成注明来源的参考消息。

调用返回 `LLMResponse`，回答文本位于 `.content`。不要将响应对象直接当作字符串进行正则匹配或拼接。

## 入参检查

同步、异步、流式以及 Function Calling 入口使用相同的基础检查：

- `messages` 必须是列表，每个元素必须是字典。
- 每个字典必须有非空字符串 `role`。
- 错误指出元素下标，不输出用户消息正文，也不发出远端请求。

这不是提供商完整 schema 验证。多模态 content、`tool_calls`、`tool_call_id` 及其他提供商字段保持原样，具体支持情况由所选适配器和模型接口决定。

## 流式结束分片

兼容接口可能发送 `choices=[]` 的统计分片。这不表示调用失败。当前 OpenAIAdapter 的同步与异步路径先检查 choices，再读取文本；usage 在文本判断之外提取，因此空 choices 的末尾分片仍可更新统计。

```python
for text in llm.stream_invoke([{"role": "user", "content": "你好"}]):
    print(text, end="")
print(llm.last_call_stats)
```

流式消费应保留网络错误和服务错误，不要在外层捕获后无条件返回空字符串。

## 本地验证

```bash
python -m pytest tests/test_llm_message_contract.py tests/test_llm_streaming.py
```

测试使用 SDK 响应形状的替身核对输入边界和分片处理，不连接模型服务。

## 保留工具请求与结果的关联

工具调用不是一段普通 assistant 文本。一次交互至少要保留模型消息中的 `tool_calls`，以及每条结果的 `tool_call_id`。下面仅展示消息结构，不会实际执行工具：

```python
messages = [
    {"role": "user", "content": "请计算住宿费用"},
    {"role": "assistant", "content": None, "tool_calls": [{
        "id": "call_budget", "type": "function",
        "function": {"name": "budget", "arguments": '{"nights":2,"price":320}'},
    }]},
    {"role": "tool", "tool_call_id": "call_budget", "content": '{"total":640}'},
]
assert messages[1]["tool_calls"][0]["id"] == messages[2]["tool_call_id"]
```

`arguments` 是 JSON 字符串，执行前需要解析并校验；结果 `content` 也是服务约定的消息内容，不能直接塞入任意 Python 对象。同一模型消息请求多个工具时，各结果分别与自己的 ID 对应。保存或压缩历史时，应一起保留调用和结果，避免产生孤立回执。

## 常见问题

**返回对象不能直接拼接字符串怎么办？**

普通回答读取 `response.content`。工具响应还要先看是否存在工具请求，不能把空正文等同于失败。

**设置了 .env，为什么仍提示缺少配置？**

客户端读取进程环境，不隐式查找磁盘文件。由应用在构造客户端前调用 `load_dotenv()`，并确认工作目录或显式文件路径正确。

**有流式文本就代表任务结束了吗？**

不代表。模型可能先输出说明，再请求工具；使用 SimpleAgent 时检查完成事件和运行状态。直接使用文本流时应正常消费结束，并处理服务异常。
