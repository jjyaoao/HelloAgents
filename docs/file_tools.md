# 文件工具：读取、写入与顺序编辑

文件工具提供 `Read`、`Write`、`Edit`、`MultiEdit`。它们返回 `ToolResponse`，可单独使用，也可注册到 Agent。编辑工具通过唯一匹配和写入前检查减少误改；宿主仍需负责访问范围和授权。

## 📚 目录

- [最小示例](#最小示例)
- [参数与结果](#参数与结果)
- [用法选择：先读，再改，再回读](#用法选择先读再改再回读)
- [边界](#边界)
- [常见问题](#常见问题)

## 最小示例

下面只操作独立临时目录，不调用模型。

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from hello_agents import ToolRegistry
from hello_agents.tools.builtin import ReadTool, WriteTool, EditTool, MultiEditTool
from hello_agents.tools.response import ToolStatus

with TemporaryDirectory() as directory:
    registry = ToolRegistry()
    for cls in (ReadTool, WriteTool, EditTool, MultiEditTool):
        registry.register_tool(cls(project_root=directory, registry=registry))
    assert registry.execute_tool("Write", {"path": "plan.txt", "content": "湖边散步"}).status == ToolStatus.SUCCESS
    assert registry.execute_tool("Read", {"path": "plan.txt"}).status == ToolStatus.SUCCESS
    result = registry.execute_tool("MultiEdit", {
        "path": "plan.txt",
        "edits": [
            {"old_string": "湖边", "new_string": "博物馆附近"},
            {"old_string": "博物馆附近散步", "new_string": "博物馆参观"},
        ],
    })
    assert result.status == ToolStatus.SUCCESS
    assert (Path(directory) / "plan.txt").read_text(encoding="utf-8") == "博物馆参观"
    print(result.to_dict())
```

第二项编辑使用第一项编辑后的内容。所有编辑先在内存副本上按顺序校验，全部通过后再写文件；任一项没有唯一匹配就返回错误，不写入部分结果。

## 参数与结果

`Read` 接收 `path`、可选 `offset` 和 `limit`，按行读取；目录路径返回目录内容。`Write` 接收 `path`、`content`，会创建缺失的父目录。`Edit` 接收 `path`、`old_string`、`new_string`；原字符串必须非空且恰好出现一次。`MultiEdit` 接收相同结构的 `edits` 数组。

读工具关联注册表后会缓存文件元数据。写入、编辑可使用缓存或显式 `file_mtime_ms` 检查读取后是否被修改。冲突返回 `CONFLICT`，应重新读取并重新决定修改，不能盲目重试旧替换。

覆盖已有内容前会保存备份，返回数据包含备份路径。写入使用独占创建的同目录临时文件，完成后替换目标文件；失败清理只针对本次临时文件。

## 用法选择：先读，再改，再回读

`Write` 适合创建新文件或在明确知道完整内容时整体替换；`Edit` 适合替换一处准确片段；`MultiEdit` 适合同一文件中有先后关系的多处替换。不要为了替换一句话，先让模型重写整个文件。

对已有文件，先通过同一注册表的 `Read` 获取内容和元数据，再选择修改方式。执行后回读，检查最终内容与工具回执是否一致。下面演示唯一匹配检查：

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from hello_agents import ToolRegistry
from hello_agents.tools.builtin import ReadTool, EditTool
from hello_agents.tools.response import ToolStatus

with TemporaryDirectory() as directory:
    path = Path(directory) / "plan.txt"
    path.write_text("上午参观博物馆\n下午参观博物馆\n", encoding="utf-8")
    registry = ToolRegistry()
    registry.register_tool(ReadTool(project_root=directory, registry=registry))
    registry.register_tool(EditTool(project_root=directory, registry=registry))
    registry.execute_tool("Read", {"path": "plan.txt"})
    rejected = registry.execute_tool("Edit", {
        "path": "plan.txt", "old_string": "参观博物馆", "new_string": "湖边散步",
    })
    assert rejected.status == ToolStatus.ERROR
    assert path.read_text(encoding="utf-8").count("参观博物馆") == 2
    changed = registry.execute_tool("Edit", {
        "path": "plan.txt", "old_string": "下午参观博物馆", "new_string": "下午湖边散步",
    })
    assert changed.status == ToolStatus.SUCCESS
    assert "下午湖边散步" in path.read_text(encoding="utf-8")
    print(registry.execute_tool("Read", {"path": "plan.txt"}).text)
```

第一次替换无法区分两处相同文本，因此没有写入；第二次增加“下午”作为定位条件，才修改目标位置。匹配失败时应补足上下文，而不是把错误吞掉后继续执行下一项修改。

### 处理并发修改

收到 `CONFLICT` 后，重新读取文件，比较另一位写者的改动，再生成新替换。旧请求基于旧内容，即使工具名和参数格式都正确，也可能已经不适用。对于需要多个写者协作的系统，还应在宿主增加锁或事务机制。

## 边界

`project_root` 与 `working_dir` 决定路径解析位置，不是访问沙箱；绝对路径及目录外路径需要宿主另行限制。读取缓存按调用路径记录，应用应统一路径表达。

修改时间采用毫秒精度，不能识别同一毫秒内且时间戳未变化的改写；检查与最终写入之间也仍有时间窗口，不能宣称跨进程比较交换或多写者事务。批量编辑的完整性只覆盖一次调用，不覆盖多个文件。备份、工具回执和会话恢复均不等于自动撤销外部操作。

相关指南：[工具返回协议](tool-response-protocol.md)、[自定义工具](custom_tools_guide.md)。

## 常见问题

**为什么 Edit 找到了内容，仍然拒绝修改？**

原字符串必须只出现一次。读取相关行，扩大替换片段以便准确定位；同时检查读取后是否发生文件修改。

**一次 MultiEdit 中，第二项能使用第一项生成的内容吗？**

可以，按数组顺序在内存中执行。任一项校验失败，本次批量修改都不落盘。它只处理一个文件，多文件操作需要宿主组织。

**工具保存备份后会自动回滚吗？**

不会。备份提供恢复材料；选择是否恢复、恢复哪个版本仍由宿主决定。
