# 工具响应协议（ToolResponse Protocol）

## 📖 概述

**ToolResponse 协议**是 HelloAgents 框架的标准化工具响应格式，解决了传统字符串返回的模糊性问题。

### 解决的问题

**之前（字符串返回）：**
```python
def run(self, parameters: Dict[str, Any]) -> str:
    return "计算结果: 5"  # 无法区分成功/失败/部分成功
```

**问题：**
- ❌ 状态不明确（成功？失败？）
- ❌ 错误信息难以解析（需要正则匹配）
- ❌ 无法携带结构化数据
- ❌ Agent 需要"猜测"工具执行结果

**之后（ToolResponse 协议）：**
```python
def run(self, parameters: Dict[str, Any]) -> ToolResponse:
    return ToolResponse.success(
        text="计算结果: 5",
        data={"result": 5, "expression": "2+3"},
        stats={"time_ms": 10}
    )
```

**优势：**
- ✅ 状态明确（SUCCESS/PARTIAL/ERROR）
- ✅ 标准错误码（15种）
- ✅ 结构化数据载荷
- ✅ Agent 直接读取 status 字段

---

## 🚀 快速开始

### 1. 创建成功响应

```python
from hello_agents.tools.response import ToolResponse

# 简单成功响应
response = ToolResponse.success(
    text="文件读取成功",
    data={"content": "Hello World", "size": 11}
)

# 带统计信息
response = ToolResponse.success(
    text="搜索完成，找到 3 条结果",
    data={"results": [...]},
    stats={"time_ms": 245, "count": 3}
)
```

### 2. 创建错误响应

```python
from hello_agents.tools.errors import ToolErrorCode

# 文件不存在
response = ToolResponse.error(
    code=ToolErrorCode.NOT_FOUND,
    message="文件 'config.py' 不存在"
)

# 参数无效
response = ToolResponse.error(
    code=ToolErrorCode.INVALID_PARAM,
    message="参数 'path' 不能为空"
)
```

### 3. 创建部分成功响应

```python
# 结果被截断
response = ToolResponse.partial(
    text="搜索结果（前 100 条）",
    data={"results": results[:100], "total": 500},
    reason="结果过多，已截断"
)
```

---

## 💡 核心概念

### 三种状态

| 状态      | 含义                   | 使用场景                       |
| --------- | ---------------------- | ------------------------------ |
| `SUCCESS` | 任务完全按预期执行     | 正常完成                       |
| `PARTIAL` | 结果可用但存在折扣     | 截断、回退、部分失败           |
| `ERROR`   | 无有效结果（致命错误） | 文件不存在、权限错误、执行失败 |

### 标准错误码（15种）

```python
from hello_agents.tools.errors import ToolErrorCode

# 资源相关
ToolErrorCode.NOT_FOUND          # 资源不存在
ToolErrorCode.ALREADY_EXISTS     # 资源已存在
ToolErrorCode.PERMISSION_DENIED  # 权限不足

# 参数相关
ToolErrorCode.INVALID_PARAM      # 参数无效
ToolErrorCode.INVALID_FORMAT     # 格式错误

# 执行相关
ToolErrorCode.EXECUTION_ERROR    # 执行错误
ToolErrorCode.TIMEOUT            # 超时
ToolErrorCode.CONFLICT           # 冲突（乐观锁）

# 系统相关
ToolErrorCode.CIRCUIT_OPEN       # 熔断器开启
ToolErrorCode.RATE_LIMIT         # 速率限制
ToolErrorCode.NETWORK_ERROR      # 网络错误
ToolErrorCode.SERVICE_UNAVAILABLE # 服务不可用

# 其他
ToolErrorCode.PARTIAL_SUCCESS    # 部分成功
ToolErrorCode.DEPRECATED         # 已弃用
ToolErrorCode.UNKNOWN            # 未知错误
```

### ToolResponse 数据结构

```python
@dataclass
class ToolResponse:
    status: ToolStatus              # SUCCESS / PARTIAL / ERROR
    text: str                       # 给 LLM 阅读的格式化文本
    data: Dict[str, Any]            # 结构化数据载荷
    error_info: Optional[Dict]      # 错误信息（仅 ERROR 时）
    stats: Optional[Dict]           # 运行统计（时间、token等）
    context: Optional[Dict]         # 上下文信息（参数、环境等）
```

---

## 📝 使用指南

### 实现自定义工具

```python
from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse
from hello_agents.tools.errors import ToolErrorCode
from typing import Dict, Any, List

class MyTool(Tool):
    def __init__(self):
        super().__init__(
            name="MyTool",
            description="我的自定义工具"
        )
    
    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        try:
            # 1. 参数验证
            if not parameters.get("input"):
                return ToolResponse.error(
                    code=ToolErrorCode.INVALID_PARAM,
                    message="参数 'input' 不能为空"
                )
            
            # 2. 执行业务逻辑
            result = self._do_work(parameters["input"])
            
            # 3. 返回成功响应
            return ToolResponse.success(
                text=f"处理完成: {result}",
                data={"result": result}
            )
        
        except FileNotFoundError:
            return ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message="文件不存在"
            )
        
        except Exception as e:
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"执行失败: {str(e)}"
            )
    
    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="input",
                type="string",
                description="输入内容",
                required=True
            )
        ]
```

### 在 Agent 中使用

```python
from hello_agents import ReActAgent, HelloAgentsLLM, ToolRegistry

# 注册工具
registry = ToolRegistry()
registry.register_tool(MyTool())

# 创建 Agent
agent = ReActAgent("assistant", HelloAgentsLLM(), tool_registry=registry)

# Agent 自动处理 ToolResponse
result = agent.run("使用 MyTool 处理数据")
```

**Agent 内部处理逻辑：**
```python
# Agent 执行工具
tool_response = registry.execute_tool("MyTool", parameters)

# 根据状态处理
if tool_response.status == ToolStatus.SUCCESS:
    # 成功：继续执行
    print(f"✅ {tool_response.text}")

elif tool_response.status == ToolStatus.PARTIAL:
    # 部分成功：提示 Agent 注意
    print(f"⚠️ {tool_response.text}")

elif tool_response.status == ToolStatus.ERROR:
    # 错误：明确提示错误码和信息
    error_code = tool_response.error_info.get("code")
    print(f"❌ 错误 [{error_code}]: {tool_response.text}")
```

---

## 🔄 迁移指南

### 旧工具（字符串返回）

```python
class OldTool(Tool):
    def run(self, parameters: Dict[str, Any]) -> str:
        if not parameters.get("path"):
            return "错误: 参数 'path' 不能为空"

        try:
            content = read_file(parameters["path"])
            return f"文件内容: {content}"
        except FileNotFoundError:
            return "错误: 文件不存在"
```

### 新工具（ToolResponse 协议）

```python
class NewTool(Tool):
    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        # 参数验证
        if not parameters.get("path"):
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="参数 'path' 不能为空"
            )

        # 执行逻辑
        try:
            content = read_file(parameters["path"])
            return ToolResponse.success(
                text=f"文件读取成功",
                data={"content": content, "path": parameters["path"]}
            )
        except FileNotFoundError:
            return ToolResponse.error(
                code=ToolErrorCode.NOT_FOUND,
                message=f"文件 '{parameters['path']}' 不存在"
            )
```

**迁移步骤：**
1. 修改返回类型：`str` → `ToolResponse`
2. 成功时使用 `ToolResponse.success()`
3. 错误时使用 `ToolResponse.error()` + 标准错误码
4. 部分成功使用 `ToolResponse.partial()`

---

## 📊 实际案例

### 案例 1：文件读取工具

```python
from hello_agents.tools.builtin import ReadTool

# 成功读取
response = read_tool.run({"path": "config.py"})
# ToolResponse(
#     status=SUCCESS,
#     text="文件读取成功",
#     data={"content": "...", "size": 1024}
# )

# 文件不存在
response = read_tool.run({"path": "not_exist.py"})
# ToolResponse(
#     status=ERROR,
#     text="文件 'not_exist.py' 不存在",
#     error_info={"code": "NOT_FOUND", "message": "..."}
# )
```

### 案例 2：计算器工具

```python
from hello_agents.tools.builtin import CalculatorTool

calc = CalculatorTool()

# 成功计算
response = calc.run({"expression": "2 + 3"})
# ToolResponse(
#     status=SUCCESS,
#     text="计算结果: 5",
#     data={"result": 5, "expression": "2+3"}
# )

# 语法错误
response = calc.run({"expression": "2 +"})
# ToolResponse(
#     status=ERROR,
#     text="表达式语法错误",
#     error_info={"code": "INVALID_FORMAT", "message": "..."}
# )
```

### 案例 3：搜索工具（部分成功）

```python
# 结果过多，自动截断
response = search_tool.run({"query": "python"})
# ToolResponse(
#     status=PARTIAL,
#     text="搜索完成（前 100 条结果）",
#     data={"results": [...], "total": 500, "truncated": True},
#     reason="结果过多，已截断到 100 条"
# )
```

---

## 🎯 最佳实践

### 1. 明确的错误码

```python
# ❌ 不好：使用通用错误码
return ToolResponse.error(
    code=ToolErrorCode.UNKNOWN,
    message="出错了"
)

# ✅ 好：使用精确的错误码
return ToolResponse.error(
    code=ToolErrorCode.PERMISSION_DENIED,
    message="无权限访问文件 'secret.txt'"
)
```

### 2. 丰富的数据载荷

```python
# ❌ 不好：只返回文本
return ToolResponse.success(text="找到 3 个文件")

# ✅ 好：返回结构化数据
return ToolResponse.success(
    text="找到 3 个文件",
    data={
        "files": ["a.py", "b.py", "c.py"],
        "count": 3,
        "directory": "/src"
    }
)
```

### 3. 有用的统计信息

```python
return ToolResponse.success(
    text="搜索完成",
    data={"results": [...]},
    stats={
        "time_ms": 245,
        "count": 10,
        "api_calls": 1
    }
)
```

---

## 🔗 相关文档

- [熔断器机制](./circuit-breaker-guide.md) - 基于 ToolResponse 的错误判断
- [文件工具](./file_tools.md) - ReadTool、WriteTool 使用 ToolResponse
- [可观测性](./observability-guide.md) - TraceLogger 记录 ToolResponse

---

## ❓ 常见问题

**Q: 函数工具如何使用新协议？**

A: ToolRegistry 会自动包装函数工具为新协议：
```python
def my_function(x: int) -> str:
    return f"结果: {x * 2}"

registry.register_function(my_function)
# 自动包装为 ToolResponse.success(text="结果: 4", data={})
```

**Q: 如何判断工具是否支持新协议？**

A: 检查返回类型：
```python
response = tool.run(parameters)
if isinstance(response, ToolResponse):
    # 支持新协议
    print(response.status)
else:
    # 旧协议（字符串）
    print(response)
```

**Q: PARTIAL 和 ERROR 的区别？**

A:
- `PARTIAL`: 有结果，但不完整（截断、部分失败）
- `ERROR`: 无有效结果（致命错误）

---

**最后更新**: 2026-02-21


