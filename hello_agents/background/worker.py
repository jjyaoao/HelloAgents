"""带持久化租约和并发限制的异步工作器；处理函数仍是普通组件。"""

import asyncio
from contextlib import suppress
import inspect
from uuid import uuid4

from .queue import JobQueue, _positive
from .types import LeaseLost


class JobContext:
    def __init__(self, queue, lease):
        self.queue, self.lease = queue, lease
        self.job_id = lease.job.job_id
        self.attempt = lease.job.attempts
        self.idempotency_key = lease.job.idempotency_key or self.job_id

    def checkpoint(self):
        """提交外部操作前，检查协作式取消信号与任务持有权。"""
        self.queue.check(self.lease)

    @property
    def progress(self):
        return self.queue.check(self.lease).progress

    def report_progress(self, progress):
        self.queue.report_progress(self.lease, progress)


class JobWorker:
    def __init__(
        self,
        queue: JobQueue,
        handlers: dict,
        *,
        worker_id=None,
        concurrency=2,
        lease_seconds=30,
        poll_interval=0.2,
        retry_delay=1,
    ):
        if not handlers or any(
            not isinstance(k, str) or not k or not callable(v)
            for k, v in handlers.items()
        ):
            raise ValueError("handlers must map nonempty task names to callables")
        if type(concurrency) is not int or not 1 <= concurrency <= 64:
            raise ValueError("concurrency must be 1..64")
        for value, name in [
            (lease_seconds, "lease_seconds"),
            (poll_interval, "poll_interval"),
            (retry_delay, "retry_delay"),
        ]:
            _positive(value, name)
        self.queue, self.handlers = queue, dict(handlers)
        self.worker_id = worker_id or uuid4().hex
        self.concurrency, self.lease_seconds = concurrency, lease_seconds
        self.poll_interval, self.retry_delay = poll_interval, retry_delay

    async def _invoke(self, handler, payload, context):
        if inspect.iscoroutinefunction(handler) or inspect.iscoroutinefunction(
            getattr(handler, "__call__", None)
        ):
            return await handler(payload, context)
        result = await asyncio.to_thread(handler, payload, context)
        return await result if inspect.isawaitable(result) else result

    async def _renew(self, lease):
        while True:
            await asyncio.sleep(self.lease_seconds / 3)
            await asyncio.to_thread(
                self.queue.heartbeat, lease, lease_seconds=self.lease_seconds
            )

    async def run_once(self):
        lease = await asyncio.to_thread(
            self.queue.claim,
            self.worker_id,
            lease_seconds=self.lease_seconds,
            tasks=tuple(self.handlers),
        )
        if lease is None:
            return False
        context = JobContext(self.queue, lease)
        work = asyncio.create_task(
            self._invoke(self.handlers[lease.job.task], lease.job.payload, context)
        )
        renew = asyncio.create_task(self._renew(lease))
        try:
            done, _ = await asyncio.wait(
                {work, renew}, return_when=asyncio.FIRST_COMPLETED
            )
            if renew in done:
                # 续期失败即视为失去持有权，不能将失败的数据库写入当作续期成功。
                await renew
            result = await work
            await asyncio.to_thread(self.queue.complete, lease, result)
        except LeaseLost:
            pass
        except asyncio.CancelledError:
            # 等待租约自然到期；取消等待后，线程中的操作可能仍在执行。
            raise
        except Exception as exc:
            with suppress(LeaseLost):
                await asyncio.to_thread(
                    self.queue.fail,
                    lease,
                    f"{type(exc).__name__}: {exc}",
                    retry_delay=min(
                        self.retry_delay * 2 ** (lease.job.attempts - 1), 3600
                    ),
                )
        finally:
            work.cancel()
            renew.cancel()
            await asyncio.gather(work, renew, return_exceptions=True)
        return True

    async def run(self, stop: asyncio.Event):
        """事件置位后停止领取任务，让已领取的任务正常执行完毕。"""

        async def slot():
            while not stop.is_set():
                if not await self.run_once():
                    try:
                        await asyncio.wait_for(stop.wait(), timeout=self.poll_interval)
                    except asyncio.TimeoutError:
                        pass

        tasks = [asyncio.create_task(slot()) for _ in range(self.concurrency)]
        try:
            await asyncio.gather(*tasks)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
