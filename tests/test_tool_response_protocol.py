"""工具响应协议测试

测试新的 ToolResponse 协议是否正常工作，包括：
1. ToolResponse 数据类的创建和序列化
2. ToolErrorCode 错误码
3. CalculatorTool 使用新协议
4. ToolRegistry 执行工具返回 ToolResponse
5. ReActAgent 解析 ToolResponse
6. FunctionCallAgent 使用新协议
"""

import pytest
import json
from hello_agents.tools.response import ToolResponse, ToolStatus
from hello_agents.tools.errors import ToolErrorCode
from hello_agents.tools.builtin.calculator import CalculatorTool
from hello_agents.tools.registry import ToolRegistry


class TestToolResponse:
    """测试 ToolResponse 数据类"""
    
    def test_success_response(self):
        """测试成功响应"""
        resp = ToolResponse.success(
            text="计算结果: 42",
            data={"result": 42, "expression": "6*7"}
        )

        assert resp.status == ToolStatus.SUCCESS
        assert resp.text == "计算结果: 42"
        assert resp.data["result"] == 42
        assert resp.error_info is None
    
    def test_partial_response(self):
        """测试部分成功响应"""
        resp = ToolResponse.partial(
            text="结果已截断",
            data={"truncated": True}
        )
        
        assert resp.status == ToolStatus.PARTIAL
        assert resp.text == "结果已截断"
        assert resp.data["truncated"] is True
    
    def test_error_response(self):
        """测试错误响应"""
        resp = ToolResponse.error(
            code=ToolErrorCode.NOT_FOUND,
            message="文件不存在"
        )

        assert resp.status == ToolStatus.ERROR
        assert resp.text == "文件不存在"
        assert resp.error_info["code"] == ToolErrorCode.NOT_FOUND
        assert resp.error_info["message"] == "文件不存在"
    
    def test_to_dict(self):
        """测试转换为字典"""
        resp = ToolResponse.success(
            text="OK",
            data={"value": 123},
            stats={"time_ms": 50},
            context={"tool": "test"}
        )
        
        d = resp.to_dict()
        assert d["status"] == "success"
        assert d["text"] == "OK"
        assert d["data"]["value"] == 123
        assert d["stats"]["time_ms"] == 50
        assert d["context"]["tool"] == "test"
    
    def test_to_json(self):
        """测试转换为 JSON"""
        resp = ToolResponse.success(text="OK", data={"value": 42})
        json_str = resp.to_json()
        
        # 验证可以解析
        parsed = json.loads(json_str)
        assert parsed["status"] == "success"
        assert parsed["data"]["value"] == 42
    
    def test_from_dict(self):
        """测试从字典创建"""
        d = {
            "status": "error",
            "text": "失败",
            "data": {},
            "error": {"code": "TEST_ERROR", "message": "失败"}
        }

        resp = ToolResponse.from_dict(d)
        assert resp.status == ToolStatus.ERROR
        assert resp.text == "失败"
        assert resp.error_info["code"] == "TEST_ERROR"
    
    def test_from_json(self):
        """测试从 JSON 创建"""
        json_str = '{"status": "success", "text": "OK", "data": {"value": 42}}'
        resp = ToolResponse.from_json(json_str)
        
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data["value"] == 42


class TestToolErrorCode:
    """测试错误码"""
    
    def test_error_codes_exist(self):
        """测试错误码是否存在"""
        assert ToolErrorCode.NOT_FOUND == "NOT_FOUND"
        assert ToolErrorCode.INVALID_PARAM == "INVALID_PARAM"
        assert ToolErrorCode.EXECUTION_ERROR == "EXECUTION_ERROR"
        assert ToolErrorCode.TIMEOUT == "TIMEOUT"
    
    def test_get_all_codes(self):
        """测试获取所有错误码"""
        codes = ToolErrorCode.get_all_codes()
        assert "NOT_FOUND" in codes
        assert "INVALID_PARAM" in codes
        assert len(codes) > 5
    
    def test_is_valid_code(self):
        """测试验证错误码"""
        assert ToolErrorCode.is_valid_code("NOT_FOUND") is True
        assert ToolErrorCode.is_valid_code("INVALID_CODE") is False


class TestCalculatorToolNewProtocol:
    """测试 CalculatorTool 使用新协议"""
    
    def test_successful_calculation(self):
        """测试成功计算"""
        tool = CalculatorTool()
        resp = tool.run({"input": "2 + 3"})
        
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data["result"] == 5
        assert resp.data["expression"] == "2 + 3"
        assert "计算结果: 5" in resp.text
    
    def test_complex_calculation(self):
        """测试复杂计算"""
        tool = CalculatorTool()
        resp = tool.run({"input": "sqrt(16) + 2 * 3"})
        
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data["result"] == 10.0
    
    def test_empty_expression_error(self):
        """测试空表达式错误"""
        tool = CalculatorTool()
        resp = tool.run({"input": ""})

        assert resp.status == ToolStatus.ERROR
        assert resp.error_info["code"] == ToolErrorCode.INVALID_PARAM
        assert "不能为空" in resp.text

    def test_syntax_error(self):
        """测试语法错误"""
        tool = CalculatorTool()
        resp = tool.run({"input": "2 +"})

        assert resp.status == ToolStatus.ERROR
        assert resp.error_info["code"] == ToolErrorCode.INVALID_FORMAT
        assert "语法错误" in resp.text

    def test_execution_error(self):
        """测试执行错误"""
        tool = CalculatorTool()
        resp = tool.run({"input": "unknown_func()"})

        assert resp.status == ToolStatus.ERROR
        assert resp.error_info["code"] == ToolErrorCode.EXECUTION_ERROR
    
    def test_run_with_timing(self):
        """测试带时间统计的执行"""
        tool = CalculatorTool()
        resp = tool.run_with_timing({"input": "10 * 5"})
        
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data["result"] == 50
        assert "time_ms" in resp.stats
        assert resp.stats["time_ms"] >= 0
        assert "params_input" in resp.context
        assert resp.context["tool_name"] == "python_calculator"


class TestToolRegistryIntegration:
    """测试 ToolRegistry 集成"""
    
    def test_execute_tool_object(self):
        """测试执行 Tool 对象"""
        registry = ToolRegistry()
        registry.register_tool(CalculatorTool())
        
        resp = registry.execute_tool("python_calculator", "10 + 20")
        
        assert isinstance(resp, ToolResponse)
        assert resp.status == ToolStatus.SUCCESS
        assert resp.data["result"] == 30
        assert "time_ms" in resp.stats
    
    def test_execute_function_tool(self):
        """测试执行函数工具（自动包装）"""
        registry = ToolRegistry()
        
        def simple_func(input_text: str) -> str:
            return f"处理: {input_text}"
        
        registry.register_function("simple", "简单函数", simple_func)
        
        resp = registry.execute_tool("simple", "测试")
        
        assert isinstance(resp, ToolResponse)
        assert resp.status == ToolStatus.SUCCESS
        assert "处理: 测试" in resp.text
        assert resp.data["output"] == "处理: 测试"
    
    def test_execute_nonexistent_tool(self):
        """测试执行不存在的工具"""
        registry = ToolRegistry()

        resp = registry.execute_tool("nonexistent", "test")

        assert resp.status == ToolStatus.ERROR
        assert resp.error_info["code"] == ToolErrorCode.NOT_FOUND
        assert "未找到" in resp.text or "不存在" in resp.text


class TestFunctionToolException:
    """测试函数工具异常处理"""
    
    def test_function_raises_exception(self):
        """测试函数抛出异常"""
        registry = ToolRegistry()

        def error_func(input_text: str) -> str:
            raise ValueError("故意的错误")

        registry.register_function("error", "错误函数", error_func)

        resp = registry.execute_tool("error", "test")

        assert resp.status == ToolStatus.ERROR
        assert resp.error_info["code"] == ToolErrorCode.EXECUTION_ERROR
        assert "故意的错误" in resp.text


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])

