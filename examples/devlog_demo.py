"""DevLogTool 使用示例

演示如何使用 DevLogTool 记录开发决策和问题：
1. 基本操作（append, read, summary, clear）
2. 过滤查询（按类别、标签）
3. Agent 集成（零配置自动注册）
4. 持久化和恢复
"""

from hello_agents import ReActAgent, ToolRegistry
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config
from hello_agents.tools.builtin import DevLogTool
from pathlib import Path

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


def demo_1_basic_operations():
    """示例 1：基本操作"""
    print("=" * 60)
    print("示例 1：DevLogTool 基本操作")
    print("=" * 60)

    # 创建 DevLogTool（使用相对路径，与 sessions/todos/traces 一致）
    tool = DevLogTool(
        session_id="demo-session-001",
        agent_name="DemoAgent",
        project_root=".",
        persistence_dir="memory/devlogs"
    )

    print(f"\n✅ DevLogTool 已创建")
    print(f"   会话 ID: {tool.session_id}")
    print(f"   Agent: {tool.agent_name}")

    # 追加决策日志
    print("\n📝 追加决策日志...")
    response = tool.run({
        "action": "append",
        "category": "decision",
        "content": "选择使用 Redis 作为缓存层，因为需要支持分布式部署和高并发访问",
        "metadata": {
            "tags": ["architecture", "cache", "redis"],
            "step": 3,
            "related_tool": "WriteTool"
        }
    })
    print(f"   {response.text}")

    # 追加问题日志
    print("\n📝 追加问题日志...")
    response = tool.run({
        "action": "append",
        "category": "issue",
        "content": "API 响应时间超过 2 秒，影响用户体验",
        "metadata": {
            "tags": ["performance", "api"],
            "severity": "high"
        }
    })
    print(f"   {response.text}")

    # 追加解决方案日志
    print("\n📝 追加解决方案日志...")
    response = tool.run({
        "action": "append",
        "category": "solution",
        "content": "增加 Redis 缓存，缓存热点数据，减少数据库查询",
        "metadata": {
            "tags": ["performance", "cache"],
            "related_issue": "API 响应时间超过 2 秒"
        }
    })
    print(f"   {response.text}")

    # 生成摘要
    print("\n📊 生成摘要...")
    response = tool.run({"action": "summary"})
    print(f"   {response.text}")

    # 读取所有日志
    print("\n📖 读取所有日志...")
    response = tool.run({"action": "read"})
    print(response.text)


def demo_2_filtering():
    """示例 2：过滤查询"""
    print("\n" + "=" * 60)
    print("示例 2：过滤查询")
    print("=" * 60)

    tool = DevLogTool(
        session_id="demo-session-002",
        agent_name="DemoAgent",
        project_root=".",
        persistence_dir="memory/devlogs"
    )

    # 添加多条日志
    logs = [
        {"category": "decision", "content": "使用 PostgreSQL 作为主数据库", "metadata": {"tags": ["database"]}},
        {"category": "decision", "content": "使用 Redis 作为缓存", "metadata": {"tags": ["cache"]}},
        {"category": "issue", "content": "数据库连接池耗尽", "metadata": {"tags": ["database", "performance"]}},
        {"category": "solution", "content": "增加连接池大小到 50", "metadata": {"tags": ["database"]}},
        {"category": "refactor", "content": "重构用户认证模块", "metadata": {"tags": ["auth", "security"]}},
    ]

    for log in logs:
        tool.run({"action": "append", **log})

    print(f"\n✅ 已添加 {len(logs)} 条日志")

    # 按类别过滤
    print("\n🔍 只查看决策类日志...")
    response = tool.run({
        "action": "read",
        "filter": {"category": "decision"}
    })
    print(response.text)

    # 按标签过滤
    print("\n🔍 只查看数据库相关日志...")
    response = tool.run({
        "action": "read",
        "filter": {"tags": ["database"]}
    })
    print(response.text)

    # 限制数量
    print("\n🔍 只查看最近 2 条日志...")
    response = tool.run({
        "action": "read",
        "filter": {"limit": 2}
    })
    print(response.text)


def demo_3_agent_integration():
    """示例 3：Agent 集成 - 零配置使用"""
    print("\n" + "=" * 60)
    print("示例 3：Agent 集成 - 零配置使用")
    print("=" * 60)

    # 配置启用 DevLog（使用相对路径）
    config = Config(
        devlog_enabled=True,
        devlog_persistence_dir="memory/devlogs",
        trace_enabled=False,
        session_enabled=False,
        todowrite_enabled=False,
        subagent_enabled=False,
        skills_enabled=False
    )

    # 创建 Agent（DevLogTool 会自动注册）
    registry = ToolRegistry()
    llm = HelloAgentsLLM()
    agent = ReActAgent(
        name="开发助手",
        llm=llm,
        tool_registry=registry,
        config=config,
        max_steps=3
    )

    # 验证工具已注册
    tool = registry.get_tool("DevLog")
    if tool:
        print("✅ DevLogTool 已自动注册")
        print(f"📝 工具名称: {tool.name}")
        print(f"📝 工具描述: {tool.description[:100]}...")
        print(f"\n💡 Agent 现在可以使用 DevLog 工具记录开发决策和问题")
    else:
        print("❌ DevLogTool 未注册")


def demo_4_persistence():
    """示例 4：持久化和恢复"""
    print("\n" + "=" * 60)
    print("示例 4：持久化和恢复")
    print("=" * 60)

    session_id = "demo-session-004"

    # 第一次：创建工具并添加日志
    print("\n📝 第一次会话：添加日志...")
    tool1 = DevLogTool(
        session_id=session_id,
        agent_name="DemoAgent",
        project_root=".",
        persistence_dir="memory/devlogs"
    )

    tool1.run({
        "action": "append",
        "category": "decision",
        "content": "决定使用微服务架构"
    })
    tool1.run({
        "action": "append",
        "category": "issue",
        "content": "服务间通信延迟高"
    })

    print("   ✅ 已添加 2 条日志")

    # 验证文件已创建
    devlog_file = Path(".") / "memory/devlogs" / f"devlog-{session_id}.json"
    print(f"   📁 日志文件: {devlog_file}")
    print(f"   ✅ 文件存在: {devlog_file.exists()}")

    # 第二次：创建新工具实例，应该自动加载已有日志
    print("\n📖 第二次会话：自动加载已有日志...")
    tool2 = DevLogTool(
        session_id=session_id,
        agent_name="DemoAgent",
        project_root=".",
        persistence_dir="memory/devlogs"
    )

    print(f"   ✅ 已加载 {len(tool2.store.entries)} 条日志")

    # 生成摘要
    response = tool2.run({"action": "summary"})
    print(f"   {response.text}")

    # 继续添加日志
    print("\n📝 继续添加日志...")
    tool2.run({
        "action": "append",
        "category": "solution",
        "content": "使用 gRPC 替代 HTTP REST"
    })

    print(f"   ✅ 现在共有 {len(tool2.store.entries)} 条日志")


if __name__ == "__main__":
    demo_1_basic_operations()
    demo_2_filtering()
    demo_3_agent_integration()
    demo_4_persistence()

    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成")
    print("=" * 60)

