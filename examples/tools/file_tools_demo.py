"""文件操作工具使用示例

演示如何使用 ReadTool、WriteTool、EditTool 和 MultiEditTool
以及乐观锁机制的工作原理
"""

from hello_agents.tools.builtin import ReadTool, WriteTool, EditTool, MultiEditTool
from hello_agents.tools.registry import ToolRegistry
from hello_agents.tools.response import ToolStatus
import tempfile
from pathlib import Path
# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def demo_basic_file_operations():
    """演示基本文件操作"""
    print("=" * 60)
    print("示例 1: 基本文件操作")
    print("=" * 60)
    
    # 创建临时工作目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 创建工具注册表
        registry = ToolRegistry()
        
        # 注册文件工具
        read_tool = ReadTool(project_root=str(temp_path), registry=registry)
        write_tool = WriteTool(project_root=str(temp_path), registry=registry)
        edit_tool = EditTool(project_root=str(temp_path), registry=registry)
        
        registry.register_tool(read_tool)
        registry.register_tool(write_tool)
        registry.register_tool(edit_tool)
        
        # 1. 写入文件
        print("\n1. 创建新文件...")
        response = write_tool.run({
            "path": "config.py",
            "content": 'API_KEY = "test_key_123"\nDEBUG = False\nPORT = 8000\n'
        })
        print(f"   状态: {response.status.value}")
        print(f"   消息: {response.text}")
        
        # 2. 读取文件
        print("\n2. 读取文件...")
        response = read_tool.run({"path": "config.py"})
        print(f"   状态: {response.status.value}")
        print(f"   内容:\n{response.data['content']}")
        print(f"   元数据: mtime={response.data['file_mtime_ms']}, size={response.data['file_size_bytes']}")
        
        # 3. 编辑文件
        print("\n3. 编辑文件...")
        response = edit_tool.run({
            "path": "config.py",
            "old_string": "DEBUG = False",
            "new_string": "DEBUG = True"
        })
        print(f"   状态: {response.status.value}")
        print(f"   消息: {response.text}")
        
        # 4. 再次读取验证
        print("\n4. 验证修改...")
        response = read_tool.run({"path": "config.py"})
        print(f"   内容:\n{response.data['content']}")


def demo_optimistic_locking():
    """演示乐观锁机制"""
    print("\n" + "=" * 60)
    print("示例 2: 乐观锁冲突检测")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 创建工具注册表
        registry = ToolRegistry()
        
        # 注册文件工具
        read_tool = ReadTool(project_root=str(temp_path), registry=registry)
        write_tool = WriteTool(project_root=str(temp_path), registry=registry)
        edit_tool = EditTool(project_root=str(temp_path), registry=registry)
        
        registry.register_tool(read_tool)
        registry.register_tool(write_tool)
        registry.register_tool(edit_tool)
        
        # 1. 创建文件
        print("\n1. 创建初始文件...")
        test_file = temp_path / "data.txt"
        test_file.write_text("Original content", encoding='utf-8')
        
        # 2. Agent 读取文件（缓存元数据）
        print("\n2. Agent 读取文件（缓存元数据）...")
        response = read_tool.run({"path": "data.txt"})
        print(f"   状态: {response.status.value}")
        print(f"   缓存的 mtime: {response.data['file_mtime_ms']}")
        
        # 3. 模拟外部修改
        print("\n3. 外部进程修改文件...")
        import time
        time.sleep(0.1)  # 确保 mtime 变化
        test_file.write_text("Modified by external process", encoding='utf-8')
        print("   文件已被外部修改")
        
        # 4. Agent 尝试编辑（应该检测到冲突）
        print("\n4. Agent 尝试编辑（使用缓存的 mtime）...")
        cached_metadata = registry.get_read_metadata("data.txt")
        response = edit_tool.run({
            "path": "data.txt",
            "old_string": "Original content",
            "new_string": "My changes",
            "file_mtime_ms": cached_metadata["file_mtime_ms"]
        })
        
        if response.status == ToolStatus.ERROR:
            print(f"   ✅ 成功检测到冲突！")
            print(f"   错误码: {response.error_info['code']}")
            print(f"   错误消息: {response.error_info['message']}")
        else:
            print(f"   ❌ 未检测到冲突（不应该发生）")


def demo_multiedit():
    """演示批量编辑"""
    print("\n" + "=" * 60)
    print("示例 3: 批量编辑操作")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        registry = ToolRegistry()
        multiedit_tool = MultiEditTool(project_root=str(temp_path), registry=registry)
        registry.register_tool(multiedit_tool)
        
        # 创建配置文件
        config_file = temp_path / "settings.py"
        config_file.write_text(
            'API_KEY = "old_key"\n'
            'DEBUG = False\n'
            'PORT = 8000\n'
            'HOST = "localhost"\n',
            encoding='utf-8'
        )
        
        print("\n原始内容:")
        print(config_file.read_text(encoding='utf-8'))
        
        # 批量编辑
        print("\n执行批量编辑...")
        response = multiedit_tool.run({
            "path": "settings.py",
            "edits": [
                {"old_string": 'API_KEY = "old_key"', "new_string": 'API_KEY = "new_key_456"'},
                {"old_string": "DEBUG = False", "new_string": "DEBUG = True"},
                {"old_string": "PORT = 8000", "new_string": "PORT = 9000"}
            ]
        })
        
        print(f"状态: {response.status.value}")
        print(f"消息: {response.text}")
        print(f"修改数量: {response.data['num_edits']}")
        
        print("\n修改后内容:")
        print(config_file.read_text(encoding='utf-8'))


if __name__ == "__main__":
    demo_basic_file_operations()
    demo_optimistic_locking()
    demo_multiedit()
    
    print("\n" + "=" * 60)
    print("✅ 所有示例运行完成！")
    print("=" * 60)

