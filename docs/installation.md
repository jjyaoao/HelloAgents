# 安装与依赖管理

推荐使用 64 位 Python 3.13，也支持 Python 3.12，框架与教程配套范围一致（`>=3.12,<3.14`）。3.12 首次加载框架时显示推荐提示，程序继续执行；`.python-version` 使用推荐的 3.13。在框架源码根目录执行下面的命令；安装时仍需可用的第三方平台轮子，版本声明不代表所有操作系统均已验收。

## 基础安装

使用 [uv 官方安装方式](https://docs.astral.sh/uv/getting-started/installation/)准备 uv。本仓库维护工具使用 `uv==0.12.23`，允许范围写在 `pyproject.toml` 的 `tool.uv.required-version`。

```bash
uv sync --locked
uv run --locked python -X utf8 -m examples.agents.async_agent_demo
```

`--locked` 要求项目声明与锁文件一致；不一致时停止，不自行升级依赖。

不使用 uv 时，创建虚拟环境并激活，再通过 pip 安装：

```bash
python -m venv .venv
# Windows PowerShell: .venv/Scripts/Activate.ps1
# macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -X utf8 -m examples.agents.async_agent_demo
```

requirements 文件已包含 `-e .`，会安装当前源码及固定版本的依赖，不需要再次安装 PyPI 包。命令必须从仓库根目录执行，即使清单位于 `requirements/`。同一虚拟环境选择一种工具维护；不要交替执行 uv 精确同步与 pip 临时加包。

## 按功能安装

基础循环、SQLite 检索、结构化记忆、用户画像和后台队列不需要额外数据库依赖。其他功能按需选择；下面每行是 uv 与 pip 的对应方式，不要求依次全部执行。

| 功能 | uv | pip |
| --- | --- | --- |
| MCP | `uv sync --locked --extra mcp` | `python -m pip install -r requirements/mcp.txt` |
| Qdrant | `uv sync --locked --extra qdrant` | `python -m pip install -r requirements/qdrant.txt` |
| 本地嵌入及 Qdrant | `uv sync --locked --extra fastembed` | `python -m pip install -r requirements/fastembed.txt` |
| GraphRAG | `uv sync --locked --extra graphrag` | `python -m pip install -r requirements/graphrag.txt` |
| Anthropic | `uv sync --locked --extra anthropic` | `python -m pip install -r requirements/anthropic.txt` |
| Gemini | `uv sync --locked --extra gemini` | `python -m pip install -r requirements/gemini.txt` |
| Web / SSE | `uv sync --locked --extra web` | `python -m pip install -r requirements/web.txt` |
| 测试 | `uv sync --locked --extra test` | `python -m pip install -r requirements/test.txt` |

同时使用 MCP 和 GraphRAG 时，uv 使用 `--extra mcp --extra graphrag`，pip 使用 `-r requirements/mcp.txt -r requirements/graphrag.txt`。需要保留的 extras 应在每次 uv 同步或运行时一起指定，例如：

```bash
uv run --locked --extra mcp python -X utf8 -m examples.tools.mcp_agent_demo
```

开发验收全部组件时使用 `uv sync --locked --all-extras`，或 `python -m pip install -r requirements/all.txt`。它们会安装额外 SDK 和本地计算依赖，基础使用不必选择全部组件。本地嵌入模型权重、API 模型与远程服务不属于 Python 锁文件的锁定范围。

## 版本范围和锁定结果

`pyproject.toml` 是直接依赖的唯一声明来源。核心、可选 SDK、测试和构建依赖都具有下限与上限；SDK 及变化较快的依赖先限定在选定的小版本系列。例如 `qdrant-client>=1.19.1,<1.20`，需要支持下一个系列时再测试并放宽。

`uv.lock` 固定直接与间接依赖；同一包在不同 Python 或平台上可能具有不同版本，导出的 requirements 保留这些环境条件。版本上下限控制允许范围，锁文件固定这次选择，两者不能相互替代。

`requirements.txt` 是基础安装，`requirements/<extra>.txt` 是基础加对应组件，`requirements/all.txt` 是全部组件；全部由同一锁文件生成。不要手动修改这些导出文件。pip 清单固定运行依赖版本；构建隔离环境的工具范围由 `build-system.requires` 限制，不属于 uv 的运行依赖锁。

只执行 `pip install -e .` 仍会按声明范围解析，适合依赖集成测试，但不保证与仓库锁文件逐项相同。教程与复现使用前面的锁定安装方式。已安装环境也不会因清单变化自动更新，需要重新安装或同步。

## 更新与检查

维护时先修改 `pyproject.toml`，随后在独立环境执行：

```bash
# 重新解析声明；指定 --upgrade-package 只升级一个包。
uv lock
# uv lock --upgrade-package qdrant-client
python scripts/sync_requirements.py
uv lock --check
python scripts/sync_requirements.py --check
uv sync --locked --all-extras
uv pip check
uv run --locked --all-extras python -m pytest
```

检查脚本逐份比较 uv 导出内容，发现未更新的清单即失败。依赖测试检查直接依赖边界、导出版本与锁文件是否一致。CI 还从 requirements 在独立 pip 环境中安装并运行测试，避免只验收 uv 路径。

需要升级整个依赖集合时才使用 `uv lock --upgrade`。把 `pyproject.toml`、`uv.lock` 和全部 requirements 导出一起提交；同时检查相关组件案例、SDK 请求协议和安装结果。锁定可以减少未经验证的更新，不能保证远程 API 或模型长期不变。

机制说明参见 [uv 锁定与同步](https://docs.astral.sh/uv/concepts/projects/sync/)及[锁文件导出](https://docs.astral.sh/uv/concepts/projects/export/)。
