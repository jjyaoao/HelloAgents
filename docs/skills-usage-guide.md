# Skills 知识外化系统使用指南

> 让 Agent 按需加载领域知识，无需 fine-tuning，节省 85% Token

---

## 🎯 什么是 Skills？

Skills 是 HelloAgents 的知识外化系统，允许你将领域知识写成独立的 Markdown 文件，Agent 会在需要时自动加载。

**核心优势**：
- ✅ **零配置**：创建 `skills/` 目录即可自动激活
- ✅ **按需加载**：启动时只加载元数据，使用时才加载完整内容
- ✅ **Token 节省**：20 个技能场景下节省 85% Token（40K → 6K）
- ✅ **人类可编辑**：纯文本 Markdown，支持版本控制
- ✅ **团队协作**：技能文件独立管理，Git 友好

---

## 🚀 快速开始

### 1. 创建技能目录

在项目根目录创建 `skills/` 文件夹：

```bash
mkdir skills
```

### 2. 创建第一个技能

创建 `skills/pdf/SKILL.md`：

```markdown
---
name: pdf
description: Process PDF files. Use when reading, creating, or merging PDFs.
---

# PDF Processing Skill

## Reading PDFs

Use pdftotext for quick text extraction:
\`\`\`bash
pdftotext input.pdf -
\`\`\`

## Creating PDFs

Use pandoc for creating PDFs from Markdown:
\`\`\`bash
pandoc input.md -o output.pdf --pdf-engine=xelatex
\`\`\`

$ARGUMENTS
```

**关键点**：
- `---` 分隔的 YAML frontmatter 是必需的
- `name` 和 `description` 字段必须存在
- `$ARGUMENTS` 占位符会被替换为用户传入的参数

### 3. 使用 Agent

```python
from hello_agents import ReActAgent, HelloAgentsLLM
from hello_agents.tools import ToolRegistry

# 创建 Agent（框架会自动检测 skills/ 目录）
agent = ReActAgent(
    name="assistant",
    llm=HelloAgentsLLM(provider="openai", model="gpt-4"),
    tool_registry=ToolRegistry()
)

# Agent 会自动加载 pdf 技能
result = agent.run("帮我提取 report.pdf 的文本内容")
```

**就这么简单！** 🎉

---

## 📁 目录结构

### 基础结构

```
your-project/
├── skills/                    # ← 技能目录（自动检测）
│   ├── pdf/
│   │   └── SKILL.md          # ← 必需文件
│   ├── code-review/
│   │   └── SKILL.md
│   └── mcp-builder/
│       └── SKILL.md
└── main.py                    # ← 你的代码
```

### 带资源的结构

```
skills/
└── my-skill/
    ├── SKILL.md              # ← 必需：技能定义
    ├── scripts/              # ← 可选：脚本文件
    │   └── helper.py
    ├── references/           # ← 可选：参考文档
    │   └── guide.md
    ├── examples/             # ← 可选：示例代码
    │   └── demo.py
    └── assets/               # ← 可选：其他资源
        └── template.json
```

**资源文件夹会自动提示给 Agent**，无需手动配置。

---

## 📝 SKILL.md 格式

### 完整示例

```markdown
---
name: my-skill
description: 简短描述，Agent 会看到这个来决定是否加载（建议 < 100 字符）
---

# 技能标题

这里是详细的技能内容，只有 Agent 调用 Skill 工具时才会加载。

## 使用方法

详细说明如何使用这个技能...

## 示例

\`\`\`python
# 代码示例
print("Hello, Skills!")
\`\`\`

## 常见问题

- 问题 1：解决方案 1
- 问题 2：解决方案 2

## 最佳实践

1. 实践 1
2. 实践 2

$ARGUMENTS
```

### 字段说明

| 字段 | 必需 | 说明 |
|-----|------|------|
| `name` | ✅ | 技能名称，用于调用 `Skill(skill="name")` |
| `description` | ✅ | 简短描述，Agent 启动时会看到（建议 < 100 字符） |
| `$ARGUMENTS` | ⚪ | 占位符，会被替换为用户传入的参数 |

---

## 🎮 使用方式

### 方式 1：零配置（推荐）

```python
from hello_agents import ReActAgent, HelloAgentsLLM
from hello_agents.tools import ToolRegistry

# 只要 skills/ 目录存在，框架会自动激活
agent = ReActAgent(
    name="assistant",
    llm=HelloAgentsLLM(provider="openai", model="gpt-4"),
    tool_registry=ToolRegistry()
)

# Agent 会自动看到 Skill 工具并按需加载
result = agent.run("帮我处理 PDF 文件")
```

### 方式 2：自定义配置

```python
from hello_agents import Config

# 自定义 skills 目录
config = Config(
    skills_enabled=True,           # 是否启用（默认 True）
    skills_dir="my-custom-skills", # 自定义目录（默认 "skills"）
    skills_auto_register=True      # 自动注册工具（默认 True）
)

agent = ReActAgent(
    name="assistant",
    llm=llm,
    tool_registry=registry,
    config=config
)
```

### 方式 3：手动控制

```python
from hello_agents.skills import SkillLoader
from hello_agents.tools.builtin.skill_tool import SkillTool
from pathlib import Path

# 手动创建 SkillLoader
loader = SkillLoader(skills_dir=Path("skills"))

# 查看可用技能
print(loader.list_skills())        # ['pdf', 'code-review', 'mcp-builder']
print(loader.get_descriptions())   # 格式化的技能描述

# 手动注册到 Agent
skill_tool = SkillTool(skill_loader=loader)
registry.register_tool(skill_tool)

# 禁用自动注册
config = Config(skills_auto_register=False)
```

### 方式 4：禁用 Skills

```python
# 如果不想使用 Skills 系统
config = Config(skills_enabled=False)

agent = ReActAgent(
    name="assistant",
    llm=llm,
    config=config
)
```

---

## 💡 实际场景示例

### 场景 1：PDF 处理

**创建技能**：`skills/pdf/SKILL.md`

```markdown
---
name: pdf
description: Process PDF files. Use when reading, creating, or merging PDFs.
---

# PDF Processing Skill

## Reading PDFs
Use pdftotext: `pdftotext input.pdf -`

## Creating PDFs
Use pandoc: `pandoc input.md -o output.pdf`

$ARGUMENTS
```

**使用**：

```python
agent = ReActAgent(name="assistant", llm=llm, tool_registry=registry)

# Agent 会自动：
# 1. 看到 Skill 工具描述中提到 "pdf: Process PDF files..."
# 2. 判断需要加载 pdf 技能
# 3. 调用 Skill(skill="pdf")
# 4. 获得完整的 PDF 处理知识
# 5. 使用知识完成任务
result = agent.run("提取 report.pdf 的文本内容")
```

### 场景 2：代码审查

**创建技能**：`skills/code-review/SKILL.md`

```markdown
---
name: code-review
description: Perform systematic code reviews. Use when reviewing code quality, security, or best practices.
---

# Code Review Skill

## Security Checklist
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] Authentication checks

## Performance Checklist
- [ ] Database query optimization
- [ ] Caching strategy
- [ ] Resource cleanup

$ARGUMENTS
```

**使用**：

```python
result = agent.run("审查这段代码的安全性：\n\n```python\n...\n```")
# Agent 会加载 code-review 技能，获得安全检查清单
```

### 场景 3：MCP Server 开发

**创建技能**：`skills/mcp-builder/SKILL.md`（参考项目中的示例）

**使用**：

```python
result = agent.run("帮我创建一个 MCP server，提供文件搜索功能")
# Agent 会加载 mcp-builder 技能，获得完整的实现模板
```

---

## 🔧 高级功能

### 1. 参数替换

在 SKILL.md 中使用 `$ARGUMENTS` 占位符：

```markdown
---
name: template-skill
description: A skill with parameters
---

# Template Skill

User provided arguments:
$ARGUMENTS

Use these arguments to customize the behavior.
```

Agent 调用时传入参数：

```python
# Agent 内部会这样调用
Skill(skill="template-skill", args="custom parameters here")
```

### 2. 资源文件

在技能目录下创建资源文件夹：

```
skills/my-skill/
├── SKILL.md
├── scripts/
│   └── helper.py
├── references/
│   └── guide.md
└── examples/
    └── demo.py
```

Agent 加载技能时会自动看到：

```
✅ 技能已加载：my-skill

**可用资源**：
  - 脚本：helper.py
  - 参考文档：guide.md
  - 示例：demo.py
```

### 3. 热重载

```python
# 运行时重新扫描技能目录
agent.skill_loader.reload()
```

---

## 📊 性能优化

### Token 节省计算

假设有 20 个技能，每个技能 2000 tokens：

| 策略 | 启动 Token | 按需加载 | 总成本 |
|-----|-----------|-----------|--------|
| **全量加载** | 20 × 2000 = 40,000 | 0 | 40,000 |
| **渐进披露** | 20 × 100 = 2,000 | 2 × 2000 = 4,000 | **6,000** |
| **节省** | | | **85%** |

### 缓存友好设计

Skills 内容作为 `tool_result`（user message）注入，而非修改 `system_prompt`：

```python
# ❌ 错误：修改 system_prompt 会破坏缓存
system_prompt = f"{base_prompt}\n\n{skill.body}"  # 前缀变了，缓存失效

# ✅ 正确：作为 tool_result 追加
# Skill 内容作为 user message 追加到对话末尾
# 前缀不变，缓存命中率高
```

---

## ✅ 最佳实践

### 1. 技能命名

- ✅ 使用小写字母和连字符：`pdf-processing`
- ✅ 简短且描述性：`code-review`
- ❌ 避免空格和特殊字符：`PDF Processing!`

### 2. 描述编写

- ✅ 简短明确（< 100 字符）：`Process PDF files. Use when reading, creating, or merging PDFs.`
- ✅ 说明使用场景：`Use when...`
- ❌ 避免冗长描述：`This is a very comprehensive skill that can handle all kinds of PDF operations including but not limited to...`

### 3. 内容组织

- ✅ 使用清晰的标题结构
- ✅ 提供代码示例
- ✅ 列出常见问题和解决方案
- ✅ 包含最佳实践

### 4. 版本控制

```bash
# 将 skills/ 目录纳入版本控制
git add skills/
git commit -m "Add PDF processing skill"

# 团队成员拉取后立即生效
git pull
```

---

## 🐛 故障排查

### 问题 1：技能未被检测到

**症状**：Agent 看不到 Skill 工具

**检查**：
```python
# 运行检查脚本
python examples/check_skills_activation.py
```

**可能原因**：
- `skills/` 目录不存在
- SKILL.md 格式错误（缺少 frontmatter）
- `skills_enabled=False`

### 问题 2：技能加载失败

**症状**：Agent 调用 Skill 工具时返回错误

**检查**：
```python
from hello_agents.skills import SkillLoader
from pathlib import Path

loader = SkillLoader(skills_dir=Path("skills"))
skill = loader.get_skill("your-skill-name")

if skill is None:
    print("技能不存在或格式错误")
else:
    print(f"技能已加载：{skill.name}")
```

**可能原因**：
- SKILL.md 缺少必需字段（name/description）
- YAML frontmatter 格式错误
- 文件编码问题（应使用 UTF-8）

### 问题 3：Agent 不调用 Skill 工具

**症状**：Agent 没有加载技能就尝试完成任务

**原因**：
- 技能描述不够明确，Agent 判断不需要
- 任务描述与技能描述不匹配

**解决**：
- 优化技能描述，明确使用场景
- 在用户提示中明确提到需要使用技能

---

## 📚 示例技能库

项目中包含 3 个示例技能：

1. **pdf** - PDF 文件处理
2. **code-review** - 代码审查
3. **mcp-builder** - MCP Server 开发

查看 `skills/` 目录获取完整示例。

---

## 🎯 总结

**使用 Skills 系统只需三步**：

1. 创建 `skills/` 目录
2. 编写 `SKILL.md` 文件
3. 创建 Agent（自动激活）

**就这么简单！** 🎉

---

**相关文档**：
- [Skills 系统设计](../refine/07-skills-knowledge-externalization.md)
- [检查脚本](../../examples/check_skills_activation.py)
- [测试用例](../../tests/test_skills.py)

