# 运行可靠性与验收

## 模型配置与生命周期

应用显式加载自己的 `.env`。模型名从配置读取；使用代理地址时，可以显式指定协议。

```python
from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM

load_dotenv()
with HelloAgentsLLM(provider="openai", top_p=0.9) as llm:
    result = llm.invoke([{"role": "user", "content": "你好"}], top_p=0.8)
    print(result.content)
```

`provider` 使用 `openai`、`anthropic`、`gemini`。不指定时按服务主机名判断。构造函数的额外参数作为调用默认值，单次调用覆盖它们；参数必须属于所选服务 SDK 支持的协议，未知字段由 SDK 拒绝。Gemini 的服务地址与超时会传入 SDK，不再被忽略。

同步代码使用 `with` / `close()`，异步代码使用 `async with` / `await aclose()`。Agent 不关闭宿主传入的模型，宿主应在所有共享使用者结束后统一关闭。关闭后不能再调用，重复关闭无副作用。正在执行的同步 SDK 请求不能靠 Python 协程取消而强制终止，仍受 SDK 超时约束；后备流取消后停止继续拉取，缓冲有界。

智能摘要默认沿用主模型。需要独立模型时，通过 `AgentComponents(summary_llm=summary, subagent_llm=small)` 注入已经配置好的完整实例，由宿主管理其生命周期。不要只填写另一家服务的模型名而沿用当前密钥与地址。

## 整次任务的预算

```python
from hello_agents import RunBudget, BudgetExceeded

budget = RunBudget(max_calls=12, max_tokens=20000, max_seconds=120)
try:
    with budget.scope():
        answer = agent.run("完成旅行规划")
except BudgetExceeded:
    print("预算已用尽，请检查已保存的结果")
print(budget.snapshot())
```

作用域内的 `HelloAgentsLLM` 调用共享预算，包括摘要、子代理和 GraphRAG 模型适配器。`asyncio.to_thread` 会传递该作用域；自行启动线程或后台进程时，应显式把同一预算对象注入进程内的模型，或由宿主提供跨进程计量，不能假设 ContextVar 会自动跨进程传播。也可以向多个 LLM 实例传入同一个 `budget=`。外部自定义 LLM 不自动受此计量控制。

调用数限制按逻辑调用在请求前原子检查，SDK 内部重试不是独立计数。token 在响应后才取得，因此最后一个已获准请求可能使总量超过限制；并发已获准请求也可能继续返回。缺失 usage 时记录为未知，后续 token 受限调用停止。时间在请求前和收到输出时检查，不保证立即终止已经阻塞的远程操作。预算不是账单硬上限，也不输出未经配置的费用估算。

## Trace 输出

HTML 对动态文本进行转义。默认递归处理常见敏感键和令牌形式；应用可通过 `TraceLogger(sanitizer=...)` 添加个人信息处理。自定义函数接收已完成基础脱敏的事件并返回事件。

`html_include_raw_response=False` 隐藏 HTML 中的 `raw_response` 字段；JSONL 保留经脱敏的原始事件，便于排查。若不能保存某类内容，必须在 sanitizer 中删除它，而不能只关闭 HTML 展示。自动脱敏不是隐私识别器，日志目录权限、保留期和备份由应用负责。

## 数据维护

SQLite 存储记录各组件的 schema 版本，旧的已知结构登记为 v1；未知版本会拒绝读取。`backup_database(source, destination)` 使用 SQLite 一致性备份，目标必须是新文件。恢复时停止使用该库，先验证备份再由宿主替换，避免与活动连接或 WAL 混用。

```python
from hello_agents.storage import backup_database

backup_database("memory.db", "backups/memory-before-maintenance.db")
records = memory.export_records()  # 当前 user_id / task_id 范围，包括撤回历史
memory.purge(expected_revision=memory.revision)
```

`MemoryStore.purge` 删除当前用户/任务的记录并提升修订号；`ProfileStore.purge_history` 删除画像内容与历史，只留下空的版本屏障，旧写请求不能重新覆盖。`export_history` 导出画像的全部历史。它们是数据库行删除，不是磁盘安全擦除；备份、模型服务记录和消息历史仍需分别处理。

删除后同步或调用 `QdrantSearch.purge_namespace()` 清理当前资料库的派生向量。此操作只删除当前 namespace 的向量与清单，不删除规范库；维护期间停止所有相关写入者。GraphStorage 的 `prune(clear_cache=True)` 清理非活动数据库代次及缓存，保留活动代次；外部资产与备份另行维护。删除流程不是跨 SQLite 与 Qdrant 的分布式事务，应用必须记录每一步并对失败步骤重试。

`migrate_database(path, component, target, migrations)` 提供事务化版本迁移入口，迁移失败会回滚；迁移前先备份。回调是可信的宿主代码，只使用 `execute` / `executemany`，不可提交事务或使用 `executescript`。应用画像 schema 的字段转换需要显式编写，框架不会猜测字段含义。当前运行组件声明的是 v1，不应随意升级数据库版本后继续用旧代码读取。

## 验收层次

基础 CI 验证锁文件、导出清单、测试与独立发行包安装。真实提供商调用须显式启用 `--run-live`；远程部署、负载、应用鉴权、隔离和数据保留还需在部署环境验收。本地用例通过不代表这些环境已经通过。

```bash
python scripts/sync_requirements.py --check
python scripts/check_distribution.py
python -m pytest
```

维护者可使用独立的 `quality` 依赖组运行发布检查；这组工具不会安装到框架运行依赖中：

```bash
uv sync --locked --all-extras --group quality
uv run --locked --all-extras --group quality ruff check hello_agents tests examples scripts
uv run --locked --all-extras --group quality coverage run -m pytest
uv run --locked --all-extras --group quality coverage report
uv run --locked --all-extras --group quality python scripts/check_security.py
uv run --locked --all-extras --group quality python scripts/check_concurrency.py --jobs 2000 --workers 8
```

静态检查覆盖语法、未定义名称等确定性错误。覆盖率同时统计分支，当前门槛为 82%；它用于发现回归覆盖下降，不能代替断言质量。安全扫描基于已公开漏洞，服务不可用也会失败；本地开发快照自身不冒用公开同名包的安全记录。并发检查使用真实 SQLite 和多个进程，包含一次未确认任务的进程退出及恢复、提交幂等和命名空间隔离；输出记录规模和耗时，不将本机数据承诺为部署容量。参考 [pip-audit 官方说明](https://github.com/pypa/pip-audit)。

协议参考：[Anthropic 工具选择](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools)。不同模型可能限制强制调用选项，框架传递协议字段，不替远程模型承诺支持情况。

## 模型工具选择的差异

PlanSolve 默认使用 `auto`，在提示中要求模型提交 `generate_plan`，并严格检查返回的计划；未返回正确工具或步骤时停止，不能把普通文本当成已经验证的计划。不会私自关闭模型思考模式。`required` 和指定工具仍按调用者要求传给服务，但不保证所有模型模式都支持。OpenAI 兼容服务实际返回的 `reasoning_content` 会保留在消息历史并回传，流式公开文本不输出该字段。消息持久化可能包含这些服务字段，应按会话数据管理。参考 [DeepSeek 工具选择限制](https://api-docs.deepseek.com/api/create-chat-completion/)。
