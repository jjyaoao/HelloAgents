"""子代理机制使用示例

演示如何使用 TaskTool 实现上下文隔离的子任务执行。
"""

from hello_agents import ReActAgent, SimpleAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config
from hello_agents.tools.registry import ToolRegistry
from hello_agents.tools.builtin import ReadTool, WriteTool, EditTool
from hello_agents.agents.factory import create_agent, default_subagent_factory
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def example_1_basic_subagent():
    """示例 1：基本子代理使用（零配置）"""
    print("\n" + "="*60)
    print("示例 1：基本子代理使用")
    print("="*60)

    # 创建 LLM（使用环境变量配置的模型）
    llm = HelloAgentsLLM()

    # 创建工具注册表
    registry = ToolRegistry()
    registry.register_tool(ReadTool(project_root="./"))

    # 创建主 Agent（自动启用子代理）
    config = Config(subagent_enabled=True)
    agent = ReActAgent(
        name="main-agent",
        llm=llm,
        tool_registry=registry,
        config=config
    )

    # 主 Agent 可以直接使用 Task 工具
    # 框架会自动注册 TaskTool
    print("\n主 Agent 可用工具:", registry.list_tools())
    print("✅ Task 工具已自动注册")


def example_2_manual_subagent():
    """示例 2：手动使用子代理（不通过工具）"""
    print("\n" + "="*60)
    print("示例 2：手动使用子代理")
    print("="*60)

    # 使用环境变量配置的模型
    llm = HelloAgentsLLM()

    # 禁用自动注册，避免重复
    config = Config(subagent_enabled=False, skills_enabled=False)

    registry = ToolRegistry()
    registry.register_tool(ReadTool(project_root="./"))

    # 创建主 Agent
    main_agent = ReActAgent("main", llm, tool_registry=registry, config=config)

    # 创建探索子 Agent
    explore_agent = ReActAgent("explorer", llm, tool_registry=registry, config=config)

    # 手动调用子代理（上下文隔离）
    from hello_agents.tools.tool_filter import ReadOnlyFilter

    print("\n执行子代理任务...")
    result = explore_agent.run_as_subagent(
        task="列出当前目录的文件",
        tool_filter=ReadOnlyFilter(),  # 只允许只读工具
        return_summary=True
    )

    print("\n子代理执行结果:")
    print(f"  成功: {result['success']}")
    print(f"  摘要: {result['summary'][:200]}...")  # 只显示前200字符
    print(f"  步数: {result['metadata']['steps']}")
    print(f"  耗时: {result['metadata']['duration_seconds']}秒")
    print(f"  工具: {result['metadata']['tools_used']}")

    # 主 Agent 的历史未被污染
    print(f"\n主 Agent 历史长度: {len(main_agent.get_history())}")


def example_3_custom_factory():
    """示例 3：自定义子代理工厂"""
    print("\n" + "="*60)
    print("示例 3：自定义子代理工厂")
    print("="*60)

    # 主模型（使用环境变量配置）
    main_llm = HelloAgentsLLM()

    # 轻量模型（使用环境变量配置）
    light_llm = HelloAgentsLLM()

    config = Config(subagent_enabled=False, skills_enabled=False)

    registry = ToolRegistry()
    registry.register_tool(ReadTool(project_root="./"))
    registry.register_tool(WriteTool(project_root="./"))

    # 自定义工厂：根据任务类型选择模型
    def my_agent_factory(agent_type: str):
        """自定义子代理创建逻辑"""
        if agent_type in ["react", "plan"]:
            # 探索和规划用轻量模型
            llm = light_llm
            print(f"  → 使用轻量模型创建 {agent_type} 子代理")
        else:
            # 反思和代码实现用主模型
            llm = main_llm
            print(f"  → 使用主模型创建 {agent_type} 子代理")

        return default_subagent_factory(
            agent_type=agent_type,
            llm=llm,
            tool_registry=registry,
            config=Config(subagent_max_steps=10, subagent_enabled=False, skills_enabled=False)
        )

    # 手动注册 TaskTool
    from hello_agents.tools.builtin.task_tool import TaskTool

    task_tool = TaskTool(
        agent_factory=my_agent_factory,
        tool_registry=registry
    )
    registry.register_tool(task_tool)

    print("\n✅ 自定义 TaskTool 已注册")
    print("  - react/plan 类型 → 轻量模型（节省成本）")
    print("  - reflection/simple 类型 → 主模型（保证质量）")


def example_4_different_agent_types():
    """示例 4：不同类型的子代理"""
    print("\n" + "="*60)
    print("示例 4：不同类型的子代理")
    print("="*60)

    llm = HelloAgentsLLM()
    config = Config(subagent_enabled=False, skills_enabled=False)
    registry = ToolRegistry()

    # 创建不同类型的子代理
    agents = {
        "react": create_agent("react", "react-sub", llm, registry, config),
        "reflection": create_agent("reflection", "reflection-sub", llm, registry, config),
        "plan": create_agent("plan", "plan-sub", llm, registry, config),
        "simple": create_agent("simple", "simple-sub", llm, None, config)
    }

    print("\n创建的子代理类型:")
    for agent_type, agent in agents.items():
        print(f"  - {agent_type}: {agent.__class__.__name__}")

    # 演示不同类型的使用场景
    print("\n推荐使用场景:")
    print("  - react: 需要工具调用的探索任务")
    print("  - reflection: 需要深度思考的分析任务")
    print("  - plan: 需要规划步骤的复杂任务")
    print("  - simple: 简单的问答或总结任务")


def example_5_tool_filtering():
    """示例 5：工具过滤策略"""
    print("\n" + "="*60)
    print("示例 5：工具过滤策略")
    print("="*60)

    from hello_agents.tools.tool_filter import (
        ReadOnlyFilter,
        FullAccessFilter,
        CustomFilter
    )

    llm = HelloAgentsLLM()
    config = Config(subagent_enabled=False, skills_enabled=False)

    registry = ToolRegistry()
    registry.register_tool(ReadTool(project_root="./"))
    registry.register_tool(WriteTool(project_root="./"))
    registry.register_tool(EditTool(project_root="./"))

    agent = ReActAgent("test", llm, tool_registry=registry, config=config)

    print("\n可用的工具过滤器:")

    # 1. 只读过滤器
    readonly_filter = ReadOnlyFilter()
    print("\n1. ReadOnlyFilter（只读）")
    print(f"   允许: {readonly_filter.filter(registry.list_tools())}")

    # 2. 完全访问过滤器
    full_filter = FullAccessFilter()
    print("\n2. FullAccessFilter（完全访问，排除危险工具）")
    print(f"   允许: {full_filter.filter(registry.list_tools())}")

    # 3. 自定义白名单
    custom_whitelist = CustomFilter(
        allowed=["Read", "Write"],
        mode="whitelist"
    )
    print("\n3. CustomFilter（白名单模式）")
    print(f"   允许: {custom_whitelist.filter(registry.list_tools())}")

    # 4. 自定义黑名单
    custom_blacklist = CustomFilter(
        denied=["Write", "Edit"],
        mode="blacklist"
    )
    print("\n4. CustomFilter（黑名单模式）")
    print(f"   允许: {custom_blacklist.filter(registry.list_tools())}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("HelloAgents 子代理机制示例")
    print("="*60)

    # 运行所有示例
    try:
        example_1_basic_subagent()
        example_2_manual_subagent()
        example_3_custom_factory()
        example_4_different_agent_types()
        example_5_tool_filtering()
    except Exception as e:
        print(f"\n❌ 示例执行出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)
    print("所有示例运行完成")
    print("="*60)


