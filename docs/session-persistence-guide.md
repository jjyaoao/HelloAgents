# 会话持久化使用指南

> 断点续跑的秘密——保存会话状态，随时恢复。

---

## 📖 概述

HelloAgents 的会话持久化功能允许你：

- ✅ **保存会话**：将 Agent 的完整状态保存到文件
- ✅ **恢复会话**：从文件恢复，实现断点续跑
- ✅ **环境检查**：自动检测配置和工具变化
- ✅ **异常保护**：崩溃或中断时自动保存
- ✅ **团队协作**：共享会话文件，多人协作

---

## 🚀 快速开始

### 基本使用

```python
from hello_agents import SimpleAgent, HelloAgentsLLM, Config

# 创建 Agent（默认启用会话持久化）
config = Config(session_enabled=True)
agent = SimpleAgent("assistant", HelloAgentsLLM(), config=config)

# 正常使用
result = agent.run("帮我分析这个项目")

# 手动保存会话
filepath = agent.save_session("my-analysis-session")
print(f"会话已保存: {filepath}")

# 恢复会话
agent.load_session("memory/sessions/my-analysis-session.json")

# 列出所有会话
sessions = agent.list_sessions()
for s in sessions:
    print(f"{s['session_id']} - {s['saved_at']}")
```

---

## 📋 核心功能

### 1. 保存会话

```python
# 手动保存会话
filepath = agent.save_session("my-session-name")
# 保存到: memory/sessions/my-session-name.json
```

**会话快照包含**：
- 完整的对话历史
- Agent 配置信息
- 工具 Schema 哈希
- Read 工具的文件元数据缓存
- 统计信息（tokens、steps、duration）

### 2. 恢复会话

```python
# 加载会话（默认检查环境一致性）
agent.load_session("memory/sessions/my-session-name.json")

# 跳过一致性检查
agent.load_session("memory/sessions/my-session-name.json", check_consistency=False)
```

**恢复内容**：
- ✅ 完整的对话历史
- ✅ 会话元数据
- ✅ Read 工具的文件元数据缓存（支持乐观锁）

### 3. 列出会话

```python
sessions = agent.list_sessions()

for session in sessions:
    print(f"会话 ID: {session['session_id']}")
    print(f"创建时间: {session['created_at']}")
    print(f"保存时间: {session['saved_at']}")
    print(f"总 Tokens: {session['metadata'].get('total_tokens', 0)}")
    print(f"总步数: {session['metadata'].get('total_steps', 0)}")
    print("---")
```

### 4. 删除会话

```python
# 通过 SessionStore 删除
if agent.session_store:
    agent.session_store.delete("my-session-name")
```

---

## ⚙️ 配置选项

### 基本配置

```python
from hello_agents import Config

config = Config(
    # 是否启用会话持久化
    session_enabled=True,
    
    # 会话文件保存目录
    session_dir="memory/sessions",
    
    # 是否启用自动保存
    auto_save_enabled=False,
    
    # 自动保存间隔（每 N 条消息）
    auto_save_interval=10
)
```

### 自动保存

```python
config = Config(
    session_enabled=True,
    auto_save_enabled=True,
    auto_save_interval=10  # 每 10 条消息自动保存
)

agent = SimpleAgent("assistant", llm, config=config)

# 每 10 条消息自动保存到 session-auto.json
agent.run("长时间任务")
```

### 禁用会话持久化

```python
config = Config(session_enabled=False)
agent = SimpleAgent("assistant", llm, config=config)

# 尝试保存会话会抛出异常
# RuntimeError: 会话持久化未启用
```

---

## 🛡️ 异常保护（ReActAgent）

ReActAgent 自动在异常时保存会话：

```python
from hello_agents import ReActAgent, ToolRegistry

agent = ReActAgent("assistant", llm, tool_registry=registry)

try:
    agent.run("长时间任务")
except KeyboardInterrupt:
    # 用户按 Ctrl+C 时自动保存为 session-interrupted.json
    print("会话已自动保存")
except Exception as e:
    # 发生错误时自动保存为 session-error.json
    print(f"错误: {e}，会话已自动保存")
```

**自动保存的会话名称**：
- `session-interrupted.json` - 用户中断（Ctrl+C）
- `session-error.json` - 发生异常

---

## 🔍 环境一致性检查

恢复会话时，框架会自动检查环境是否发生变化：

### 配置一致性

检查项：
- LLM 提供商（openai、anthropic 等）
- LLM 模型（gpt-4、gpt-3.5-turbo 等）
- 最大步数（max_steps）

```python
agent.load_session("memory/sessions/my-session.json")

# 如果配置不一致，会输出警告：
# ⚠️ 环境配置不一致：
#   - 模型变化: gpt-4 → gpt-3.5-turbo
```

### 工具 Schema 一致性

检查工具定义是否变化：

```python
agent.load_session("memory/sessions/my-session.json")

# 如果工具定义变化，会输出警告：
# ⚠️ 工具定义已变化
#   建议：建议重新读取文件
```

---

## 📦 会话文件结构

会话文件是标准的 JSON 格式：

```json
{
  "session_id": "s-20250119-a3f2d8e1",
  "created_at": "2025-01-19T10:30:45Z",
  "saved_at": "2025-01-19T10:45:10Z",
  
  "agent_config": {
    "name": "assistant",
    "agent_type": "ReActAgent",
    "llm_provider": "openai",
    "llm_model": "gpt-4",
    "max_steps": 10
  },
  
  "history": [
    {
      "role": "user",
      "content": "请分析这个仓库的架构",
      "timestamp": "2025-01-19T10:30:45Z"
    },
    {
      "role": "assistant",
      "content": "好的，我来分析...",
      "timestamp": "2025-01-19T10:31:00Z"
    }
  ],
  
  "tool_schema_hash": "a3f2d8e1",
  
  "read_cache": {
    "src/main.py": {
      "file_mtime_ms": 1738245123456,
      "file_size_bytes": 4217
    }
  },
  
  "metadata": {
    "created_at": "2025-01-19T10:30:45Z",
    "total_tokens": 43500,
    "total_steps": 25,
    "duration_seconds": 877
  }
}
```

---

## 💡 使用场景

### 场景 1：长时间任务断点续跑

**问题**：Agent 分析大型代码库，运行 30 分钟后网络断开

```python
# 第一次运行
agent = ReActAgent("assistant", llm, tool_registry=registry)

try:
    agent.run("分析整个代码库的架构")
except Exception:
    # 自动保存为 session-error.json
    pass

# 恢复后继续
agent.load_session("memory/sessions/session-error.json")
agent.run("继续之前的分析")
```

**收益**：
- ✅ 避免重复工作
- ✅ 节省 Token 成本
- ✅ 节省时间

### 场景 2：团队协作

**问题**：多人轮班处理复杂任务

```python
# 第一个人
agent1 = ReActAgent("assistant", llm, tool_registry=registry)
agent1.run("开始分析项目")
agent1.save_session("team-analysis-session")

# 第二个人接手
agent2 = ReActAgent("assistant", llm, tool_registry=registry)
agent2.load_session("memory/sessions/team-analysis-session.json")
agent2.run("继续分析")
```

**收益**：
- ✅ 无缝交接
- ✅ 保持上下文
- ✅ 提高协作效率

### 场景 3：调试和重现

**问题**：需要重现某个问题

```python
# 保存问题会话
agent.run("触发问题的操作")
agent.save_session("bug-reproduction")

# 随时重放
agent.load_session("memory/sessions/bug-reproduction.json")
# 查看历史，分析问题
history = agent.get_history()
```

**收益**：
- ✅ 精确重现问题
- ✅ 便于调试
- ✅ 便于报告 Bug

### 场景 4：实验和对比

**问题**：测试不同的提示词或配置

```python
# 实验 1
config1 = Config(max_steps=5)
agent1 = ReActAgent("assistant", llm, config=config1)
agent1.run("测试任务")
agent1.save_session("experiment-1")

# 实验 2
config2 = Config(max_steps=10)
agent2 = ReActAgent("assistant", llm, config=config2)
agent2.run("测试任务")
agent2.save_session("experiment-2")

# 对比结果
sessions = agent1.list_sessions()
for s in sessions:
    print(f"{s['filename']}: {s['metadata']['total_steps']} 步")
```

**收益**：
- ✅ 便于对比
- ✅ 可重复实验
- ✅ 数据驱动优化

---

## 🔧 高级用法

### 1. 自定义会话目录

```python
config = Config(
    session_enabled=True,
    session_dir="my-custom-sessions"  # 自定义目录
)
agent = SimpleAgent("assistant", llm, config=config)
```

### 2. 编程式访问 SessionStore

```python
from hello_agents.core.session_store import SessionStore

# 创建独立的 SessionStore
store = SessionStore(session_dir="my-sessions")

# 列出所有会话
sessions = store.list_sessions()

# 加载会话数据
session_data = store.load("my-sessions/my-session.json")

# 检查一致性
config_check = store.check_config_consistency(
    saved_config=session_data["agent_config"],
    current_config={"llm_model": "gpt-4"}
)

tool_check = store.check_tool_schema_consistency(
    saved_hash=session_data["tool_schema_hash"],
    current_hash="new-hash"
)
```

### 3. 恢复 Read 工具缓存

会话持久化自动集成了 Read 工具的元数据缓存（乐观锁）：

```python
# 第一次运行
agent.run("读取并编辑 config.py")
agent.save_session("edit-session")

# 恢复会话
agent.load_session("memory/sessions/edit-session.json")
# Read 工具的文件元数据缓存已自动恢复
# 可以继续编辑文件，乐观锁仍然有效
```

### 4. 条件保存

```python
# 只在特定条件下保存
if agent._session_metadata["total_steps"] > 10:
    agent.save_session("long-session")
```

---

## ⚠️ 注意事项

### 1. 会话文件大小

- 会话文件包含完整的对话历史
- 长对话可能产生较大的文件
- 建议定期清理旧会话

### 2. 环境一致性

- 恢复会话时，建议使用相同的配置和工具
- 如果环境变化，框架会给出警告
- 可以通过 `check_consistency=False` 跳过检查

### 3. 敏感信息

- 会话文件可能包含敏感信息（API Key、密码等）
- 建议不要提交到版本控制系统
- 添加 `memory/sessions/` 到 `.gitignore`

### 4. 自动保存性能

- 自动保存会增加 I/O 开销
- 建议根据实际需求调整 `auto_save_interval`
- 对于短对话，建议禁用自动保存

---

## 📚 API 参考

### Agent 方法

#### `save_session(session_name: str) -> str`

保存会话到文件。

**参数**：
- `session_name`: 会话名称（不含 .json 后缀）

**返回**：
- 保存的文件路径

**异常**：
- `RuntimeError`: 会话持久化未启用

#### `load_session(filepath: str, check_consistency: bool = True) -> None`

从文件加载会话。

**参数**：
- `filepath`: 会话文件路径
- `check_consistency`: 是否检查环境一致性（默认 True）

**异常**：
- `RuntimeError`: 会话持久化未启用
- `FileNotFoundError`: 文件不存在

#### `list_sessions() -> List[Dict[str, Any]]`

列出所有可用会话。

**返回**：
- 会话信息列表，按保存时间倒序排列

### SessionStore 方法

#### `save(...) -> str`

保存会话数据。

#### `load(filepath: str) -> Dict[str, Any]`

加载会话数据。

#### `list_sessions() -> List[Dict[str, Any]]`

列出所有会话。

#### `delete(session_name: str) -> bool`

删除会话。

#### `check_config_consistency(...) -> Dict[str, Any]`

检查配置一致性。

#### `check_tool_schema_consistency(...) -> Dict[str, Any]`

检查工具 Schema 一致性。

---

## 🎯 最佳实践

1. **定期保存**：长时间任务建议启用自动保存
2. **命名规范**：使用有意义的会话名称（如 `project-analysis-2025-01-19`）
3. **清理旧会话**：定期删除不需要的会话文件
4. **版本控制**：不要提交会话文件到 Git
5. **团队协作**：通过其他方式共享会话文件（如云存储）

---

## 🔗 相关文档

- [上下文工程优化](../refine/02-context-engineering.md)
- [乐观锁机制](../refine/08-optimistic-locking.md)
- [可观测性优化](../refine/03-observability.md)

---

**最后更新**：2025-01-19
**维护者**：HelloAgents 开发团队



