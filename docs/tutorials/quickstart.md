# 快速开始

## 安装

```bash
pip install hello-agents
```

## 基础使用

### 1. 创建简单Agent

```python
from hello_agents import SimpleAgent, HelloAgentsLLM

# 创建LLM实例
llm = HelloAgentsLLM(
    provider="deepseek",
    api_key="your-api-key"
)

# 创建Agent
agent = SimpleAgent(
    name="助手",
    llm=llm,
    system_prompt="你是一个有用的AI助手"
)

# 使用Agent
response = agent.run("你好！")
print(response)
```

### 2. 使用工具Agent

```python
from hello_agents import ToolAgent
from hello_agents.tools.builtin import SearchTool

# 创建带工具的Agent
agent = ToolAgent(
    name="研究助手",
    llm=llm,
    tools=[SearchTool()]
)

# 使用工具
response = agent.run("搜索最新的AI发展趋势")
```

## 下一步

- 查看[完整教程](./complete_guide.md)
- 浏览[API文档](../api/index.md)
- 运行[示例代码](../../examples/)