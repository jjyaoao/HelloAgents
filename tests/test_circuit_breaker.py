"""熔断器机制测试"""

import pytest
import time
from hello_agents.tools.circuit_breaker import CircuitBreaker
from hello_agents.tools.response import ToolResponse, ToolStatus
from hello_agents.tools.errors import ToolErrorCode
from hello_agents.tools.registry import ToolRegistry
from hello_agents.tools.base import Tool


class TestCircuitBreaker:
    """测试 CircuitBreaker 核心功能"""

    def test_initial_state(self):
        """测试初始状态"""
        cb = CircuitBreaker()
        assert cb.is_open("test_tool") is False
        status = cb.get_status("test_tool")
        assert status["state"] == "closed"
        assert status["failure_count"] == 0

    def test_failure_threshold(self):
        """测试失败阈值触发熔断"""
        cb = CircuitBreaker(failure_threshold=3)

        # 模拟 3 次失败
        for i in range(3):
            response = ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message="Test error"
            )
            cb.record_result("test_tool", response)

        # 检查是否熔断
        assert cb.is_open("test_tool") is True
        status = cb.get_status("test_tool")
        assert status["state"] == "open"
        assert status["failure_count"] == 3

    def test_success_resets_counter(self):
        """测试成功重置失败计数"""
        cb = CircuitBreaker(failure_threshold=3)

        # 2 次失败
        for i in range(2):
            response = ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message="Test error"
            )
            cb.record_result("test_tool", response)

        # 1 次成功
        response = ToolResponse.success(text="Success")
        cb.record_result("test_tool", response)

        # 失败计数应该重置
        status = cb.get_status("test_tool")
        assert status["failure_count"] == 0
        assert status["state"] == "closed"

    def test_auto_recovery(self):
        """测试自动恢复"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        # 触发熔断
        for i in range(2):
            response = ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message="Test error"
            )
            cb.record_result("test_tool", response)

        assert cb.is_open("test_tool") is True

        # 等待恢复
        time.sleep(1.1)

        # 应该自动恢复
        assert cb.is_open("test_tool") is False

    def test_manual_open_close(self):
        """测试手动开启/关闭熔断"""
        cb = CircuitBreaker()

        # 手动开启
        cb.open("test_tool")
        assert cb.is_open("test_tool") is True

        # 手动关闭
        cb.close("test_tool")
        assert cb.is_open("test_tool") is False

    def test_disabled_circuit_breaker(self):
        """测试禁用熔断器"""
        cb = CircuitBreaker(enabled=False, failure_threshold=1)

        # 即使失败也不应该熔断
        response = ToolResponse.error(
            code=ToolErrorCode.EXECUTION_ERROR,
            message="Test error"
        )
        cb.record_result("test_tool", response)

        assert cb.is_open("test_tool") is False

    def test_get_all_status(self):
        """测试获取所有工具状态"""
        cb = CircuitBreaker(failure_threshold=2)

        # 工具 A：1 次失败
        response = ToolResponse.error(
            code=ToolErrorCode.EXECUTION_ERROR,
            message="Error"
        )
        cb.record_result("tool_a", response)

        # 工具 B：2 次失败（熔断）
        for i in range(2):
            cb.record_result("tool_b", response)

        all_status = cb.get_all_status()
        assert "tool_a" in all_status
        assert "tool_b" in all_status
        assert all_status["tool_a"]["state"] == "closed"
        assert all_status["tool_b"]["state"] == "open"


class DummyTool(Tool):
    """测试用的虚拟工具"""

    def __init__(self, should_fail: bool = False):
        super().__init__(
            name="dummy_tool",
            description="A dummy tool for testing"
        )
        self.should_fail = should_fail
        self.call_count = 0

    def run(self, parameters: dict) -> ToolResponse:
        self.call_count += 1
        if self.should_fail:
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message="Dummy tool failed"
            )
        return ToolResponse.success(text="Success")

    def get_parameters(self):
        """返回工具参数定义"""
        from hello_agents.tools.base import ToolParameter
        return [
            ToolParameter(
                name="input",
                type="string",
                description="Test input",
                required=False
            )
        ]


class TestToolRegistryIntegration:
    """测试 ToolRegistry 集成熔断器"""

    def test_circuit_breaker_blocks_tool(self):
        """测试熔断器阻止工具调用"""
        cb = CircuitBreaker(failure_threshold=2)
        registry = ToolRegistry(circuit_breaker=cb)

        # 注册一个会失败的工具
        tool = DummyTool(should_fail=True)
        registry.register_tool(tool)

        # 调用 2 次触发熔断
        for i in range(2):
            response = registry.execute_tool("dummy_tool", "test")
            assert response.status == ToolStatus.ERROR

        # 第 3 次应该被熔断器阻止
        response = registry.execute_tool("dummy_tool", "test")
        assert response.status == ToolStatus.ERROR
        assert response.error_info["code"] == ToolErrorCode.CIRCUIT_OPEN
        assert "熔断" in response.text or "禁用" in response.text

        # 工具实际上没有被调用（call_count 应该是 2）
        assert tool.call_count == 2

    def test_circuit_breaker_recovery_allows_retry(self):
        """测试熔断器恢复后允许重试"""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        registry = ToolRegistry(circuit_breaker=cb)

        # 注册一个会失败的工具
        tool = DummyTool(should_fail=True)
        registry.register_tool(tool)

        # 触发熔断
        for i in range(2):
            registry.execute_tool("dummy_tool", "test")

        assert cb.is_open("dummy_tool") is True

        # 等待恢复
        time.sleep(1.1)

        # 现在应该可以再次调用
        response = registry.execute_tool("dummy_tool", "test")
        assert response.status == ToolStatus.ERROR
        assert response.error_info["code"] != ToolErrorCode.CIRCUIT_OPEN

    def test_success_after_partial_failure(self):
        """测试部分失败后成功重置计数"""
        cb = CircuitBreaker(failure_threshold=3)
        registry = ToolRegistry(circuit_breaker=cb)

        # 注册一个可控的工具
        tool = DummyTool(should_fail=True)
        registry.register_tool(tool)

        # 2 次失败
        for i in range(2):
            registry.execute_tool("dummy_tool", "test")

        # 修改为成功
        tool.should_fail = False
        response = registry.execute_tool("dummy_tool", "test")
        assert response.status == ToolStatus.SUCCESS

        # 失败计数应该重置，再失败 3 次才会熔断
        tool.should_fail = True
        for i in range(2):
            registry.execute_tool("dummy_tool", "test")

        # 还没有熔断
        assert cb.is_open("dummy_tool") is False

    def test_multiple_tools_independent(self):
        """测试多个工具的熔断器独立工作"""
        cb = CircuitBreaker(failure_threshold=2)
        registry = ToolRegistry(circuit_breaker=cb)

        # 注册两个工具
        tool_a = DummyTool(should_fail=True)
        tool_a.name = "tool_a"
        tool_b = DummyTool(should_fail=False)
        tool_b.name = "tool_b"

        registry.register_tool(tool_a)
        registry.register_tool(tool_b)

        # tool_a 失败 2 次
        for i in range(2):
            registry.execute_tool("tool_a", "test")

        # tool_a 应该被熔断
        assert cb.is_open("tool_a") is True

        # tool_b 应该仍然可用
        assert cb.is_open("tool_b") is False
        response = registry.execute_tool("tool_b", "test")
        assert response.status == ToolStatus.SUCCESS


class TestCircuitBreakerWithConfig:
    """测试通过 Config 配置熔断器"""

    def test_config_integration(self):
        """测试通过 Config 配置熔断器参数"""
        from hello_agents.core.config import Config
        from hello_agents.tools.circuit_breaker import CircuitBreaker

        config = Config(
            circuit_enabled=True,
            circuit_failure_threshold=5,
            circuit_recovery_timeout=60
        )

        cb = CircuitBreaker(
            failure_threshold=config.circuit_failure_threshold,
            recovery_timeout=config.circuit_recovery_timeout,
            enabled=config.circuit_enabled
        )

        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 60
        assert cb.enabled is True

    def test_disabled_via_config(self):
        """测试通过 Config 禁用熔断器"""
        from hello_agents.core.config import Config
        from hello_agents.tools.circuit_breaker import CircuitBreaker

        config = Config(circuit_enabled=False)

        cb = CircuitBreaker(enabled=config.circuit_enabled)

        # 即使失败也不会熔断
        response = ToolResponse.error(
            code=ToolErrorCode.EXECUTION_ERROR,
            message="Error"
        )
        cb.record_result("test_tool", response)

        assert cb.is_open("test_tool") is False

