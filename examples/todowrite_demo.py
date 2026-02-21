"""TodoWrite 进度管理工具示例

演示如何使用 TodoWrite 工具管理复杂任务的进度。

特性：
- 声明式任务列表管理
- 单线程强制（最多 1 个 in_progress）
- 自动 Recap 生成
- 持久化支持断点恢复
"""

from hello_agents import ReActAgent, HelloAgentsLLM, ToolRegistry, Config
from hello_agents.tools.builtin import TodoWriteTool
from dotenv import load_dotenv

load_dotenv()


def demo_1_basic_usage():
    """示例 1：基本使用 - 手动管理任务列表"""
    print("\n" + "="*60)
    print("示例 1：基本使用 - 手动管理任务列表")
    print("="*60)
    
    # 创建工具
    tool = TodoWriteTool(project_root="./", persistence_dir="memory/todos")
    
    # 1. 创建任务列表
    print("\n1️⃣ 创建任务列表")
    response = tool.run({
        "summary": "实现电商核心功能",
        "todos": [
            {"content": "实现用户认证模块", "status": "pending"},
            {"content": "实现订单处理模块", "status": "pending"},
            {"content": "实现支付集成", "status": "pending"},
            {"content": "实现库存管理", "status": "pending"}
        ]
    })
    print(f"✅ {response.text}")
    print(f"📊 统计: {response.data['stats']}")
    
    # 2. 开始第一个任务
    print("\n2️⃣ 开始第一个任务")
    response = tool.run({
        "summary": "实现电商核心功能",
        "todos": [
            {"content": "实现用户认证模块", "status": "in_progress"},
            {"content": "实现订单处理模块", "status": "pending"},
            {"content": "实现支付集成", "status": "pending"},
            {"content": "实现库存管理", "status": "pending"}
        ]
    })
    print(f"✅ {response.text}")
    
    # 3. 完成第一个任务，开始第二个
    print("\n3️⃣ 完成第一个任务，开始第二个")
    response = tool.run({
        "summary": "实现电商核心功能",
        "todos": [
            {"content": "实现用户认证模块", "status": "completed"},
            {"content": "实现订单处理模块", "status": "in_progress"},
            {"content": "实现支付集成", "status": "pending"},
            {"content": "实现库存管理", "status": "pending"}
        ]
    })
    print(f"✅ {response.text}")
    
    # 4. 继续完成任务
    print("\n4️⃣ 继续完成任务")
    response = tool.run({
        "summary": "实现电商核心功能",
        "todos": [
            {"content": "实现用户认证模块", "status": "completed"},
            {"content": "实现订单处理模块", "status": "completed"},
            {"content": "实现支付集成", "status": "in_progress"},
            {"content": "实现库存管理", "status": "pending"}
        ]
    })
    print(f"✅ {response.text}")
    
    # 5. 全部完成
    print("\n5️⃣ 全部完成")
    response = tool.run({
        "summary": "实现电商核心功能",
        "todos": [
            {"content": "实现用户认证模块", "status": "completed"},
            {"content": "实现订单处理模块", "status": "completed"},
            {"content": "实现支付集成", "status": "completed"},
            {"content": "实现库存管理", "status": "completed"}
        ]
    })
    print(f"✅ {response.text}")


def demo_2_constraint_validation():
    """示例 2：约束验证 - 单线程强制"""
    print("\n" + "="*60)
    print("示例 2：约束验证 - 单线程强制")
    print("="*60)
    
    tool = TodoWriteTool(project_root="./", persistence_dir="memory/todos")
    
    # 尝试创建多个 in_progress 任务（违反约束）
    print("\n❌ 尝试创建多个 in_progress 任务")
    response = tool.run({
        "todos": [
            {"content": "任务1", "status": "in_progress"},
            {"content": "任务2", "status": "in_progress"},  # 违反约束
        ]
    })
    
    if response.status.value == "error":
        print(f"🚫 错误: {response.error_info['message']}")
        print(f"📝 错误码: {response.error_info['code']}")
    
    # 正确的方式：最多 1 个 in_progress
    print("\n✅ 正确方式：最多 1 个 in_progress")
    response = tool.run({
        "todos": [
            {"content": "任务1", "status": "in_progress"},
            {"content": "任务2", "status": "pending"},
        ]
    })
    print(f"✅ {response.text}")


def demo_3_agent_integration():
    """示例 3：Agent 集成 - 零配置使用"""
    print("\n" + "="*60)
    print("示例 3：Agent 集成 - 零配置使用")
    print("="*60)
    
    # 配置启用 TodoWrite
    config = Config(
        todowrite_enabled=True,
        todowrite_persistence_dir="memory/todos",
        trace_enabled=False  # 关闭 trace 简化输出
    )
    
    # 创建 Agent（TodoWriteTool 会自动注册）
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
    tool = registry.get_tool("TodoWrite")
    if tool:
        print("✅ TodoWriteTool 已自动注册")
        print(f"📝 工具名称: {tool.name}")
        print(f"📝 工具描述: {tool.description[:100]}...")
    else:
        print("❌ TodoWriteTool 未注册")


def demo_4_persistence():
    """示例 4：持久化 - 保存和加载任务列表"""
    print("\n" + "="*60)
    print("示例 4：持久化 - 保存和加载任务列表")
    print("="*60)
    
    tool = TodoWriteTool(project_root="./", persistence_dir="memory/todos")
    
    # 创建任务列表（会自动持久化）
    print("\n1️⃣ 创建任务列表（自动持久化）")
    response = tool.run({
        "summary": "重构项目架构",
        "todos": [
            {"content": "分析现有架构", "status": "completed"},
            {"content": "设计新架构", "status": "in_progress"},
            {"content": "实施重构", "status": "pending"}
        ]
    })
    print(f"✅ {response.text}")
    
    # 查看持久化文件
    import os
    from pathlib import Path
    
    todos_dir = Path("memory/todos")
    if todos_dir.exists():
        files = sorted(todos_dir.glob("todoList-*.json"))
        if files:
            latest_file = files[-1]
            print(f"\n📁 最新持久化文件: {latest_file.name}")
            
            # 加载任务列表
            print(f"\n2️⃣ 加载任务列表")
            tool2 = TodoWriteTool(project_root="./", persistence_dir="memory/todos")
            tool2.load_todos(str(latest_file))
            
            print(f"✅ 已加载任务列表")
            print(f"📝 摘要: {tool2.current_todos.summary}")
            print(f"📊 统计: {tool2.current_todos.get_stats()}")


def demo_5_recap_formats():
    """示例 5：Recap 格式 - 不同场景的输出"""
    print("\n" + "="*60)
    print("示例 5：Recap 格式 - 不同场景的输出")
    print("="*60)
    
    tool = TodoWriteTool(project_root="./", persistence_dir="memory/todos")
    
    # 场景 1：无任务
    print("\n📋 场景 1：无任务")
    response = tool.run({"action": "clear"})
    print(f"   {response.text}")
    
    # 场景 2：部分完成
    print("\n📋 场景 2：部分完成")
    response = tool.run({
        "todos": [
            {"content": "任务1", "status": "completed"},
            {"content": "任务2", "status": "in_progress"},
            {"content": "任务3", "status": "pending"}
        ]
    })
    print(f"   {response.text}")
    
    # 场景 3：全部完成
    print("\n📋 场景 3：全部完成")
    response = tool.run({
        "todos": [
            {"content": "任务1", "status": "completed"},
            {"content": "任务2", "status": "completed"}
        ]
    })
    print(f"   {response.text}")
    
    # 场景 4：多个待处理（截断）
    print("\n📋 场景 4：多个待处理（截断）")
    todos = [{"content": f"任务{i}", "status": "pending"} for i in range(1, 11)]
    todos[0]["status"] = "in_progress"
    response = tool.run({"todos": todos})
    print(f"   {response.text}")


if __name__ == "__main__":
    print("\n🚀 TodoWrite 进度管理工具示例")
    print("="*60)
    
    # 运行所有示例
    demo_1_basic_usage()
    demo_2_constraint_validation()
    demo_3_agent_integration()
    demo_4_persistence()
    demo_5_recap_formats()
    
    print("\n" + "="*60)
    print("✅ 所有示例运行完成")
    print("="*60)

