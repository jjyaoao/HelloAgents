"""自定义工具测试套件

测试自定义工具的注册、执行和各种特性。
"""

import pytest
from hello_agents.tools import Tool, ToolParameter, ToolResponse, ToolRegistry
from hello_agents.tools.errors import ToolErrorCode


# ============================================
# 测试工具定义
# ============================================

class SimpleTestTool(Tool):
    """简单测试工具"""
    
    def __init__(self):
        super().__init__(
            name="simple_test",
            description="简单测试工具"
        )
    
    def run(self, parameters):
        text = parameters.get("text", "")
        if not text:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="参数 'text' 不能为空"
            )
        
        return ToolResponse.success(
            text=f"处理结果: {text.upper()}",
            data={"original": text, "processed": text.upper()}
        )
    
    def get_parameters(self):
        return [
            ToolParameter(
                name="text",
                type="string",
                description="要处理的文本",
                required=True
            )
        ]


# ============================================
# 测试用例
# ============================================

class TestCustomToolBasics:
    """测试自定义工具的基本功能"""
    
    def test_tool_creation(self):
        """测试工具创建"""
        tool = SimpleTestTool()
        assert tool.name == "simple_test"
        assert tool.description == "简单测试工具"
    
    def test_tool_parameters(self):
        """测试工具参数定义"""
        tool = SimpleTestTool()
        params = tool.get_parameters()
        
        assert len(params) == 1
        assert params[0].name == "text"
        assert params[0].type == "string"
        assert params[0].required is True
    
    def test_tool_execution_success(self):
        """测试工具成功执行"""
        tool = SimpleTestTool()
        response = tool.run({"text": "hello"})
        
        assert response.status.value == "success"
        assert "HELLO" in response.text
        assert response.data["original"] == "hello"
        assert response.data["processed"] == "HELLO"
    
    def test_tool_execution_error(self):
        """测试工具错误处理"""
        tool = SimpleTestTool()
        response = tool.run({})  # 缺少参数
        
        assert response.status.value == "error"
        assert response.error_info["code"] == ToolErrorCode.INVALID_PARAM
        assert "不能为空" in response.error_info["message"]
    
    def test_tool_with_timing(self):
        """测试带时间统计的执行"""
        tool = SimpleTestTool()
        response = tool.run_with_timing({"text": "test"})
        
        assert response.status.value == "success"
        assert "time_ms" in response.stats
        assert response.stats["time_ms"] >= 0
        assert response.context["tool_name"] == "simple_test"


class TestToolRegistry:
    """测试工具注册表"""
    
    def test_register_tool(self):
        """测试注册工具"""
        registry = ToolRegistry()
        tool = SimpleTestTool()
        
        registry.register_tool(tool)
        
        assert "simple_test" in registry.list_tools()
        assert registry.get_tool("simple_test") is tool
    
    def test_execute_tool(self):
        """测试执行已注册的工具"""
        registry = ToolRegistry()
        tool = SimpleTestTool()
        registry.register_tool(tool)
        
        response = registry.execute_tool("simple_test", {"text": "world"})
        
        assert response.status.value == "success"
        assert "WORLD" in response.text
    
    def test_execute_nonexistent_tool(self):
        """测试执行不存在的工具"""
        registry = ToolRegistry()
        
        response = registry.execute_tool("nonexistent", {"text": "test"})
        
        assert response.status.value == "error"
        assert response.error_info["code"] == ToolErrorCode.NOT_FOUND


class TestFunctionTools:
    """测试函数式工具"""
    
    def test_register_function_new_style(self):
        """测试新式函数注册（自动提取名称和描述）"""
        def my_function(input: str) -> str:
            """这是我的函数"""
            return f"处理: {input}"
        
        registry = ToolRegistry()
        registry.register_function(my_function)
        
        assert "my_function" in registry.list_tools()
    
    def test_register_function_with_custom_name(self):
        """测试指定名称的函数注册"""
        def my_function(input: str) -> str:
            """这是我的函数"""
            return f"处理: {input}"
        
        registry = ToolRegistry()
        registry.register_function(my_function, name="custom_name", description="自定义描述")
        
        assert "custom_name" in registry.list_tools()
    
    def test_execute_function_tool(self):
        """测试执行函数工具"""
        def uppercase(input: str) -> str:
            """转换为大写"""
            return input.upper()
        
        registry = ToolRegistry()
        registry.register_function(uppercase)
        
        response = registry.execute_tool("uppercase", "hello")
        
        assert response.status.value == "success"
        assert response.data["output"] == "HELLO"
    
    def test_function_tool_error_handling(self):
        """测试函数工具的错误处理"""
        def failing_function(input: str) -> str:
            """会失败的函数"""
            raise ValueError("故意失败")
        
        registry = ToolRegistry()
        registry.register_function(failing_function)
        
        response = registry.execute_tool("failing_function", "test")
        
        assert response.status.value == "error"
        assert "故意失败" in response.error_info["message"]


class TestExpandableTools:
    """测试可展开工具"""
    
    def test_expandable_tool_registration(self):
        """测试可展开工具的注册"""
        from hello_agents.tools import tool_action
        
        class MultiTool(Tool):
            def __init__(self):
                super().__init__(
                    name="multi",
                    description="多功能工具",
                    expandable=True
                )
            
            @tool_action("multi_action1", "动作1")
            def action1(self, input: str) -> ToolResponse:
                """执行动作1"""
                return ToolResponse.success(text=f"动作1: {input}")
            
            @tool_action("multi_action2", "动作2")
            def action2(self, input: str) -> ToolResponse:
                """执行动作2"""
                return ToolResponse.success(text=f"动作2: {input}")
            
            def run(self, parameters):
                return ToolResponse.error(code="NOT_IMPLEMENTED", message="请使用子工具")
            
            def get_parameters(self):
                return []
        
        registry = ToolRegistry()
        tool = MultiTool()
        registry.register_tool(tool)
        
        # 应该注册了两个子工具
        tools = registry.list_tools()
        assert "multi_action1" in tools
        assert "multi_action2" in tools


# ============================================
# 运行测试
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

