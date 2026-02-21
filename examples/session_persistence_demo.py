"""会话持久化使用示例

演示如何使用 SessionStore 保存和恢复会话：
- 手动保存和加载会话
- 环境一致性检查
- 自动保存机制
- 异常保护
"""

from hello_agents import ReActAgent, SimpleAgent
from hello_agents.core.llm import HelloAgentsLLM
from hello_agents.core.config import Config
from hello_agents.tools.registry import ToolRegistry
from hello_agents.tools.builtin import ReadTool, WriteTool
from hello_agents.core.message import Message
import tempfile
from pathlib import Path
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()


def demo_basic_save_load():
    """演示基本的保存和加载"""
    print("=" * 60)
    print("示例 1: 基本保存和加载")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建 Agent（启用会话持久化）
        config = Config(
            session_enabled=True,
            session_dir=temp_dir,
            trace_enabled=False
        )
        
        llm = HelloAgentsLLM()
        agent = SimpleAgent("assistant", llm, config=config)
        
        # 添加一些对话历史
        print("\n添加对话历史...")
        agent.add_message(Message("你好", "user"))
        agent.add_message(Message("你好！有什么可以帮助你的？", "assistant"))
        agent.add_message(Message("介绍一下你自己", "user"))
        agent.add_message(Message("我是 AI 助手", "assistant"))
        
        print(f"当前历史长度: {len(agent.get_history())}")
        
        # 保存会话
        print("\n保存会话...")
        filepath = agent.save_session("demo-session")
        print(f"会话已保存: {filepath}")
        
        # 清空历史
        agent.clear_history()
        print(f"清空后历史长度: {len(agent.get_history())}")
        
        # 加载会话
        print("\n加载会话...")
        agent.load_session(filepath)
        print(f"恢复后历史长度: {len(agent.get_history())}")
        
        # 验证内容
        history = agent.get_history()
        assert len(history) == 4
        assert history[0].content == "你好"
        
        print("\n✅ 基本保存和加载测试完成")


def demo_list_sessions():
    """演示列出所有会话"""
    print("\n" + "=" * 60)
    print("示例 2: 列出所有会话")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config(
            session_enabled=True,
            session_dir=temp_dir,
            trace_enabled=False
        )
        
        llm = HelloAgentsLLM()
        agent = SimpleAgent("assistant", llm, config=config)
        
        # 创建多个会话
        print("\n创建多个会话...")
        for i in range(3):
            agent.add_message(Message(f"消息 {i+1}", "user"))
            agent.save_session(f"session-{i+1}")
            agent.clear_history()
        
        # 列出所有会话
        print("\n列出所有会话:")
        sessions = agent.list_sessions()
        
        for session in sessions:
            print(f"\n  会话 ID: {session['session_id']}")
            print(f"  创建时间: {session['created_at']}")
            print(f"  保存时间: {session['saved_at']}")
            print(f"  文件路径: {Path(session['filepath']).name}")
        
        assert len(sessions) == 3
        print("\n✅ 列出会话测试完成")


def demo_consistency_check():
    """演示环境一致性检查"""
    print("\n" + "=" * 60)
    print("示例 3: 环境一致性检查")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建第一个 Agent 并保存会话
        config1 = Config(
            session_enabled=True,
            session_dir=temp_dir,
            trace_enabled=False
        )
        
        llm = HelloAgentsLLM()
        registry1 = ToolRegistry()
        registry1.register_tool(ReadTool(project_root="./"))
        
        agent1 = ReActAgent("assistant", llm, tool_registry=registry1, config=config1)
        agent1.add_message(Message("测试消息", "user"))
        
        filepath = agent1.save_session("consistency-test")
        print(f"\n会话已保存: {Path(filepath).name}")
        
        # 创建第二个 Agent（不同的工具配置）
        registry2 = ToolRegistry()
        registry2.register_tool(ReadTool(project_root="./"))
        registry2.register_tool(WriteTool(project_root="./"))  # 新增工具
        
        agent2 = ReActAgent("assistant", llm, tool_registry=registry2, config=config1)
        
        # 加载会话（会检测到工具变化）
        print("\n加载会话（工具配置已变化）...")
        agent2.load_session(filepath, check_consistency=True)
        
        # 会话仍然可以加载，但会有警告
        assert len(agent2.get_history()) == 1
        
        print("\n✅ 环境一致性检查完成")


def demo_auto_save():
    """演示自动保存"""
    print("\n" + "=" * 60)
    print("示例 4: 自动保存机制")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 启用自动保存（每 3 条消息保存一次）
        config = Config(
            session_enabled=True,
            session_dir=temp_dir,
            auto_save_enabled=True,
            auto_save_interval=3,
            trace_enabled=False
        )
        
        llm = HelloAgentsLLM()
        agent = SimpleAgent("assistant", llm, config=config)
        
        print("\n添加消息（每 3 条自动保存）...")
        
        # 添加 7 条消息（应该触发 2 次自动保存）
        for i in range(7):
            agent.add_message(Message(f"消息 {i+1}", "user"))
            print(f"  添加消息 {i+1}")
        
        # 检查自动保存的文件
        session_files = list(Path(temp_dir).glob("session-auto*.json"))
        print(f"\n自动保存文件数: {len(session_files)}")
        
        # 至少应该有 1 个自动保存文件
        assert len(session_files) >= 1
        
        print("\n✅ 自动保存测试完成")


def demo_metadata_tracking():
    """演示元数据追踪"""
    print("\n" + "=" * 60)
    print("示例 5: 会话元数据追踪")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config(
            session_enabled=True,
            session_dir=temp_dir,
            trace_enabled=False
        )
        
        llm = HelloAgentsLLM()
        agent = SimpleAgent("assistant", llm, config=config)
        
        # 添加消息
        for i in range(5):
            agent.add_message(Message(f"消息 {i+1}", "user"))
            agent.add_message(Message(f"回复 {i+1}", "assistant"))
        
        # 保存会话
        filepath = agent.save_session("metadata-test")
        
        # 加载会话数据
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        print("\n会话元数据:")
        print(f"  会话 ID: {session_data['session_id']}")
        print(f"  创建时间: {session_data['created_at']}")
        print(f"  保存时间: {session_data['saved_at']}")
        print(f"  Agent 名称: {session_data['agent_config']['name']}")
        print(f"  历史消息数: {len(session_data['history'])}")
        
        metadata = session_data.get('metadata', {})
        print(f"\n统计信息:")
        print(f"  总 Tokens: {metadata.get('total_tokens', 0)}")
        print(f"  总步数: {metadata.get('total_steps', 0)}")
        print(f"  持续时间: {metadata.get('duration_seconds', 0)} 秒")
        
        print("\n✅ 元数据追踪测试完成")


if __name__ == "__main__":
    demo_basic_save_load()
    demo_list_sessions()
    demo_consistency_check()
    demo_auto_save()
    demo_metadata_tracking()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成！")
    print("=" * 60)

