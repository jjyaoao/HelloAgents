"""工具响应协议使用示例

演示如何使用标准化的 ToolResponse 协议，包括：
- 成功响应 (SUCCESS)
- 部分成功响应 (PARTIAL)
- 错误响应 (ERROR)
- 标准错误码的使用
"""

from hello_agents.tools.base import Tool, ToolParameter
from hello_agents.tools.response import ToolResponse, ToolStatus
from hello_agents.tools.errors import ToolErrorCode
from hello_agents.tools.registry import ToolRegistry
from typing import Dict, Any
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


class DemoCalculatorTool(Tool):
    """演示计算器工具 - 展示三种响应状态"""

    def __init__(self):
        super().__init__(
            name="DemoCalculator",
            description="演示工具响应协议的计算器"
        )

    def get_parameters(self) -> list[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="expression",
                type="string",
                description="数学表达式",
                required=True
            )
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        expression = parameters.get("expression", "").strip()
        
        # 错误响应：参数无效
        if not expression:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="表达式不能为空",
                context={"params_input": parameters}
            )
        
        # 错误响应：格式错误
        if not all(c in "0123456789+-*/() ." for c in expression):
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_FORMAT,
                message=f"表达式包含非法字符: {expression}",
                context={"expression": expression}
            )
        
        # 尝试计算
        try:
            result = eval(expression)
            
            # 部分成功：结果过大（演示 PARTIAL 状态）
            if abs(result) > 1e10:
                return ToolResponse.partial(
                    text=f"计算结果: {result:.2e} (结果过大，已使用科学计数法)",
                    data={"result": result, "expression": expression, "truncated": True, "reason": "结果超过显示范围"}
                )
            
            # 成功响应
            return ToolResponse.success(
                text=f"计算结果: {result}",
                data={"result": result, "expression": expression}
            )
            
        except Exception as e:
            # 错误响应：执行错误
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"计算失败: {str(e)}",
                context={"expression": expression, "error": str(e)}
            )


def demo_success_response():
    """演示成功响应"""
    print("=" * 60)
    print("示例 1: 成功响应 (SUCCESS)")
    print("=" * 60)
    
    tool = DemoCalculatorTool()
    response = tool.run({"expression": "2 + 3 * 4"})
    
    print(f"\n状态: {response.status.value}")
    print(f"文本: {response.text}")
    print(f"数据: {response.data}")
    print(f"统计: {response.stats}")
    
    assert response.status == ToolStatus.SUCCESS
    assert response.data["result"] == 14
    print("\n✅ 成功响应测试通过")


def demo_partial_response():
    """演示部分成功响应"""
    print("\n" + "=" * 60)
    print("示例 2: 部分成功响应 (PARTIAL)")
    print("=" * 60)
    
    tool = DemoCalculatorTool()
    response = tool.run({"expression": "10 ** 15"})
    
    print(f"\n状态: {response.status.value}")
    print(f"文本: {response.text}")
    print(f"数据: {response.data}")
    print(f"原因: {response.data.get('reason', 'N/A')}")
    
    assert response.status == ToolStatus.PARTIAL
    assert response.data["truncated"] is True
    print("\n✅ 部分成功响应测试通过")


def demo_error_responses():
    """演示各种错误响应"""
    print("\n" + "=" * 60)
    print("示例 3: 错误响应 (ERROR)")
    print("=" * 60)
    
    tool = DemoCalculatorTool()
    
    # 错误 1: 参数无效
    print("\n3.1 参数无效 (INVALID_PARAM)")
    response = tool.run({"expression": ""})
    print(f"   状态: {response.status.value}")
    print(f"   错误码: {response.error_info['code']}")
    print(f"   错误消息: {response.error_info['message']}")
    assert response.status == ToolStatus.ERROR
    assert response.error_info["code"] == ToolErrorCode.INVALID_PARAM
    
    # 错误 2: 格式错误
    print("\n3.2 格式错误 (INVALID_FORMAT)")
    response = tool.run({"expression": "2 + abc"})
    print(f"   状态: {response.status.value}")
    print(f"   错误码: {response.error_info['code']}")
    print(f"   错误消息: {response.error_info['message']}")
    assert response.error_info["code"] == ToolErrorCode.INVALID_FORMAT
    
    # 错误 3: 执行错误
    print("\n3.3 执行错误 (EXECUTION_ERROR)")
    response = tool.run({"expression": "1 / 0"})
    print(f"   状态: {response.status.value}")
    print(f"   错误码: {response.error_info['code']}")
    print(f"   错误消息: {response.error_info['message']}")
    assert response.error_info["code"] == ToolErrorCode.EXECUTION_ERROR
    
    print("\n✅ 所有错误响应测试通过")


if __name__ == "__main__":
    demo_success_response()
    demo_partial_response()
    demo_error_responses()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成！")
    print("=" * 60)

