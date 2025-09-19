# HelloAgents API 文档

## 🚀 快速导航

### 核心组件

#### 🤖 [LLM接口](./core/llm.md)
- 支持9种主流LLM提供商
- 统一配置格式和智能检测
- 同步/异步调用接口

#### 🎯 [Agent系统](./agents/index.md)
- SimpleAgent - 基础对话Agent
- ReActAgent - 工具调用和推理Agent
- ReflectionAgent - 自我反思和改进Agent
- PlanAndSolveAgent - 计划分解和执行Agent

#### 🛠️ [工具系统](./tools/index.md)
- 工具注册和管理
- 内置工具集合
- 自定义工具开发

## 📋 API参考

### 核心类

| 类名 | 描述 | 文档链接 |
|------|------|----------|
| `HelloAgentsLLM` | LLM统一接口 | [详细文档](./core/llm.md) |
| `SimpleAgent` | 基础对话Agent | [详细文档](./agents/index.md#simpleagent) |
| `ReActAgent` | 工具调用Agent | [详细文档](./agents/index.md#reactagent) |
| `ToolRegistry` | 工具注册表 | [详细文档](./tools/index.md#toolregistry) |
| `Tool` | 工具基类 | [详细文档](./tools/index.md#tool基类) |

### 支持的LLM提供商

| 提供商 | Provider | 自动检测 | 特点 |
|--------|----------|----------|------|
| 🔥 ModelScope | `modelscope` | ✅ | 免费额度大，Qwen模型优秀 |
| 🤖 OpenAI | `openai` | ✅ | 最成熟的商业LLM服务 |
| 🚀 DeepSeek | `deepseek` | ✅ | 高性价比，代码能力强 |
| ☁️ 通义千问 | `qwen` | ✅ | 阿里云官方Qwen服务 |
| 🌙 Kimi | `kimi` | ✅ | 长上下文处理能力强 |
| 🧠 智谱AI | `zhipu` | ✅ | 清华技术，中文理解优秀 |
| 🦙 Ollama | `ollama` | ✅ | 简单易用的本地LLM |
| ⚡ vLLM | `vllm` | ✅ | 高性能推理服务 |
| 🏠 通用本地 | `local` | ✅ | 支持任何OpenAI兼容服务 |

## 🎯 使用场景

### 基础对话
```python
from hello_agents import HelloAgentsLLM, SimpleAgent

llm = HelloAgentsLLM()  # 自动检测配置
agent = SimpleAgent("AI助手", llm)
response = agent.run("你好！")
```

### 工具调用
```python
from hello_agents import ReActAgent, ToolRegistry
from hello_agents.tools.builtin import calculate

registry = ToolRegistry()
registry.register_function("calculate", "计算工具", calculate)

agent = ReActAgent("工具助手", llm, registry)
response = agent.run("计算 123 * 456")
```

### 代码生成
```python
from hello_agents import ReflectionAgent

agent = ReflectionAgent("代码助手", llm, max_iterations=2)
response = agent.run("编写一个快速排序算法")
```

### 问题分解
```python
from hello_agents import PlanAndSolveAgent

agent = PlanAndSolveAgent("规划助手", llm)
response = agent.run("如何设计一个推荐系统？")
```

## 📚 更多资源

- [快速开始指南](../tutorials/quickstart.md)
- [配置文档](../configuration.md)
- [版本更新指南](../tutorials/version_update_guide.md)
- [GitHub仓库](https://github.com/your-repo/hello-agents)