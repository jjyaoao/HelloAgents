"""简单工具模板 - 最小实现

这是一个最简单的自定义工具模板，适合快速开发简单功能的工具。

使用方法:
    1. 复制此文件并重命名
    2. 修改类名、工具名称和描述
    3. 实现 run() 方法中的业务逻辑
    4. 定义 get_parameters() 中的参数
    5. 注册到 ToolRegistry 并使用
"""

from typing import Dict, Any, List
from hello_agents.tools import Tool, ToolParameter, ToolResponse
from hello_agents.tools.errors import ToolErrorCode


class SimpleToolTemplate(Tool):
    """简单工具模板
    
    这是一个模板工具，演示最基本的工具实现。
    
    功能:
        - 接收输入参数
        - 执行简单的处理逻辑
        - 返回标准化的响应
    
    使用示例:
        >>> tool = SimpleToolTemplate()
        >>> response = tool.run({"input": "test"})
        >>> print(response.text)
    """
    
    def __init__(self):
        """初始化工具
        
        在这里可以:
        - 设置工具名称和描述
        - 初始化配置参数
        - 加载必要的资源
        """
        super().__init__(
            name="simple_tool",  # 修改为你的工具名称
            description="这是一个简单的工具模板，用于演示基本用法"  # 修改为你的工具描述
        )
        
        # 在这里添加你的初始化代码
        # 例如: self.config = load_config()
    
    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行工具的核心逻辑
        
        Args:
            parameters: 工具参数字典，包含用户传入的所有参数
        
        Returns:
            ToolResponse: 标准化的工具响应对象
        """
        # 1. 获取参数
        user_input = parameters.get("input", "")
        
        # 2. 参数验证
        if not user_input:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="参数 'input' 不能为空",
                context={"provided_params": parameters}
            )
        
        # 3. 执行业务逻辑
        try:
            # 在这里实现你的工具逻辑
            # 例如: 调用 API、处理数据、执行计算等
            result = self._process_input(user_input)
            
            # 4. 返回成功响应
            return ToolResponse.success(
                text=f"处理成功: {result}",
                data={
                    "input": user_input,
                    "output": result,
                    "processed": True
                }
            )
        
        except Exception as e:
            # 5. 错误处理
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"工具执行失败: {str(e)}",
                context={"input": user_input}
            )
    
    def get_parameters(self) -> List[ToolParameter]:
        """定义工具的参数列表
        
        Returns:
            List[ToolParameter]: 参数定义列表
        """
        return [
            ToolParameter(
                name="input",
                type="string",
                description="要处理的输入文本",
                required=True
            ),
            # 添加更多参数
            # ToolParameter(
            #     name="option",
            #     type="string",
            #     description="可选参数",
            #     required=False,
            #     default="default_value"
            # )
        ]
    
    def _process_input(self, user_input: str) -> str:
        """处理输入的私有方法
        
        将业务逻辑封装在私有方法中，保持 run() 方法简洁。
        
        Args:
            user_input: 用户输入
        
        Returns:
            str: 处理结果
        """
        # 在这里实现具体的处理逻辑
        # 这只是一个示例，将输入转换为大写
        return user_input.upper()


# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":
    from hello_agents import ToolRegistry, ReActAgent, HelloAgentsLLM
    
    # 1. 创建工具实例
    tool = SimpleToolTemplate()
    
    # 2. 测试工具（直接调用）
    print("=== 直接测试工具 ===")
    response = tool.run({"input": "hello world"})
    print(f"状态: {response.status}")
    print(f"文本: {response.text}")
    print(f"数据: {response.data}")
    print()
    
    # 3. 注册到 ToolRegistry
    print("=== 在 Agent 中使用 ===")
    registry = ToolRegistry()
    registry.register_tool(tool)
    
    # 4. 在 Agent 中使用
    llm = HelloAgentsLLM()
    agent = ReActAgent("assistant", llm, tool_registry=registry)
    
    # Agent 会自动调用工具
    result = agent.run("使用 simple_tool 处理文本 'test message'")
    print(result)

