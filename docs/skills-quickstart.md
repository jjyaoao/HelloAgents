# Agent Skill 快速开始

Agent Skill 将某类任务的操作说明放在 `SKILL.md` 中。加载器先读取名称与用途，模型需要时再通过 `Skill` 工具取得正文。这里演示文件加载，不调用模型。

## 创建并加载

从源码根目录安装 `python -m pip install -r requirements.txt`，执行：

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from hello_agents.skills import SkillLoader
from hello_agents.tools.builtin import SkillTool
from hello_agents.tools.response import ToolStatus

with TemporaryDirectory() as directory:
    skill_dir = Path(directory) / "travel-check"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: travel-check\ndescription: 核对旅行计划的预约与步行约束\n---\n"
        "先核对 $ARGUMENTS 的预约要求，再计算各日步行距离。\n",
        encoding="utf-8",
    )
    loader = SkillLoader(Path(directory))
    assert loader.list_skills() == ["travel-check"]
    assert "核对旅行计划" in loader.get_descriptions()
    tool = SkillTool(loader)
    reply = tool.run({"skill": "travel-check", "args": "博物馆"})
    assert reply.status == ToolStatus.SUCCESS
    assert "博物馆" in reply.text
    print(reply.text)
```

结果包含完整说明及可用资源提示。`$ARGUMENTS` 是文本替换位置；它不会执行命令。生产应用应把 Skill 放在持久目录，再将 `SkillTool(loader)` 注册到代理的工具注册表。

## 下一步

阅读 [Skills 使用指南](skills-usage-guide.md) 了解目录、刷新与组合方式；阅读 [组件组合](component-composition-guide.md) 将加载器注入 Agent。完整离线运行示例使用 `python -X utf8 -m examples.agents.runtime_features`。
