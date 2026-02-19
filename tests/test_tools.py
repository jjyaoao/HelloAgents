"""测试工具注册表与内置计算器。"""

import pytest
from hello_agents.tools.registry import ToolRegistry
from hello_agents.tools.builtin.calculator import CalculatorTool


class TestToolRegistry:
    def test_register_and_get_tool(self):
        reg = ToolRegistry()
        calc = CalculatorTool()
        reg.register_tool(calc, auto_expand=True)
        assert reg.get_tool(calc.name) is calc

    def test_execute_tool_by_name(self):
        reg = ToolRegistry()
        reg.register_tool(CalculatorTool(), auto_expand=True)
        out = reg.execute_tool("python_calculator", "2 + 3")
        assert "5" in out

    def test_register_function(self):
        reg = ToolRegistry()

        def echo(x: str) -> str:
            return x

        reg.register_function("echo", "Echo input", echo)
        assert reg.get_function("echo") is echo
        assert reg.execute_tool("echo", "hi") == "hi"

    def test_get_tools_description(self):
        reg = ToolRegistry()
        reg.register_tool(CalculatorTool(), auto_expand=True)
        desc = reg.get_tools_description()
        assert "python_calculator" in desc or "计算" in desc

    def test_unregister(self):
        reg = ToolRegistry()
        reg.register_function("dummy", "Dummy", lambda x: x)
        reg.unregister("dummy")
        assert reg.get_function("dummy") is None


class TestCalculatorTool:
    def test_run_with_input(self):
        calc = CalculatorTool()
        assert calc.run({"input": "1 + 1"}) == "2"

    def test_run_with_expression(self):
        calc = CalculatorTool()
        assert calc.run({"expression": "3 * 4"}) == "12"

    def test_run_empty_fails(self):
        calc = CalculatorTool()
        out = calc.run({"input": ""})
        assert "错误" in out or "空" in out

    def test_math_functions(self):
        calc = CalculatorTool()
        assert "2" in calc.run({"input": "sqrt(4)"})
