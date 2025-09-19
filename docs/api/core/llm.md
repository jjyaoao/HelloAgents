# HelloAgentsLLM API 文档

## 概述

`HelloAgentsLLM` 是HelloAgents框架的核心LLM接口，支持9种主流LLM提供商，提供统一的配置格式和智能provider检测。

## 类定义

```python
class HelloAgentsLLM:
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[SUPPORTED_PROVIDERS] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        **kwargs
    )
```

## 支持的提供商

| 提供商 | Provider值 | 自动检测 | 特点 |
|--------|------------|----------|------|
| ModelScope | `modelscope` | ✅ | 免费额度大，Qwen模型优秀 |
| OpenAI | `openai` | ✅ | 最成熟的商业LLM服务 |
| DeepSeek | `deepseek` | ✅ | 高性价比，代码能力强 |
| 通义千问 | `qwen` | ✅ | 阿里云官方Qwen服务 |
| Kimi | `kimi` | ✅ | 长上下文处理能力强 |
| 智谱AI | `zhipu` | ✅ | 清华技术，中文理解优秀 |
| Ollama | `ollama` | ✅ | 简单易用的本地LLM |
| vLLM | `vllm` | ✅ | 高性能推理服务 |
| 通用本地 | `local` | ✅ | 支持任何OpenAI兼容服务 |

## 初始化参数

### 基础参数

- **model** (`Optional[str]`): 模型名称，如果未提供则从环境变量`LLM_MODEL_ID`读取
- **api_key** (`Optional[str]`): API密钥，如果未提供则从环境变量读取
- **base_url** (`Optional[str]`): 服务地址，如果未提供则从环境变量`LLM_BASE_URL`读取
- **provider** (`Optional[SUPPORTED_PROVIDERS]`): LLM提供商，如果未提供则自动检测
- **temperature** (`float`): 温度参数，默认0.7
- **max_tokens** (`Optional[int]`): 最大token数
- **timeout** (`Optional[int]`): 超时时间，从环境变量`LLM_TIMEOUT`读取，默认60秒

## 配置方式

### 1. 统一配置（推荐）

```python
# .env文件
LLM_MODEL_ID=Qwen/Qwen2.5-72B-Instruct
LLM_API_KEY=ms-your-api-key
LLM_BASE_URL=https://api-inference.modelscope.cn/v1/
LLM_TIMEOUT=60

# Python代码
from hello_agents import HelloAgentsLLM

llm = HelloAgentsLLM()  # 自动检测为modelscope
```

### 2. 特定提供商环境变量

```python
# .env文件
MODELSCOPE_API_KEY=ms-your-api-key
OPENAI_API_KEY=sk-your-openai-key
OLLAMA_API_KEY=ollama

# Python代码
llm = HelloAgentsLLM()  # 自动检测对应的provider
```

### 3. 代码参数传递

```python
llm = HelloAgentsLLM(
    model="Qwen/Qwen2.5-72B-Instruct",
    api_key="ms-your-api-key",
    base_url="https://api-inference.modelscope.cn/v1/",
    provider="modelscope"
)
```

## 主要方法

### invoke()

同步调用LLM，返回完整响应。

```python
def invoke(self, messages: list[dict[str, str]], **kwargs) -> str
```

**参数:**
- `messages`: 消息列表，格式为`[{"role": "user", "content": "消息内容"}]`
- `**kwargs`: 额外参数，会覆盖初始化时的参数

**返回:**
- `str`: LLM的完整响应

**示例:**
```python
messages = [{"role": "user", "content": "你好！"}]
response = llm.invoke(messages)
print(response)
```

### stream_invoke()

流式调用LLM，返回响应流。

```python
def stream_invoke(self, messages: list[dict[str, str]], **kwargs) -> Iterator[str]
```

**参数:**
- `messages`: 消息列表
- `**kwargs`: 额外参数

**返回:**
- `Iterator[str]`: 响应流迭代器

**示例:**
```python
messages = [{"role": "user", "content": "讲个故事"}]
for chunk in llm.stream_invoke(messages):
    print(chunk, end="", flush=True)
```

### think()

思考方法，默认使用流式响应。

```python
def think(self, messages: list[dict[str, str]], temperature: Optional[float] = None) -> Iterator[str]
```

**参数:**
- `messages`: 消息列表
- `temperature`: 临时温度参数，会覆盖初始化时的值

**返回:**
- `Iterator[str]`: 响应流迭代器

## 自动检测逻辑

### 检测优先级

1. **特定提供商环境变量**（最高优先级）
2. **API密钥格式识别**
3. **Base URL域名识别**
4. **默认为auto**（通用配置）

### 检测规则

```python
# 1. 特定环境变量
MODELSCOPE_API_KEY → modelscope
OPENAI_API_KEY → openai
OLLAMA_API_KEY → ollama

# 2. API密钥格式
ms-xxx → modelscope
ollama → ollama
local → local
key.secret → zhipu

# 3. Base URL域名
api-inference.modelscope.cn → modelscope
api.openai.com → openai
localhost:11434 → ollama
```

## 属性

- **provider** (`str`): 检测到的或指定的提供商
- **model** (`str`): 使用的模型名称
- **api_key** (`str`): 使用的API密钥
- **base_url** (`str`): 使用的服务地址
- **temperature** (`float`): 温度参数
- **timeout** (`int`): 超时时间

## 异常处理

### HelloAgentsException

当配置不正确时抛出：

```python
from hello_agents.core.exceptions import HelloAgentsException

try:
    llm = HelloAgentsLLM()
except HelloAgentsException as e:
    print(f"配置错误: {e}")
```

## 使用示例

### 基础使用

```python
from hello_agents import HelloAgentsLLM

# 自动检测配置
llm = HelloAgentsLLM()
print(f"Provider: {llm.provider}")
print(f"Model: {llm.model}")

# 同步调用
response = llm.invoke([{"role": "user", "content": "你好"}])
print(response)

# 流式调用
for chunk in llm.stream_invoke([{"role": "user", "content": "讲个笑话"}]):
    print(chunk, end="")
```

### 本地部署使用

```python
# Ollama配置
llm = HelloAgentsLLM(
    model="llama3.2",
    api_key="ollama",
    base_url="http://localhost:11434/v1"
)

# vLLM配置
llm = HelloAgentsLLM(
    model="meta-llama/Llama-2-7b-chat-hf",
    api_key="vllm",
    base_url="http://localhost:8000/v1"
)
```

### 多provider切换

```python
# 配置不同的provider
providers = {
    "modelscope": {
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "api_key": "ms-your-key",
        "base_url": "https://api-inference.modelscope.cn/v1/"
    },
    "openai": {
        "model": "gpt-3.5-turbo",
        "api_key": "sk-your-key",
        "base_url": "https://api.openai.com/v1"
    }
}

for provider_name, config in providers.items():
    llm = HelloAgentsLLM(**config)
    response = llm.invoke([{"role": "user", "content": "你好"}])
    print(f"{provider_name}: {response}")
```

## 最佳实践

1. **使用统一配置格式**：推荐使用`LLM_*`环境变量
2. **让框架自动检测**：不指定provider，让框架智能选择
3. **本地部署优化**：增加超时时间，选择合适的模型大小
4. **错误处理**：捕获`HelloAgentsException`异常
5. **流式响应**：对于长文本生成，使用流式调用提升用户体验
