"""模型调用、摘要和子任务共享的线程安全预算准入控制。"""
from contextvars import ContextVar
from contextlib import contextmanager
import math
from threading import Lock
from time import monotonic
from functools import wraps

_current = ContextVar('helloagents_budget', default=None)


class BudgetExceeded(RuntimeError):
    pass


class RunBudget:
    """限制逻辑调用次数与已报告的 Token 用量，不保证远端计费上限。

    Token 用量在响应返回后才可得知，因此已获准的调用可能超过
    Token 上限。用量缺失时，停止后续受 Token 预算限制的调用。SDK 内部
    重试计入同一次逻辑调用。时间限制在准入与输出时检查。
    """
    def __init__(self, *, max_calls=None, max_tokens=None, max_seconds=None):
        for value in (max_calls, max_tokens):
            if value is not None and (type(value) is not int or value <= 0):
                raise ValueError('call/token limits must be positive integers')
        if max_seconds is not None and (isinstance(max_seconds, bool) or not isinstance(max_seconds, (int,float)) or not math.isfinite(max_seconds) or max_seconds <= 0):
            raise ValueError('max_seconds must be finite and positive')
        self.max_calls, self.max_tokens, self.max_seconds = max_calls, max_tokens, max_seconds
        self.calls = self.tokens = self.unknown_usage = 0
        self._started = monotonic()
        self._lock = Lock()

    @contextmanager
    def scope(self):
        token = _current.set(self)
        try:
            yield self
        finally:
            _current.reset(token)

    def check_time(self):
        if self.max_seconds is not None and monotonic() - self._started >= self.max_seconds:
            raise BudgetExceeded('Task time budget exhausted')

    def reserve(self):
        with self._lock:
            self.check_time()
            if self.max_calls is not None and self.calls >= self.max_calls:
                raise BudgetExceeded('Model call budget exhausted')
            if self.max_tokens is not None and (self.unknown_usage or self.tokens >= self.max_tokens):
                raise BudgetExceeded('Token budget exhausted or previous usage unknown')
            self.calls += 1

    def record(self, usage):
        total = usage.get('total_tokens') if isinstance(usage, dict) else None
        if total is None and isinstance(usage, dict):
            parts = [usage.get('prompt_tokens'), usage.get('completion_tokens')]
            if all(type(x) is int and x >= 0 for x in parts):
                total = sum(parts)
        with self._lock:
            if type(total) is not int or total < 0:
                self.unknown_usage += 1
            else:
                self.tokens += total

    def snapshot(self):
        with self._lock:
            return dict(model_calls=self.calls, reported_tokens=self.tokens,
                        unknown_usage_calls=self.unknown_usage,
                        elapsed_seconds=monotonic() - self._started)


@contextmanager
def budget_call(default=None):
    budget = _current.get() or default
    receipt = {}
    if budget is not None:
        budget.reserve()
    try:
        yield receipt, budget
        if budget is not None:
            budget.check_time()
    finally:
        if budget is not None:
            budget.record(receipt.get('usage'))


def budgeted(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with budget_call(self.budget) as (receipt, budget):
            result = method(self, *args, **kwargs)
            receipt['usage'] = result.usage
            return result
    return call


def budgeted_stream(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with budget_call(self.budget) as (receipt, budget):
            self.last_call_stats = None
            source = method(self, *args, **kwargs)
            try:
                for item in source:
                    if budget:
                        budget.check_time()
                    yield item
                receipt['usage'] = getattr(self.last_call_stats, 'usage', None)
            finally:
                source.close()
    return call


def budgeted_astream(method):
    @wraps(method)
    async def call(self, *args, **kwargs):
        with budget_call(self.budget) as (receipt, budget):
            self.last_call_stats = None
            source = method(self, *args, **kwargs)
            try:
                async for item in source:
                    if budget:
                        budget.check_time()
                    yield item
                receipt['usage'] = getattr(self.last_call_stats, 'usage', None)
            finally:
                await source.aclose()
    return call
