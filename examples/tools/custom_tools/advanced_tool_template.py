"""本地异步查询、TTL 缓存与有界重试。

运行 python -m examples.tools.custom_tools.advanced_tool_template，无需密钥。
loader 是异步只读查询；timeout 限制每次尝试，retries 是额外尝试次数。
缓存属于一个实例，不做跨线程协调、请求合并或持久化。
"""

import asyncio
from copy import deepcopy
import math
import time
from hello_agents.tools import Tool, ToolParameter, ToolResponse


async def local_lookup(query):
    await asyncio.sleep(0)
    return {
        "query": query,
        "notice": "教学资料：参观前确认预约。",
        "source": "fixture://travel",
    }


class AdvancedToolTemplate(Tool):
    def __init__(
        self,
        loader=local_lookup,
        *,
        timeout=1.0,
        retries=1,
        cache_ttl=30.0,
        clock=time.monotonic,
    ):
        super().__init__("advanced_tool", "查询本地教学资料，成功结果短期缓存")
        if not callable(loader) or not callable(clock):
            raise TypeError("loader 和 clock 必须可调用")
        if type(retries) is not int or retries < 0:
            raise ValueError("retries 必须是非负整数")
        if not self._positive(timeout) or not self._positive(cache_ttl):
            raise ValueError("timeout 和 cache_ttl 必须为有限正数")
        self.loader, self.timeout, self.retries = loader, timeout, retries
        self.cache_ttl, self.clock = cache_ttl, clock
        self._cache = {}

    @staticmethod
    def _positive(value):
        return type(value) in (int, float) and math.isfinite(value) and value > 0

    def get_parameters(self):
        return [
            ToolParameter(name="query", type="string", description="查询条件"),
            ToolParameter(
                name="timeout",
                type="number",
                description="每次尝试的等待上限（秒）",
                required=False,
                default=self.timeout,
                json_schema={"type": "number", "exclusiveMinimum": 0},
            ),
        ]

    def run(self, parameters):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(parameters))
        return ToolResponse.error(
            "INVALID_PARAM", "事件循环中请 await tool.arun(parameters)"
        )

    async def arun(self, parameters):
        if not isinstance(parameters, dict) or set(parameters) - {"query", "timeout"}:
            return ToolResponse.error("INVALID_PARAM", "仅接受 query 和 timeout 参数")
        query = parameters.get("query")
        timeout = parameters.get("timeout", self.timeout)
        if (
            not isinstance(query, str)
            or not query.strip()
            or not self._positive(timeout)
        ):
            return ToolResponse.error(
                "INVALID_PARAM", "query 必须是非空字符串，timeout 必须为有限正数"
            )
        now = self.clock()
        self._cache = {
            key: value for key, value in self._cache.items() if value[0] > now
        }
        if query in self._cache:
            return ToolResponse.success(
                "缓存命中",
                data=deepcopy(self._cache[query][1]),
                stats={"cache_hit": True, "attempts": 0},
            )
        for attempt in range(self.retries + 1):
            try:
                result = await asyncio.wait_for(self.loader(query), timeout=timeout)
                if not isinstance(result, dict):
                    return ToolResponse.error("INVALID_FORMAT", "loader 必须返回字典")
                # 只缓存成功载荷；每次返回副本，调用者不能修改缓存。
                if len(self._cache) >= 128:
                    self._cache.pop(next(iter(self._cache)))
                self._cache[query] = (self.clock() + self.cache_ttl, deepcopy(result))
                return ToolResponse.success(
                    "查询完成",
                    data=deepcopy(result),
                    stats={"cache_hit": False, "attempts": attempt + 1},
                )
            except (TimeoutError, asyncio.TimeoutError, OSError) as error:
                if attempt == self.retries:
                    code = (
                        "TIMEOUT"
                        if isinstance(error, (TimeoutError, asyncio.TimeoutError))
                        else "EXECUTION_ERROR"
                    )
                    return ToolResponse.error(
                        code, "查询未完成", stats={"attempts": attempt + 1}
                    )
            except Exception as error:
                return ToolResponse.error(
                    "EXECUTION_ERROR", str(error), stats={"attempts": attempt + 1}
                )
        raise AssertionError("unreachable")

    def clear_cache(self):
        self._cache.clear()


def main():
    tool = AdvancedToolTemplate()
    first = tool.run({"query": "预约"})
    second = tool.run({"query": "预约"})
    assert not first.stats["cache_hit"] and second.stats["cache_hit"]
    print(first.to_json())
    print(second.to_json())

    # wait_for 取消协作式异步查询；不能强制终止阻塞线程或撤销外部副作用。
    async def slow(query):
        await asyncio.sleep(1)
        return {"query": query}

    timed = asyncio.run(
        AdvancedToolTemplate(slow, retries=0).arun({"query": "预约", "timeout": 0.01})
    )
    assert timed.error_info["code"] == "TIMEOUT"
    print(timed.to_json())


if __name__ == "__main__":
    main()
