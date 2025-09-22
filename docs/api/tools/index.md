# 工具系统 API 文档

## 概述

HelloAgents提供了强大的工具系统，支持两种工具注册方式：Tool对象注册（推荐）和函数直接注册（简便）。

## 核心组件

### ToolRegistry

工具注册表，负责管理和执行工具。

```python
class ToolRegistry:
    def __init__(self)
    
    def register_tool(self, tool: Tool)
    def register_function(self, name: str, description: str, func: Callable, **kwargs)
    def execute_tool(self, name: str, **kwargs) -> Any
    def get_tool_descriptions(self) -> str
    def list_tools(self) -> list[str]
```

### Tool基类

所有工具的基类。

```python
class Tool(ABC):
    def __init__(self, name: str, description: str)
    
    @abstractmethod
    def execute(self, **kwargs) -> Any
    
    def get_schema(self) -> dict[str, Any]
```

## 工具注册

### 方式1：Tool对象注册（推荐）

```python
from hello_agents.tools.base import Tool
from hello_agents import ToolRegistry

class CalculatorTool(Tool):
    def __init__(self):
        super().__init__(
            name="calculator",
            description="执行基本数学计算"
        )
    
    def execute(self, expression: str) -> float:
        """执行数学表达式计算"""
        try:
            return eval(expression)
        except Exception as e:
            return f"计算错误: {e}"

# 注册工具
registry = ToolRegistry()
registry.register_tool(CalculatorTool())
```

### 方式2：函数直接注册（简便）

```python
from hello_agents import ToolRegistry

def calculate(expression: str) -> float:
    """执行数学计算
    
    Args:
        expression: 数学表达式，如 "2 + 3 * 4"
    
    Returns:
        计算结果
    """
    try:
        return eval(expression)
    except Exception as e:
        return f"计算错误: {e}"

# 注册函数
registry = ToolRegistry()
registry.register_function("calculate", "数学计算工具", calculate)
```

## 内置工具

### calculate

基础数学计算工具。

```python
from hello_agents.tools.builtin import calculate

# 直接使用
result = calculate("2 + 3 * 4")  # 14

# 注册到工具注册表
registry.register_function("calculate", "数学计算", calculate)
```

**参数:**
- `expression` (str): 数学表达式

**返回:**
- `float`: 计算结果

**示例:**
```python
calculate("10 + 5")      # 15.0
calculate("2 ** 3")      # 8.0
calculate("sqrt(16)")    # 4.0
```

### 搜索工具（可选）

需要安装额外依赖和配置API密钥。

#### Tavily搜索

```python
# 安装依赖
pip install tavily-python

# 配置API密钥
TAVILY_API_KEY=tvly-your-api-key

# 使用
from hello_agents.tools.builtin import tavily_search

result = tavily_search("Python编程教程")
```

#### SerpApi搜索

```python
# 安装依赖
pip install serpapi

# 配置API密钥
SERPAPI_API_KEY=your-serpapi-key

# 使用
from hello_agents.tools.builtin import serpapi_search

result = serpapi_search("机器学习算法")
```

## 工具执行

### 直接执行

```python
registry = ToolRegistry()
registry.register_function("calculate", "计算工具", calculate)

# 执行工具
result = registry.execute_tool("calculate", expression="2 + 3")
print(result)  # 5.0
```

### 在Agent中使用

```python
from hello_agents import ReActAgent, ToolRegistry, HelloAgentsLLM
from hello_agents.tools.builtin import calculate

# 创建工具注册表
registry = ToolRegistry()
registry.register_function("calculate", "数学计算工具", calculate)

# 创建Agent
llm = HelloAgentsLLM()
agent = ReActAgent("工具助手", llm, registry)

# 使用工具
response = agent.run("计算 123 * 456 的结果")
```

## 自定义工具开发

### 简单工具

```python
from hello_agents.tools.base import Tool

class WeatherTool(Tool):
    def __init__(self):
        super().__init__(
            name="weather",
            description="获取指定城市的天气信息"
        )
    
    def execute(self, city: str) -> str:
        # 这里应该调用真实的天气API
        return f"{city}的天气：晴天，温度25°C"

# 注册和使用
registry = ToolRegistry()
registry.register_tool(WeatherTool())
```

### 复杂工具

```python
import requests
from hello_agents.tools.base import Tool

class HttpRequestTool(Tool):
    def __init__(self):
        super().__init__(
            name="http_request",
            description="发送HTTP请求"
        )
    
    def execute(self, url: str, method: str = "GET", **kwargs) -> dict:
        """发送HTTP请求
        
        Args:
            url: 请求URL
            method: HTTP方法
            **kwargs: 其他请求参数
        
        Returns:
            响应数据
        """
        try:
            response = requests.request(method, url, **kwargs)
            return {
                "status_code": response.status_code,
                "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "请求的URL"
                    },
                    "method": {
                        "type": "string",
                        "description": "HTTP方法",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                        "default": "GET"
                    }
                },
                "required": ["url"]
            }
        }
```

## 工具管理

### 列出所有工具

```python
registry = ToolRegistry()
registry.register_function("calculate", "计算工具", calculate)

# 获取工具列表
tools = registry.list_tools()
print(tools)  # ['calculate']

# 获取工具描述
descriptions = registry.get_tool_descriptions()
print(descriptions)
```

### 工具信息

```python
# 检查工具是否存在
if "calculate" in registry.list_tools():
    result = registry.execute_tool("calculate", expression="2+3")

# 获取所有Tool对象
all_tools = registry.get_all_tools()
for tool in all_tools:
    print(f"工具: {tool.name}, 描述: {tool.description}")
```

## 错误处理

### 工具执行异常

```python
from hello_agents.core.exceptions import HelloAgentsException

try:
    result = registry.execute_tool("nonexistent_tool")
except HelloAgentsException as e:
    print(f"工具执行失败: {e}")
```

### 工具开发异常处理

```python
class SafeCalculatorTool(Tool):
    def __init__(self):
        super().__init__(
            name="safe_calculator",
            description="安全的数学计算工具"
        )
    
    def execute(self, expression: str) -> str:
        try:
            # 限制可用的函数和变量
            allowed_names = {
                k: v for k, v in __builtins__.items()
                if k in ['abs', 'round', 'min', 'max', 'sum']
            }
            allowed_names.update({
                'sqrt': lambda x: x ** 0.5,
                'pow': pow
            })
            
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return str(result)
        except Exception as e:
            return f"计算错误: {e}"
```

## 最佳实践

1. **工具命名**：使用清晰、描述性的名称
2. **文档字符串**：为工具函数提供详细的文档
3. **错误处理**：在工具中处理可能的异常
4. **参数验证**：验证输入参数的有效性
5. **返回格式**：保持一致的返回格式
6. **安全性**：避免执行不安全的代码（如eval）
7. **性能**：对于耗时操作，考虑添加超时机制

## 高级功能

### 工具链式调用

工具链允许将多个工具按顺序组合执行，实现复杂的工作流程。

```python
from hello_agents import ToolRegistry, ToolChain, ToolChainManager

# 创建工具注册表
registry = ToolRegistry()
registry.register_function("search", "搜索工具", search_function)
registry.register_function("calculate", "计算工具", calculate_function)

# 创建工具链
chain = ToolChain("research_chain", "研究和计算工具链")
chain.add_step("search", "{input}", "search_result")
chain.add_step("calculate", "2 + 2", "calc_result")

# 创建工具链管理器
chain_manager = ToolChainManager(registry)
chain_manager.register_chain(chain)

# 执行工具链
result = chain_manager.execute_chain("research_chain", "Python编程")
print(result)
```

**ToolChain API:**
- `ToolChain(name, description)` - 创建工具链
- `add_step(tool_name, input_template, output_key)` - 添加执行步骤
- `execute(registry, input_data, context)` - 执行工具链

**ToolChainManager API:**
- `ToolChainManager(registry)` - 创建管理器
- `register_chain(chain)` - 注册工具链
- `execute_chain(chain_name, input_data, context)` - 执行工具链
- `list_chains()` - 列出所有工具链
- `get_chain_info(chain_name)` - 获取工具链信息

### 异步工具执行

支持并行执行多个工具，提高执行效率。

```python
import asyncio
from hello_agents import ToolRegistry, AsyncToolExecutor

# 创建工具注册表
registry = ToolRegistry()
registry.register_function("calculate", "计算工具", calculate)

# 异步执行单个工具
async def single_async_example():
    executor = AsyncToolExecutor(registry)
    result = await executor.execute_tool_async("calculate", "2 + 3")
    print(result)
    executor.close()

# 并行执行多个工具
async def parallel_example():
    executor = AsyncToolExecutor(registry, max_workers=4)

    tasks = [
        {"tool_name": "calculate", "input_data": "2 + 2"},
        {"tool_name": "calculate", "input_data": "3 * 4"},
        {"tool_name": "calculate", "input_data": "10 / 2"},
    ]

    results = await executor.execute_tools_parallel(tasks)
    for result in results:
        print(f"{result['tool_name']}({result['input_data']}) = {result['result']}")

    executor.close()

# 运行异步示例
asyncio.run(parallel_example())
```

**AsyncToolExecutor API:**
- `AsyncToolExecutor(registry, max_workers)` - 创建异步执行器
- `execute_tool_async(tool_name, input_data)` - 异步执行单个工具
- `execute_tools_parallel(tasks)` - 并行执行多个工具
- `execute_tools_batch(tool_name, input_list)` - 批量执行同一工具
- `close()` - 关闭执行器

**便捷函数:**
- `run_parallel_tools(registry, tasks, max_workers)` - 异步并行执行
- `run_batch_tool(registry, tool_name, input_list, max_workers)` - 异步批量执行
- `run_parallel_tools_sync(registry, tasks, max_workers)` - 同步版本的并行执行
- `run_batch_tool_sync(registry, tool_name, input_list, max_workers)` - 同步版本的批量执行

## 完整示例

```python
from hello_agents import HelloAgentsLLM, ReActAgent, ToolRegistry
from hello_agents.tools.builtin import calculate

# 1. 创建LLM
llm = HelloAgentsLLM()

# 2. 创建工具注册表
registry = ToolRegistry()

# 3. 注册内置工具
registry.register_function("calculate", "数学计算工具", calculate)

# 4. 注册自定义工具
def get_time():
    """获取当前时间"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

registry.register_function("get_time", "获取当前时间", get_time)

# 5. 创建Agent
agent = ReActAgent("工具助手", llm, registry, max_steps=5)

# 6. 使用Agent
response = agent.run("现在几点了？然后帮我计算 123 + 456")
print(response)
```
