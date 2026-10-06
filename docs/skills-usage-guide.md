# Agent Skill：按需提供任务说明

当工具只说明“能调用什么”，但某类任务还需要步骤、检查项或领域约定时，可用 Agent Skill 补充操作说明。Skill 本身不是执行器；其中涉及的读写、命令或网络操作仍由已注册工具完成。

## 📚 目录

- [文件组织](#文件组织)
- [完整示例：从说明文件到工具回执](#完整示例从说明文件到工具回执)
- [加载与刷新](#加载与刷新)
- [与 Agent 组合](#与-agent-组合)
- [适用边界](#适用边界)
- [常见问题](#常见问题)

## 文件组织

```text
skills/
  travel-check/
    SKILL.md
    references/
    examples/
    scripts/
    assets/
```

`SKILL.md` 开头使用 YAML frontmatter，必须提供非空字符串 `name` 与 `description`。正文说明具体步骤；资源文件存放在相应子目录。先运行 [快速开始](skills-quickstart.md) 中的完整例子，确认名称、用途和正文都能读取。

描述应让模型判断何时需要该 Skill，正文再交代步骤和完成条件。不要把所有参考文档直接塞进描述，也不要把无关的当前任务写成通用步骤。

## 完整示例：从说明文件到工具回执

下面创建一份临时 Skill，先查看用途，再通过注册表加载正文。整个过程无需模型，适合先检查文件格式与资源路径。

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from hello_agents import ToolRegistry
from hello_agents.skills import SkillLoader
from hello_agents.tools.builtin import SkillTool
from hello_agents.tools.response import ToolStatus

with TemporaryDirectory() as directory:
    folder = Path(directory) / "travel-check"
    folder.mkdir()
    (folder / "SKILL.md").write_text(
        "---\nname: travel-check\ndescription: 核对旅行路线的预约条件与步行限制\n---\n"
        "先读取预约依据，再核对步行距离。当前对象：$ARGUMENTS。\n",
        encoding="utf-8",
    )
    loader = SkillLoader(directory)
    print(loader.get_descriptions())
    registry = ToolRegistry()
    registry.register_tool(SkillTool(loader))
    result = registry.execute_tool("Skill", {"skill": "travel-check", "args": "杭州两日游"})
    assert result.status == ToolStatus.SUCCESS
    assert "杭州两日游" in result.text
    assert "$ARGUMENTS" not in result.text
    print(result.text)
```

用途说明帮助选择，正文交代执行步骤，工具回执将本次加载内容送回循环。这个例子只加载文本，没有读取预约网页或调用搜索；要执行这些步骤，还需把对应工具注册给 Agent。

### 写一份容易采用的 Skill

描述说明适用任务，例如“核对旅行路线的预约条件与步行限制”；正文按执行顺序列出操作，并给出完成条件，例如“所有预约要求都能回到来源，未知条件明确列出”。较长的规则放在 `references/`，正文标明何时读取。

固定流程可以写在 Skill 中，用户本次的日期、预算和目的地放在任务输入。频繁变化的真实政策由检索工具取得，不适合永久写成 Skill 的事实前提。

## 加载与刷新

`SkillLoader(skills_dir)` 扫描目录，`list_skills()` 返回名称，`get_descriptions()` 返回用途说明，`get_skill(name)` 按需返回 `Skill`。不存在的名称返回 `None`。

`Skill` 包含 `name`、`description`、`body`、`path`、`dir`，以及 `scripts`、`references`、`examples` 文件列表。无效元数据会进入 `loader.diagnostics`，不会阻止其他有效 Skill 加载。重名时采用扫描顺序中第一个有效条目并记录诊断。

修改文件后调用 `loader.reload()`，重新建立元数据与正文缓存。更新工具中展示的能力目录时，应同时重新创建 `SkillTool(loader)` 并通过 `registry.register_tool(tool, replace=True)` 替换注册项。

## 与 Agent 组合

有两种明确装配方式：应用自行注册 `SkillTool(loader)`；或在配置中启用 Skills，并通过 `AgentComponents(skill_loader=loader)` 注入加载器。后一种方式的自动注册还受 `skills_auto_register` 控制，代理必须有工具注册表。见 [组件组合](component-composition-guide.md)。

模型调用 `Skill` 时提交 `skill` 和可选字符串 `args`。工具返回正文，并把 `$ARGUMENTS` 替换为 `args`。正文以工具回执进入对话，不会自动变成系统级指令。模型是否选择加载取决于输入、描述与模型行为，不能保证仅凭描述就一定加载。

## 适用边界

资源提示只列出文件，不执行脚本，也不自动把全部参考资料放进上下文。应用需提供读取资源或执行操作的工具。Skill 不能绕过工具权限或授予文件访问能力。

按需加载可以减少每轮直接携带的正文，但实际 Token、缓存命中和质量需要测量。工具返回的 `token_estimate` 当前是文本长度，不是供应商 Token 计量，不能用于账单估算。

Skills 适合可复用步骤；用户偏好和会话事实应进入 [记忆组件](memory-guide.md)，大量可检索资料应进入 [RAG 组件](rag-guide.md)。

## 常见问题

**修改 SKILL.md 后，模型为什么仍看到旧描述？**

先 `loader.reload()`，再用新加载器内容创建并替换 SkillTool。只更新磁盘文件，不会自动替换已经注册的工具描述。

**加载成功，就说明模型采用了流程吗？**

还不能这样判断。检查后续工具请求和最终产物，例如是否实际回读了预约规则。加载回执只证明说明已进入消息。

**Skill 中写了执行脚本，框架会自动执行吗？**

不会。资源文件是线索，宿主仍需提供读取或执行工具，并设置相应权限。Skill 文本不能自行获得执行权。
