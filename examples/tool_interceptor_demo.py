"""
工具调用拦截器演示 - Human-in-the-loop 确认机制

演示四种拦截策略：
1. AlwaysAllow - 默认放行
2. ConsoleConfirm - 控制台确认
3. SessionConfirm - 会话级缓存确认
4. Callback - 自定义回调确认
"""

import os
import sys
from pathlib import Path

# 确保项目根目录在 path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from hello_agents import HelloAgentsLLM, SimpleAgent, ToolRegistry
from hello_agents.tools import (
    ReadTool, WriteTool, CalculatorTool,
    ConsoleConfirmInterceptor,
    SessionConfirmInterceptor,
    CallbackInterceptor,
    InterceptorResult,
    InterceptorDecision,
)


def demo_console_confirm():
    """示例 1: 控制台确认模式
    每次工具调用（除了白名单中的）都会在控制台打印参数并等待确认。
    """
    print("=" * 60)
    print("示例 1: ConsoleConfirm 控制台确认模式")
    print("=" * 60)

    llm = HelloAgentsLLM()
    registry = ToolRegistry()
    registry.register_tool(ReadTool())
    registry.register_tool(WriteTool())
    registry.register_tool(CalculatorTool())

    agent = SimpleAgent("assistant", llm, tool_registry=registry)

    # 设置拦截器：ReadTool 和 CalculatorTool 在白名单中，无需确认
    agent.set_tool_interceptor(
        ConsoleConfirmInterceptor(
            whitelist={"ReadTool", "CalculatorTool"},
            timeout=60.0,
            show_full_params=True,
            abort_on_deny=3  # 连续拒绝 3 次后中止
        )
    )

    print(f"当前拦截器: {type(agent.tool_interceptor).__name__}")
    print(f"白名单工具: ReadTool, CalculatorTool")
    print()

    # 模拟运行（实际使用中替换为 agent.run()）
    # agent.run("读取 README.md 的内容")


def demo_session_confirm():
    """示例 2: 会话级确认模式
    同一会话中，相同的工具+参数只确认一次。
    """
    print("=" * 60)
    print("示例 2: SessionConfirm 会话级确认模式")
    print("=" * 60)

    registry = ToolRegistry()
    agent_interceptor = SessionConfirmInterceptor(
        whitelist={"ReadTool", "CalculatorTool"},
        cache_denies=True,
        max_cache_size=200
    )

    # 模拟多次工具调用
    print("第一次调用 WriteTool(path='/tmp/a.txt')")
    result = agent_interceptor.intercept(
        "WriteTool",
        {"path": "/tmp/a.txt", "content": "hello"},
        {"agent_name": "demo_agent"}
    )
    print(f"  决策: {result.decision.value}, 原因: {result.reason}\n")

    print("第二次调用 WriteTool(path='/tmp/a.txt') - 相同参数，命中缓存")
    result = agent_interceptor.intercept(
        "WriteTool",
        {"path": "/tmp/a.txt", "content": "hello"},
        {"agent_name": "demo_agent"}
    )
    # 注意：SessionConfirm 内部使用 ConsoleConfirm 作为 delegate，
    # 在实际运行中第二次不会弹确认框，但这里 delegate 会再次触发 input()
    print(f"  缓存条目数: {len(agent_interceptor._cache)}")


def demo_callback():
    """示例 3: 回调拦截器模式
    用户可以提供自定义函数来决定是否允许执行。
    适用于：权限服务查询、GUI 弹窗、审批流等场景。
    """

    print("=" * 60)
    print("示例 3: Callback 自定义回调模式")
    print("=" * 60)

    # 定义自定义确认逻辑
    def my_permission_checker(tool_name, parameters, context):
        """自定义权限检查：Bash 和危险写操作需阻止"""
        DANGEROUS_TOOLS = {"BashTool", "ExecuteTool"}

        if tool_name in DANGEROUS_TOOLS:
            return InterceptorResult.deny(
                f"安全策略禁止使用 {tool_name}",
                policy="security_block"
            )

        # 检查写操作的目标路径
        if tool_name in ("WriteTool", "EditTool", "MultiEditTool"):
            path = parameters.get("path", "")
            if path.startswith("/etc/") or path.startswith("C:\\Windows"):
                return InterceptorResult.deny(
                    f"禁止修改系统目录: {path}",
                    policy="system_protect"
                )

        return InterceptorResult.allow("权限检查通过")

    interceptor = CallbackInterceptor(my_permission_checker)

    # 测试危险工具
    result = interceptor.intercept("BashTool", {"command": "rm -rf /"})
    print(f"BashTool: {result.decision.value} - {result.reason}")

    # 测试写系统文件
    result = interceptor.intercept("WriteTool", {"path": "/etc/hosts", "content": "..."})
    print(f"WriteTool(/etc/hosts): {result.decision.value} - {result.reason}")

    # 测试正常工具
    result = interceptor.intercept("ReadTool", {"path": "/tmp/test.txt"})
    print(f"ReadTool: {result.decision.value} - {result.reason}")

    # 集成到 Agent
    llm = HelloAgentsLLM()
    registry = ToolRegistry()
    registry.register_tool(ReadTool())
    registry.register_tool(WriteTool())
    registry.register_tool(CalculatorTool())

    agent = SimpleAgent("secure_agent", llm, tool_registry=registry)
    agent.set_tool_interceptor(interceptor)
    print(f"\nAgent 拦截器已设置: {type(agent.tool_interceptor).__name__}")


def demo_registry_level():
    """示例 4: Registry 级别的拦截器
    直接在 ToolRegistry 上设置拦截器，对所有使用该注册表的执行生效。
    """
    print("=" * 60)
    print("示例 4: Registry 级别拦截")
    print("=" * 60)

    def deny_writes(tool_name, params, context):
        if tool_name in ("WriteTool", "EditTool", "MultiEditTool"):
            return InterceptorResult.deny("当前会话禁止写入操作")
        return InterceptorResult.allow()

    registry = ToolRegistry(
        interceptor=CallbackInterceptor(deny_writes)
    )
    registry.register_tool(CalculatorTool())

    # 测试计算器（应通过）
    result = registry.execute_tool("CalculatorTool", {"expression": "2+2"})

    print(f"Calculator tool result status: {result.status.value}")

    # 写工具的测试（由于未注册，会在拦截器通过后返回 NOT_FOUND）
    # 实际使用中，拦截器在检查之前会先判断

    print(f"Registry interceptor: {type(registry.interceptor).__name__}")


if __name__ == "__main__":
    # 需要用户交互的示例在非交互环境中会被跳过
    import argparse
    parser = argparse.ArgumentParser(description="工具调用拦截器演示")
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="运行需要用户交互的示例（控制台确认）"
    )
    parser.add_argument(
        "--example", "-e",
        type=int, choices=[1, 2, 3, 4],
        help="只运行指定示例（1-4）"
    )
    args = parser.parse_args()

    examples = {
        1: ("控制台确认模式 (需交互)", demo_console_confirm, True),
        2: ("会话级确认模式", demo_session_confirm, False),
        3: ("回调拦截器模式", demo_callback, False),
        4: ("Registry 级别拦截", demo_registry_level, False),
    }

    for num, (name, func, requires_interactive) in examples.items():
        if args.example and args.example != num:
            continue
        if requires_interactive and not args.interactive:
            print(f"⏭️  跳过示例 {num}: {name}（使用 --interactive 启用）")
            print()
            continue
        func()
        print()
