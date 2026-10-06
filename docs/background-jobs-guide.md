# 后台任务与恢复

文档抽取、图索引和记忆向量同步可能持续数分钟。`JobQueue` 把任务保存到 SQLite，`JobWorker` 从宿主注册的处理函数中执行任务，记录进度、结果和失败信息。提交任务后可以退出进程，之后启动 worker 继续处理。

## 📚 目录

- [快速开始](#快速开始)
- [进度与恢复](#进度与恢复)
- [索引与记忆任务](#索引与记忆任务)
- [并发与取消](#并发与取消)
- [API 参考](#api-参考)
- [边界与部署](#边界与部署)
- [接入应用的完整顺序](#接入应用的完整顺序)
- [常见问题](#常见问题)

## 快速开始

基础安装即可使用，无需消息服务或额外依赖：

```bash
python -m pip install -r requirements.txt
python -X utf8 -m examples.runtime.background_jobs_demo --workspace workspace/jobs-demo
```

案例把三份旅行规则导入 `RAGStore`，在第一份写入后注入一次异常。重试时读取保存的进度，完成其余导入。查看 `background-report.json`：`status` 为 `succeeded`，`attempts` 为 `2`，`progress.imported` 为 `3`。再次运行相同目录会读回同一个任务，不重复导入。

```python
import asyncio
from hello_agents.background import JobQueue, JobWorker

queue = JobQueue("workspace/jobs.sqlite", namespace="travel")
job = queue.submit("index_rules", {"dataset": "approved-rules-v1"},
                   idempotency_key="approved-rules-v1", max_attempts=3)

def index_rules(payload, context):
    context.report_progress({"stage": "reading"})
    # 用宿主已验证的资料标识读取内容，并调用实际索引组件。
    context.checkpoint()
    return {"dataset": payload["dataset"], "indexed": True}

worker = JobWorker(queue, {"index_rules": index_rules}, concurrency=1)
asyncio.run(worker.run_once())
print(queue.get(job.job_id).status)
```

这个最小片段说明调度接口；实际文档导入见前面的完整案例。任务载荷只保存 JSON 数据，处理函数由 worker 注册，不从载荷反序列化代码，也不让模型指定导入路径或可执行函数。

## 进度与恢复

任务依次经过 `queued`、`running`，最终为 `succeeded`、`failed` 或 `cancelled`。worker 领取时获得一段租约，运行期间自动续租。进程异常退出后，其他 worker 在租约到期后可以重新领取；每次领取都消耗一次尝试额度。

`context.report_progress({...})` 保存阶段或游标，重试时通过 `context.progress` 读取。进度并不会自动恢复 Python 调用栈；处理函数必须根据游标恢复，并使重复写入安全。案例用稳定的文档 ID、版本和内容实现幂等导入，即使进程在“写入文档”与“保存进度”之间退出，重试也不会增加重复版本。

失败后按 `retry_delay × 2^(attempt - 1)` 延迟重试，上限一小时。达到 `max_attempts` 后进入 `failed`。保存的 `error` 最多 2000 个字符。超时或取消不应被写成业务成功；应用应检查状态及结果。

相同 namespace 下，相同幂等键和相同任务载荷返回原任务；相同键配不同任务或载荷会抛 `JobConflict`。已失败或已取消的任务也不会被同一个键自动重启，需要宿主明确提交新键。

## 索引与记忆任务

处理函数直接调用组件，不需要再创建一层 Agent：

```python
def build_graph(payload, context):
    context.report_progress({"stage": "graph_build"})
    report = graph_index.build(checkpoint=context.checkpoint)
    return report.to_dict()

def sync_memories(payload, context):
    context.report_progress({"stage": "embedding"})
    count = semantic_memory.sync(checkpoint=context.checkpoint)
    return {"encoded": count}
```

这里的 `graph_index` 和 `semantic_memory` 是宿主创建、绑定资料范围的实例，分别见 [GraphRAG](graphrag-guide.md) 与 [记忆语义检索](semantic-memory-guide.md)。模型和数据库凭据留在宿主配置中，不放进任务载荷。`checkpoint` 在阶段之间检测取消或租约失效，避免已经失去执行权的任务继续昂贵操作。图构建还会缓存已经通过校验的抽取与社区报告，重试可复用它们。

完整组合案例：

```bash
python -X utf8 -m examples.memory.semantic_memory_demo --help
```

该案例通过后台任务同步真实向量索引，修订用户偏好后重新同步，并可用 `--live` 让模型通过 Function Calling 读取当前记忆。

## 并发与取消

持续运行 worker 时传入一个停止事件：

```python
async def serve(stop):
    worker = JobWorker(queue, {"index_rules": index_rules}, concurrency=2,
                       lease_seconds=30, poll_interval=0.2)
    await worker.run(stop)
```

设置 `stop.set()` 后不再领取新任务，已领取任务正常完成。直接取消 `run()` 则中止异步等待，未完成任务保留到租约过期后恢复。`queue.cancel(job_id)` 撤销队列内的执行权；旧 worker 不能写入结果或进度。

同步处理函数在线程中执行，Python 无法强制终止已经运行的线程；外部 HTTP 请求也可能已经发生。因此，取消是协作式的，长任务应在阶段间调用 `checkpoint()`。队列保证旧租约不能覆盖任务记录，不保证跨数据库或外部服务的“恰好一次”。外部写操作仍需使用幂等键、版本条件或目标系统自己的事务。

## API 参考

```python
JobQueue(path, namespace="default", max_payload_bytes=1048576)
queue.submit(task, payload, idempotency_key=None, max_attempts=3, delay=0)
queue.get(job_id)
queue.list(status=None, limit=20)
queue.cancel(job_id)

JobWorker(queue, handlers, concurrency=2, lease_seconds=30,
          poll_interval=0.2, retry_delay=1)
await worker.run_once()  # 是否领取了一个任务；业务结果读取 queue.get()
await worker.run(stop)

context.job_id
context.attempt
context.idempotency_key
context.progress
context.report_progress(json_value)
context.checkpoint()
```

`payload` 必须是 JSON 对象；结果与进度可为 JSON 值。默认各限制为 1 MiB，大文件应保存为外部产物，只传受信任的标识。`Job` 是某次读取的快照，`to_dict()` 提供序列化字典；查看新状态要再次调用 `get()`。`claim/heartbeat/complete/fail` 是自定义 worker 的底层接口，所有更新都会校验当前租约。

## 边界与部署

SQLite 队列适合单机多进程；使用本地磁盘文件。跨机器部署和大规模调度应替换独立任务后端。namespace 是隔离键，不替代宿主认证。访问控制、凭据保管和日志保留由应用负责。

同一 Qdrant 索引只安排一个写入者；本地 Qdrant 目录也不能由多个进程同时打开。同步使用新代次，全部写完才发布，失败代次不会参与检索；它不具备跨进程分布式锁。后台租约与 Qdrant 的发布操作不是同一事务，`checkpoint()` 不能替代索引端的原子条件更新。GraphRAG 的 SQLite 发布使用版本比较，竞争构建不会静默覆盖已经发布的新代次。

当前提供持久化队列、租约、重试、取消和进度恢复。没有 Cron、团队协作或 Worktree 生命周期管理。

## 接入应用的完整顺序

Web 请求或前台程序先通过 `submit()` 保存任务，向调用者返回 job_id；worker 独立启动并注册可信的处理函数。前台通过 `get()` 查询新状态和进度。不要在提交后直接显示“索引完成”，只有 succeeded 和处理结果才能说明这次处理结束。

资料同步类任务应把数据集标识或修订号写入幂等键。同一修订重复提交返回原任务；资料已经变化时使用新键。处理函数先读取持久进度，再执行下一批操作，保存进度并检查取消。输入文件、业务数据库与外部服务的写入仍需各自实现可重试语义。

## 常见问题

**提交之后为什么一直 queued？**

Queue 只存任务，不自动启动执行线程。需要启动注册了对应任务名的 JobWorker，并使它连接同一数据库与 namespace。

**进程崩溃后会从刚才那一行继续吗？**

不会。租约到期后任务重新进入处理函数，函数根据持久 progress 决定继续位置。未保存的局部变量无法恢复。

**cancelled 后，外部服务为什么仍有写入？**

取消撤销任务的队列执行权，无法强制撤回已经发送的请求。长任务在阶段之间检查取消，修改型请求使用幂等和结果核对。
