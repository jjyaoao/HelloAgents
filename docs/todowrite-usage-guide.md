# TodoWrite 进度管理工具使用指南

> 提供任务列表管理能力，强制单线程专注，避免任务切换

---

## 📚 目录

- [快速开始](#快速开始)
- [核心特性](#核心特性)
- [使用示例](#使用示例)
- [API 参考](#api-参考)
- [最佳实践](#最佳实践)
- [实战案例](#实战案例)

---

## 快速开始

### 零配置使用（推荐）

TodoWrite 工具已内置在 HelloAgents 框架中，默认启用。

```python
from hello_agents import ReActAgent, HelloAgentsLLM, ToolRegistry, Config

# 创建 Agent（TodoWriteTool 会自动注册）
config = Config(todowrite_enabled=True)
registry = ToolRegistry()
llm = HelloAgentsLLM()

agent = ReActAgent(
    name="开发助手",
    llm=llm,
    tool_registry=registry,
    config=config
)

# Agent 可以直接使用 TodoWrite 工具
agent.run("帮我实现用户系统、订单系统和支付系统")
```

### 手动使用

```python
from hello_agents.tools.builtin import TodoWriteTool

# 创建工具
tool = TodoWriteTool(
    project_root="./",
    persistence_dir="memory/todos"
)

# 创建任务列表
response = tool.run({
    "summary": "实现电商核心功能",
    "todos": [
        {"content": "实现用户认证", "status": "pending"},
        {"content": "实现订单处理", "status": "pending"},
        {"content": "实现支付功能", "status": "pending"}
    ]
})

print(response.text)
# 📋 [0/3] 待处理: 实现用户认证; 实现订单处理; 实现支付功能
```

---

## 核心特性

### 1. 声明式覆盖

每次提交完整的任务列表，避免状态不一致。

```python
# ✅ 正确：提交完整列表
response = tool.run({
    "todos": [
        {"content": "任务1", "status": "completed"},
        {"content": "任务2", "status": "in_progress"},
        {"content": "任务3", "status": "pending"}
    ]
})

# ❌ 错误：不支持增量更新
# tool.add_todo(...)  # 不存在此方法
```

### 2. 单线程强制

最多只能有 1 个任务标记为 `in_progress`，防止任务切换和焦点丢失。

```python
# ❌ 错误：多个 in_progress
response = tool.run({
    "todos": [
        {"content": "任务1", "status": "in_progress"},
        {"content": "任务2", "status": "in_progress"}  # 违反约束
    ]
})
# 返回错误：最多只能有 1 个 in_progress 任务

# ✅ 正确：最多 1 个 in_progress
response = tool.run({
    "todos": [
        {"content": "任务1", "status": "in_progress"},
        {"content": "任务2", "status": "pending"}
    ]
})
```

### 3. 自动 Recap 生成

自动生成紧凑的进度摘要，节省上下文。

```python
# 部分完成
"📋 [2/5] 进行中: 实现订单查询. 待处理: 实现订单创建; 实现订单更新"

# 全部完成
"✅ [5/5] 所有任务已完成！"

# 无任务
"📋 [0/0] 无活动任务"

# 多个待处理（截断）
"📋 [3/10] 进行中: 实现认证. 待处理: 任务1; 任务2; 任务3. 还有 4 个..."
```

### 4. 持久化支持

任务列表自动保存到文件，支持断点恢复。

```python
# 自动保存
memory/todos/
├── todoList-20250220-103045.json
├── todoList-20250220-143022.json
└── todoList-20250220-183033.json

# 加载历史任务
tool.load_todos("memory/todos/todoList-20250220-103045.json")
```

---

## 使用示例

### 示例 1：基本工作流

```python
from hello_agents.tools.builtin import TodoWriteTool

tool = TodoWriteTool(project_root="./")

# 1. 创建任务列表
response = tool.run({
    "summary": "实现博客系统",
    "todos": [
        {"content": "设计数据库", "status": "pending"},
        {"content": "实现用户模块", "status": "pending"},
        {"content": "实现文章模块", "status": "pending"}
    ]
})
print(response.text)
# 📋 [0/3] 待处理: 设计数据库; 实现用户模块; 实现文章模块

# 2. 开始第一个任务
response = tool.run({
    "summary": "实现博客系统",
    "todos": [
        {"content": "设计数据库", "status": "in_progress"},
        {"content": "实现用户模块", "status": "pending"},
        {"content": "实现文章模块", "status": "pending"}
    ]
})
print(response.text)
# 📋 [0/3] 进行中: 设计数据库. 待处理: 实现用户模块; 实现文章模块

# 3. 完成第一个任务，开始第二个
response = tool.run({
    "summary": "实现博客系统",
    "todos": [
        {"content": "设计数据库", "status": "completed"},
        {"content": "实现用户模块", "status": "in_progress"},
        {"content": "实现文章模块", "status": "pending"}
    ]
})
print(response.text)
# 📋 [1/3] 进行中: 实现用户模块. 待处理: 实现文章模块

# 4. 全部完成
response = tool.run({
    "summary": "实现博客系统",
    "todos": [
        {"content": "设计数据库", "status": "completed"},
        {"content": "实现用户模块", "status": "completed"},
        {"content": "实现文章模块", "status": "completed"}
    ]
})
print(response.text)
# ✅ [3/3] 所有任务已完成！
```

### 示例 2：清空任务列表

```python
# 清空所有任务
response = tool.run({"action": "clear"})
print(response.text)
# ✅ 任务列表已清空
```

### 示例 3：加载历史任务

```python
# 加载之前保存的任务列表
tool.load_todos("memory/todos/todoList-20250220-103045.json")

# 查看当前状态
stats = tool.current_todos.get_stats()
print(f"总任务: {stats['total']}")
print(f"已完成: {stats['completed']}")
print(f"进行中: {stats['in_progress']}")
print(f"待处理: {stats['pending']}")
```

---

## API 参考

### TodoWriteTool

#### 初始化

```python
TodoWriteTool(
    project_root: str = ".",
    persistence_dir: str = "memory/todos"
)
```

**参数**：
- `project_root`: 项目根目录
- `persistence_dir`: 持久化目录（相对于 project_root）

#### run() 方法

```python
tool.run(parameters: Dict[str, Any]) -> ToolResponse
```

**参数**：
- `summary` (str, 可选): 总体任务描述
- `todos` (list, 可选): 待办事项列表
- `action` (str, 可选): 操作类型（create/update/clear）

**todos 格式**：
```python
[
    {
        "content": "任务内容",
        "status": "pending" | "in_progress" | "completed"
    }
]
```

**返回**：
- `ToolResponse` 对象
  - `status`: SUCCESS/ERROR
  - `text`: Recap 文本
  - `data`: 统计信息

#### load_todos() 方法

```python
tool.load_todos(filepath: str)
```

从文件加载任务列表。

### TodoList

#### 方法

```python
# 获取当前进行的任务
get_in_progress() -> Optional[TodoItem]

# 获取待处理任务
get_pending(limit: int = 5) -> List[TodoItem]

# 获取已完成任务
get_completed() -> List[TodoItem]

# 获取统计信息
get_stats() -> dict
```

---

## 最佳实践

### 1. 任务粒度

✅ **推荐**：适中粒度，每个任务 1-4 小时
```python
{"content": "实现用户注册接口", "status": "pending"}
{"content": "实现用户登录接口", "status": "pending"}
```

❌ **不推荐**：粒度过大
```python
{"content": "实现整个用户系统", "status": "pending"}  # 太大
```

❌ **不推荐**：粒度过小
```python
{"content": "创建 User 模型", "status": "pending"}  # 太小
{"content": "添加 email 字段", "status": "pending"}  # 太小
```

### 2. 任务数量

- **建议**：5-10 个任务为宜
- **最多**：不超过 20 个（Recap 会截断）

### 3. 状态转换

遵循单向流转：`pending → in_progress → completed`

```python
# ✅ 正确的状态转换
pending → in_progress  # 开始任务
in_progress → completed  # 完成任务

# ❌ 避免的状态转换
completed → in_progress  # 不要重新打开已完成任务
in_progress → pending  # 如需暂停，应该完成或取消
```

### 4. 持久化策略

```python
# 关键节点手动保存
tool.run({...})  # 自动保存

# 定期检查持久化文件
from pathlib import Path
todos_dir = Path("memory/todos")
files = sorted(todos_dir.glob("todoList-*.json"))
latest = files[-1] if files else None
```

---

## 实战案例

### 案例 1：复杂项目开发

**场景**：开发一个完整的电商系统

```python
# 创建项目计划
response = tool.run({
    "summary": "开发电商系统",
    "todos": [
        {"content": "设计数据库模型", "status": "pending"},
        {"content": "实现用户认证", "status": "pending"},
        {"content": "实现商品管理", "status": "pending"},
        {"content": "实现购物车", "status": "pending"},
        {"content": "实现订单系统", "status": "pending"},
        {"content": "实现支付集成", "status": "pending"},
        {"content": "编写测试", "status": "pending"},
        {"content": "部署上线", "status": "pending"}
    ]
})

# 逐步完成任务...
```

**优势**：
- 清晰的任务列表，不会遗漏
- 单线程专注，避免上下文切换
- 进度透明，随时了解完成情况

### 案例 2：长时间运行任务

**场景**：分析大型代码库，运行 2 小时后网络断开

```python
# 之前：所有进度丢失，需要重新开始

# 之后：
# 1. 任务列表自动持久化
# 2. 恢复会话后加载最新状态
tool.load_todos("memory/todos/todoList-20250220-143022.json")

# 3. 继续完成当前任务
response = tool.run({
    "todos": [
        {"content": "分析核心模块", "status": "completed"},
        {"content": "分析工具模块", "status": "completed"},
        {"content": "生成重构建议", "status": "in_progress"}  # 从这里继续
    ]
})
```

### 案例 3：多轮对话

**场景**：用户分多次对话完成任务

```python
# 第 1 轮对话
用户: "帮我实现用户认证"
Agent: 创建任务列表 [认证, 订单, 支付]
      📋 [0/3] 进行中: 实现用户认证

# 第 2 轮对话（第二天）
用户: "现在实现订单处理"
Agent: 📋 [1/3] 进行中: 实现订单处理（认证已完成）

# 第 3 轮对话（第三天）
用户: "最后实现支付功能"
Agent: 📋 [2/3] 进行中: 实现支付功能
```

---

## 配置选项

### Config 参数

```python
from hello_agents import Config

config = Config(
    # 启用/禁用 TodoWrite
    todowrite_enabled=True,
    
    # 持久化目录
    todowrite_persistence_dir="memory/todos"
)
```

### 禁用 TodoWrite

```python
config = Config(todowrite_enabled=False)
agent = ReActAgent("assistant", llm, tool_registry=registry, config=config)
```

---

## 常见问题

### Q1: 如何修改已创建的任务？

A: 使用声明式 API，提交完整的新列表：

```python
# 修改任务内容
response = tool.run({
    "todos": [
        {"content": "新的任务描述", "status": "pending"},  # 修改后的内容
        {"content": "任务2", "status": "pending"}
    ]
})
```

### Q2: 可以同时进行多个任务吗？

A: 不可以。TodoWrite 强制单线程，最多 1 个 `in_progress`，这是设计约束，目的是保持专注。

### Q3: 如何查看历史任务列表？

A: 查看 `memory/todos/` 目录下的 JSON 文件：

```python
from pathlib import Path
import json

todos_dir = Path("memory/todos")
files = sorted(todos_dir.glob("todoList-*.json"))

for file in files:
    with open(file) as f:
        data = json.load(f)
        print(f"{file.name}: {data['summary']}")
```

### Q4: 任务列表会自动保存吗？

A: 是的，每次调用 `tool.run()` 都会自动保存到 `memory/todos/` 目录。

---

## 相关文档

- [工具响应协议](../refine/01-tool-response-protocol.md)
- [会话持久化](../refine/05-session-persistence.md)
- [子代理机制](../refine/06-subagent-mechanism.md)

---

## 示例代码

完整示例代码请参考：
- `examples/todowrite_demo.py` - 基础示例
- `examples/todowrite_real_world.py` - 实战案例

