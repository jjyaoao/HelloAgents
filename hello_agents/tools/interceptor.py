"""工具调用拦截器 - Human-in-the-loop 确认机制

提供在工具执行前插入人工确认的能力，支持多种确认策略：

策略对比：
- AlwaysAllow: 直接放行（默认，向后兼容）
- ConsoleConfirm: 控制台打印参数并等待 y/n 输入
- SessionConfirm: 同一会话中相同的 (工具名, 参数) 只确认一次
- Callback: 用户提供 async callback，自行实现确认逻辑

用法示例：
    from hello_agents.tools.interceptor import (
        ConsoleConfirmInterceptor, SessionConfirmInterceptor
    )

    # 控制台确认模式
    agent.set_tool_interceptor(
        ConsoleConfirmInterceptor(
            whitelist=["ReadTool", "TodoWriteTool"],
        )
    )

    # 同会话只确认一次
    agent.set_tool_interceptor(
        SessionConfirmInterceptor(
            whitelist=["ReadTool"],
            confirm_each_new_params=True
        )
    )
"""

import asyncio
import hashlib
import json
import sys
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set, Awaitable, Union


class InterceptorDecision(Enum):
    """拦截器决策"""
    ALLOW = "allow"  # 允许执行
    DENY = "deny"    # 拒绝执行


@dataclass
class InterceptorResult:
    """拦截器返回结果

    Attributes:
        decision: 拦截决策（允许/拒绝）
        reason: 决策原因（用于日志和 Agent 反馈）
        metadata: 附加元数据
    """
    decision: InterceptorDecision
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def allow(cls, reason: str = "", **metadata) -> "InterceptorResult":
        """快捷方法：允许执行"""
        return cls(decision=InterceptorDecision.ALLOW, reason=reason, metadata=metadata)

    @classmethod
    def deny(cls, reason: str = "", **metadata) -> "InterceptorResult":
        """快捷方法：拒绝执行"""
        return cls(decision=InterceptorDecision.DENY, reason=reason, metadata=metadata)

    @property
    def is_allowed(self) -> bool:
        return self.decision == InterceptorDecision.ALLOW

    @property
    def is_denied(self) -> bool:
        return self.decision == InterceptorDecision.DENY


class ToolInterceptor(ABC):
    """工具调用拦截器基类

    所有拦截器必须实现 intercept() 方法。
    拦截器在工具执行前被调用，可以允许或拒绝执行。

    异步支持：
    - intercept(): 同步版本，在同步上下文（SimpleAgent.run() 等）中调用
    - aintercept(): 异步版本，在异步上下文（ReActAgent.arun() 等）中调用
      默认实现在线程池中运行 intercept()，避免阻塞事件循环。
      子类可以重写以提供真正的异步实现（如异步 HTTP 回调确认）。

    生命周期：
    - 框架在同步路径调用 intercept()
    - 框架在异步路径调用 aintercept()
    - 如果方法抛出异常，行为等同于拒绝
    """

    @abstractmethod
    def intercept(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> InterceptorResult:
        """拦截工具调用（同步版本）

        所有子类必须实现此方法。

        Args:
            tool_name: 工具名称
            parameters: 工具参数（已做类型转换的参数字典）
            context: 上下文信息，包含：
                - agent_name: Agent 名称
                - agent_type: Agent 类型
                - step: 当前步骤（如果适用）
                - tool_description: 工具描述

        Returns:
            InterceptorResult: 拦截决策
        """
        pass

    async def aintercept(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> InterceptorResult:
        """拦截工具调用（异步版本）

        默认实现：在线程池中运行同步 intercept()，避免阻塞事件循环。
        这对 ConsoleConfirmInterceptor（使用 input()）等阻塞场景尤为关键。

        子类可以重写此方法提供真正的异步实现（如异步 HTTP 回调）。

        Args:
            tool_name: 工具名称
            parameters: 工具参数
            context: 上下文信息

        Returns:
            InterceptorResult: 拦截决策
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.intercept(tool_name, parameters, context)
        )

    def reset(self):
        """重置拦截器状态（子类可选实现，如清除记忆）"""
        pass


class AlwaysAllowInterceptor(ToolInterceptor):
    """默认拦截器：始终放行

    向后兼容：如果未设置拦截器，行为与此一致。
    """

    def intercept(self, tool_name, parameters, context=None):
        return InterceptorResult.allow("默认放行")


class ConsoleConfirmInterceptor(ToolInterceptor):
    """控制台确认拦截器

    在控制台中打印工具调用信息，等待用户输入 y/n 确认。

    参数：
        whitelist: 无需确认的工具名称集合
        timeout: 等待超时秒数（0 = 无超时，默认 60 秒后拒绝）
        show_full_params: 是否显示完整参数（可能很长）
        abort_on_deny: 连续拒绝多少次后中止整个 Agent 执行
    """

    def __init__(
        self,
        whitelist: Optional[Set[str]] = None,
        timeout: float = 60.0,
        show_full_params: bool = True,
        abort_on_deny: int = 0
    ):
        self.whitelist: Set[str] = set(whitelist or [])
        self.timeout = timeout
        self.show_full_params = show_full_params
        self.abort_on_deny = abort_on_deny
        self._deny_count: int = 0

    def intercept(self, tool_name, parameters, context=None):
        # 白名单工具直接放行
        if tool_name in self.whitelist:
            return InterceptorResult.allow(f"白名单工具: {tool_name}")

        # 打印确认信息
        self._print_confirmation(tool_name, parameters, context)

        # 等待用户输入（带超时）
        try:
            response = self._get_input_with_timeout()
        except (EOFError, KeyboardInterrupt):
            print("\n⚠️ 输入中断，默认拒绝执行\n")
            self._deny_count += 1
            return InterceptorResult.deny("用户中断")

        if response.lower() in ('y', 'yes', '允许'):
            print("✅ 已确认执行\n")
            return InterceptorResult.allow("用户确认")
        else:
            print("❌ 已拒绝执行\n")
            self._deny_count += 1
            reason = "用户拒绝"
            if self.abort_on_deny > 0 and self._deny_count >= self.abort_on_deny:
                reason = f"用户连续拒绝 {self._deny_count} 次，建议中止"
            return InterceptorResult.deny(reason)

    def reset(self):
        self._deny_count = 0

    def _print_confirmation(self, tool_name, parameters, context=None):
        """打印确认信息到控制台"""
        print()
        print("┌" + "─" * 58 + "┐")
        print("│" + " 🔧 工具调用确认".ljust(60) + "│")
        print("├" + "─" * 58 + "┤")
        print(f"│  工具名称: {tool_name}".ljust(60) + "│")

        # 显示上下文
        if context:
            if context.get("agent_name"):
                print(f"│  Agent: {context['agent_name']}".ljust(60) + "│")
            if context.get("step"):
                print(f"│  步骤: {context['step']}".ljust(60) + "│")
            if context.get("tool_description"):
                desc = context["tool_description"][:45]
                print(f"│  描述: {desc}".ljust(60) + "│")

        # 显示参数
        if self.show_full_params and parameters:
            print("│" + "─" * 58 + "┤")
            params_str = json.dumps(parameters, ensure_ascii=False, indent=2)
            for line in params_str.split("\n"):
                # 截断过长的行
                display = line[:52] + ".." if len(line) > 52 else line
                print(f"│  {display}".ljust(60) + "│")

        print("└" + "─" * 58 + "┘")

    def _get_input_with_timeout(self) -> str:
        """带超时的用户输入"""
        if self.timeout <= 0:
            return input("是否允许执行？[y/N] ").strip()

        # 使用线程实现超时（跨平台兼容）
        result: list = [""]
        event = threading.Event()

        def _get_input():
            try:
                result[0] = input("是否允许执行？[y/N] ({}秒超时) ".format(int(self.timeout))).strip()
            except (EOFError, OSError):
                result[0] = ""
            finally:
                event.set()

        thread = threading.Thread(target=_get_input, daemon=True)
        thread.start()

        if not event.wait(timeout=self.timeout):
            print("\n⏰ 确认超时，默认拒绝执行\n")
            return "n"

        return result[0] if result[0] else "n"


# 回调类型定义
InterceptCallback = Callable[
    [str, Dict[str, Any], Optional[Dict[str, Any]]],
    InterceptorResult
]

AsyncInterceptCallback = Callable[
    [str, Dict[str, Any], Optional[Dict[str, Any]]],
    Awaitable[InterceptorResult]
]


class CallbackInterceptor(ToolInterceptor):
    """回调拦截器

    将确认逻辑委托给用户提供的回调函数。
    适用于自定义确认逻辑（GUI 弹窗、HTTP 回调、权限服务查询等）。

    支持同步回调和异步回调。

    用法：
        def my_confirm(tool_name, params, context):
            if tool_name in ("BashTool",):
                return InterceptorResult.deny("Bash 工具已禁用")
            return InterceptorResult.allow()

        agent.set_tool_interceptor(CallbackInterceptor(my_confirm))
    """

    def __init__(
        self,
        callback: InterceptCallback,
        async_callback: Optional[AsyncInterceptCallback] = None
    ):
        """
        Args:
            callback: 同步确认回调函数
            async_callback: 异步确认回调函数（可选，用于 async 上下文）
        """
        self._callback = callback
        self._async_callback = async_callback

    def intercept(self, tool_name, parameters, context=None):
        return self._callback(tool_name, parameters, context)

    async def aintercept(self, tool_name, parameters, context=None):
        """异步拦截

        如果提供了 async_callback 则使用异步回调，
        否则在线程池中运行同步回调（避免阻塞事件循环）。
        """
        if self._async_callback:
            return await self._async_callback(tool_name, parameters, context)
        # 在线程池中运行同步回调
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._callback(tool_name, parameters, context)
        )


class SessionConfirmInterceptor(ToolInterceptor):
    """会话级确认拦截器

    在同一会话中，相同的 (工具名, 参数哈希) 只确认一次。
    确认结果会被缓存，后续相同调用自动复用决策。

    可选：仅对"允许"的决策做缓存（拒绝的每次都要确认）。

    参数：
        whitelist: 无需确认的工具名称集合
        cache_denies: 是否缓存拒绝决策（默认 True）
        confirm_each_new_params: 新参数时是否重新确认（默认 True）
        max_cache_size: 最大缓存条目数（防止内存泄漏）
        delegate: 实际的确认逻辑（默认使用控制台输入）
    """

    def __init__(
        self,
        whitelist: Optional[Set[str]] = None,
        cache_denies: bool = True,
        confirm_each_new_params: bool = True,
        max_cache_size: int = 500,
        delegate: Optional[ToolInterceptor] = None  # noqa: F811
    ):
        self.whitelist: Set[str] = set(whitelist or [])
        self.cache_denies = cache_denies
        self.confirm_each_new_params = confirm_each_new_params
        self.max_cache_size = max_cache_size
        self._delegate = delegate or ConsoleConfirmInterceptor()

        # 决策缓存：key = (tool_name, params_hash), value = InterceptorResult
        self._cache: Dict[str, InterceptorResult] = {}

    def intercept(self, tool_name, parameters, context=None):
        if tool_name in self.whitelist:
            return InterceptorResult.allow(f"白名单工具: {tool_name}")

        cache_key = self._make_key(tool_name, parameters)

        # 检查缓存
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if cached.is_allowed or self.cache_denies:
                return cached

        # 委托给实际确认逻辑
        result = self._delegate.intercept(tool_name, parameters, context)

        # 缓存结果
        if result.is_allowed or self.cache_denies:
            self._maybe_evict()
            self._cache[cache_key] = result

        return result

    async def aintercept(self, tool_name, parameters, context=None):
        """异步版本：委托给 delegate.aintercept() 并缓存结果"""
        if tool_name in self.whitelist:
            return InterceptorResult.allow(f"白名单工具: {tool_name}")

        cache_key = self._make_key(tool_name, parameters)

        # 检查缓存
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if cached.is_allowed or self.cache_denies:
                return cached

        # 异步委托给实际确认逻辑
        result = await self._delegate.aintercept(tool_name, parameters, context)

        # 缓存结果
        if result.is_allowed or self.cache_denies:
            self._maybe_evict()
            self._cache[cache_key] = result

        return result

    def reset(self):
        self._cache.clear()
        self._delegate.reset()

    def _make_key(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """生成缓存键：(工具名, 参数哈希)"""
        params_json = json.dumps(parameters, sort_keys=True, ensure_ascii=False)
        params_hash = hashlib.sha256(params_json.encode()).hexdigest()[:16]
        return f"{tool_name}:{params_hash}"

    def _maybe_evict(self):
        """缓存条目过多时淘汰最旧的"""
        if len(self._cache) >= self.max_cache_size:
            # 淘汰前 20%
            evict_count = max(1, self.max_cache_size // 5)
            keys_to_remove = list(self._cache.keys())[:evict_count]
            for key in keys_to_remove:
                del self._cache[key]


# 导出所有公开类
__all__ = [
    "InterceptorDecision",
    "InterceptorResult",
    "ToolInterceptor",
    "AlwaysAllowInterceptor",
    "ConsoleConfirmInterceptor",
    "CallbackInterceptor",
    "SessionConfirmInterceptor",
    "InterceptCallback",
    "AsyncInterceptCallback",
]
