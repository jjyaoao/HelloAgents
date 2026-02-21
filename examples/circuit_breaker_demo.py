"""熔断器机制使用示例

演示如何使用 CircuitBreaker 防止工具连续失败：
- 自动熔断和恢复
- 手动控制熔断器
- 与 ToolRegistry 集成
"""

from hello_agents.tools.circuit_breaker import CircuitBreaker
from hello_agents.tools.registry import ToolRegistry
from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse, ToolStatus
from hello_agents.tools.errors import ToolErrorCode
from typing import Dict, Any
import time
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


class UnstableTool(Tool):
    """不稳定的工具 - 用于演示熔断器"""

    def __init__(self):
        super().__init__(
            name="UnstableTool",
            description="一个不稳定的工具，用于测试熔断器"
        )
        self.call_count = 0

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        self.call_count += 1
        should_fail = parameters.get("should_fail", False)

        if should_fail:
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"工具执行失败 (第 {self.call_count} 次调用)"
            )

        return ToolResponse.success(
            text=f"工具执行成功 (第 {self.call_count} 次调用)",
            data={"call_count": self.call_count}
        )

    def get_parameters(self):
        """返回工具参数定义"""
        return [
            ToolParameter(
                name="should_fail",
                type="boolean",
                description="是否应该失败",
                required=False
            )
        ]


def demo_auto_circuit_breaking():
    """演示自动熔断"""
    print("=" * 60)
    print("示例 1: 自动熔断机制")
    print("=" * 60)
    
    # 创建熔断器（失败 3 次后熔断）
    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=5,
        enabled=True
    )
    
    # 创建工具注册表
    registry = ToolRegistry(circuit_breaker=breaker)
    tool = UnstableTool()
    registry.register_tool(tool)
    
    print("\n连续失败测试:")
    
    # 连续失败 3 次
    for i in range(3):
        response = registry.execute_tool("UnstableTool", '{"should_fail": true}')
        print(f"  调用 {i+1}: {response.status.value} - {response.text if response.status == ToolStatus.SUCCESS else response.error_info['message']}")
    
    # 第 4 次调用应该被熔断器拦截
    print("\n第 4 次调用（应该被熔断）:")
    response = registry.execute_tool("UnstableTool", '{"should_fail": true}')
    print(f"  状态: {response.status.value}")
    print(f"  错误码: {response.error_info['code']}")
    print(f"  消息: {response.error_info['message']}")
    
    assert response.status == ToolStatus.ERROR
    assert response.error_info["code"] == ToolErrorCode.CIRCUIT_OPEN
    
    print("\n✅ 自动熔断测试完成")


def demo_auto_recovery():
    """演示自动恢复"""
    print("\n" + "=" * 60)
    print("示例 2: 自动恢复机制")
    print("=" * 60)
    
    # 创建熔断器（恢复时间 2 秒）
    breaker = CircuitBreaker(
        failure_threshold=2,
        recovery_timeout=2,
        enabled=True
    )
    
    registry = ToolRegistry(circuit_breaker=breaker)
    tool = UnstableTool()
    registry.register_tool(tool)
    
    # 触发熔断
    print("\n触发熔断:")
    for i in range(2):
        response = registry.execute_tool("UnstableTool", '{"should_fail": true}')
        print(f"  调用 {i+1}: {response.status.value}")
    
    # 验证熔断
    response = registry.execute_tool("UnstableTool", '{"should_fail": false}')
    print(f"\n熔断状态: {response.error_info['code'] if response.status == ToolStatus.ERROR else 'N/A'}")
    assert response.error_info["code"] == ToolErrorCode.CIRCUIT_OPEN
    
    # 等待恢复
    print("\n等待 2 秒自动恢复...")
    time.sleep(2.1)
    
    # 恢复后应该可以调用
    response = registry.execute_tool("UnstableTool", '{"should_fail": false}')
    print(f"恢复后调用: {response.status.value}")
    assert response.status == ToolStatus.SUCCESS
    
    print("\n✅ 自动恢复测试完成")


def demo_success_reset():
    """演示成功重置失败计数"""
    print("\n" + "=" * 60)
    print("示例 3: 成功重置失败计数")
    print("=" * 60)
    
    breaker = CircuitBreaker(failure_threshold=3, enabled=True)
    registry = ToolRegistry(circuit_breaker=breaker)
    tool = UnstableTool()
    registry.register_tool(tool)
    
    print("\n失败 -> 失败 -> 成功 -> 失败:")
    
    # 失败 2 次
    registry.execute_tool("UnstableTool", '{"should_fail": true}')
    print("  调用 1: 失败 (计数: 1)")
    registry.execute_tool("UnstableTool", '{"should_fail": true}')
    print("  调用 2: 失败 (计数: 2)")
    
    # 成功 1 次（重置计数）
    response = registry.execute_tool("UnstableTool", '{"should_fail": false}')
    print("  调用 3: 成功 (计数: 0) ← 重置")
    assert response.status == ToolStatus.SUCCESS
    
    # 再失败 2 次（不会熔断，因为计数已重置）
    registry.execute_tool("UnstableTool", '{"should_fail": true}')
    print("  调用 4: 失败 (计数: 1)")
    response = registry.execute_tool("UnstableTool", '{"should_fail": true}')
    print("  调用 5: 失败 (计数: 2)")
    
    # 应该还能调用（未达到阈值 3）
    assert response.status == ToolStatus.ERROR
    assert response.error_info["code"] != ToolErrorCode.CIRCUIT_OPEN
    
    print("\n✅ 成功重置测试完成")


def demo_manual_control():
    """演示手动控制熔断器"""
    print("\n" + "=" * 60)
    print("示例 4: 手动控制熔断器")
    print("=" * 60)
    
    breaker = CircuitBreaker(enabled=True)
    registry = ToolRegistry(circuit_breaker=breaker)
    tool = UnstableTool()
    registry.register_tool(tool)
    
    # 手动开启熔断
    print("\n手动开启熔断:")
    breaker.open("UnstableTool")
    
    response = registry.execute_tool("UnstableTool", '{"should_fail": false}')
    print(f"  状态: {response.status.value}")
    assert response.error_info["code"] == ToolErrorCode.CIRCUIT_OPEN
    
    # 手动关闭熔断
    print("\n手动关闭熔断:")
    breaker.close("UnstableTool")
    
    response = registry.execute_tool("UnstableTool", '{"should_fail": false}')
    print(f"  状态: {response.status.value}")
    assert response.status == ToolStatus.SUCCESS
    
    print("\n✅ 手动控制测试完成")


if __name__ == "__main__":
    demo_auto_circuit_breaking()
    demo_auto_recovery()
    demo_success_reset()
    demo_manual_control()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成！")
    print("=" * 60)

