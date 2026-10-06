"""自定义工具完整示例

这个文件展示了如何使用 HelloAgents 框架创建和使用自定义工具的完整流程。
"""

from hello_agents import ToolRegistry, ReActAgent, HelloAgentsLLM, Config
from hello_agents.tools import Tool, ToolParameter, ToolResponse, tool_action
from hello_agents.tools.errors import ToolErrorCode


# ============================================
# 示例 1：最简单的自定义工具
# ============================================


class GreetingTool(Tool):
    """问候工具 - 最简单的示例"""

    def __init__(self):
        super().__init__(name="greeting", description="生成个性化的问候语")

    def run(self, parameters):
        name = parameters.get("name", "")
        if not name:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM, message="参数 'name' 不能为空"
            )

        greeting = f"你好，{name}！欢迎使用 HelloAgents 框架！"

        return ToolResponse.success(
            text=greeting, data={"name": name, "greeting": greeting}
        )

    def get_parameters(self):
        return [
            ToolParameter(
                name="name",
                type="string",
                description="要问候的人的名字",
                required=True,
            )
        ]


# ============================================
# 示例 2：函数式工具（最快速）
# ============================================


def word_counter(text: str) -> str:
    """统计文本中的单词数量

    Args:
        text: 要统计的文本
    """
    words = text.split()
    return f"文本包含 {len(words)} 个单词"


# ============================================
# 示例 3：可展开的多功能工具
# ============================================


class TextProcessorTool(Tool):
    """文本处理工具集 - 可展开为多个子工具"""

    def __init__(self):
        super().__init__(
            name="text_processor",
            description="文本处理工具集，包含多种文本处理功能",
            expandable=True,
        )

    @tool_action("text_uppercase", "转换为大写")
    def uppercase(self, text: str) -> ToolResponse:
        """将文本转换为大写

        Args:
            text: 要转换的文本
        """
        return ToolResponse.success(
            text=f"转换结果: {text.upper()}",
            data={"original": text, "result": text.upper()},
        )

    @tool_action("text_lowercase", "转换为小写")
    def lowercase(self, text: str) -> ToolResponse:
        """将文本转换为小写

        Args:
            text: 要转换的文本
        """
        return ToolResponse.success(
            text=f"转换结果: {text.lower()}",
            data={"original": text, "result": text.lower()},
        )

    @tool_action("text_reverse", "反转文本")
    def reverse(self, text: str) -> ToolResponse:
        """反转文本

        Args:
            text: 要反转的文本
        """
        return ToolResponse.success(
            text=f"反转结果: {text[::-1]}",
            data={"original": text, "result": text[::-1]},
        )

    def run(self, parameters):
        return ToolResponse.error(
            code=ToolErrorCode.NOT_IMPLEMENTED,
            message="请使用展开后的子工具: text_uppercase, text_lowercase, text_reverse",
        )

    def get_parameters(self):
        return []


# ============================================
# 主程序：演示所有工具的使用
# ============================================


def main():
    print("=" * 60)
    print("HelloAgents 自定义工具完整示例")
    print("=" * 60)
    print()

    # 1. 创建工具注册表
    print("📦 步骤 1: 创建工具注册表")
    registry = ToolRegistry()
    print("✅ 工具注册表创建成功")
    print()

    # 2. 注册简单工具
    print("📦 步骤 2: 注册简单工具")
    greeting_tool = GreetingTool()
    registry.register_tool(greeting_tool)
    print()

    # 3. 注册函数式工具
    print("📦 步骤 3: 注册函数式工具")
    registry.register_function(word_counter)
    print()

    # 4. 注册可展开工具
    print("📦 步骤 4: 注册可展开工具")
    text_processor = TextProcessorTool()
    registry.register_tool(text_processor)
    print()

    # 5. 查看所有已注册的工具
    print("📋 步骤 5: 查看所有已注册的工具")
    tools = registry.list_tools()
    print(f"已注册 {len(tools)} 个工具:")
    for tool_name in tools:
        print(f"  - {tool_name}")
    print()

    # 6. 直接测试工具
    print("=" * 60)
    print("🧪 直接测试工具")
    print("=" * 60)
    print()

    # 测试问候工具
    print("测试 1: 问候工具")
    response = registry.execute_tool("greeting", {"name": "张三"})
    print(f"  状态: {response.status.value}")
    print(f"  结果: {response.text}")
    print()

    # 测试函数工具
    print("测试 2: 单词计数工具")
    response = registry.execute_tool("word_counter", "Hello World from HelloAgents")
    print(f"  状态: {response.status.value}")
    print(f"  结果: {response.text}")
    print()

    # 测试可展开工具的子工具
    print("测试 3: 文本处理工具（大写）")
    response = registry.execute_tool("text_uppercase", {"text": "hello world"})
    print(f"  状态: {response.status.value}")
    print(f"  结果: {response.text}")
    print()

    print("测试 4: 文本处理工具（反转）")
    response = registry.execute_tool("text_reverse", {"text": "HelloAgents"})
    print(f"  状态: {response.status.value}")
    print(f"  结果: {response.text}")
    print()

    # 7. 实际通过 Agent 运行工具，--live 可切换到配置的模型。
    from examples._support import (
        demo_config,
        demo_llm,
        response as model_response,
        tool_response,
    )

    llm = demo_llm(
        [tool_response("greeting", {"name": "李四"}), model_response("你好，李四！")]
    )
    agent = ReActAgent("assistant", llm, tool_registry=registry, config=demo_config())
    print(agent.run("请用 greeting 工具问候李四"))
    assert agent.last_run.status == "completed" and agent.last_run.tool_calls >= 1

    print("📚 更多信息:")
    print("  - 文档: docs/custom_tools_guide.md")
    print("  - 模板: examples/tools/custom_tools/*_template.py")
    print("  - 示例: examples/tools/custom_tools/weather_tool.py")


if __name__ == "__main__":
    main()
