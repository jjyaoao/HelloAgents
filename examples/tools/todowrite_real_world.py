"""TodoWrite 实战案例：复杂项目开发

演示用 TodoWrite 保存、恢复和更新项目进度；不执行实际开发任务。

场景：开发一个完整的博客系统
- 用户管理
- 文章管理
- 评论系统
- 搜索功能
"""

from hello_agents.tools.builtin import TodoWriteTool
from dotenv import load_dotenv
import time

load_dotenv()


class BlogProjectManager:
    """博客项目管理器"""
    
    def __init__(self):
        self.tool = TodoWriteTool(
            project_root="./",
            persistence_dir="memory/todos"
        )
        
    def create_project_plan(self):
        """创建项目计划"""
        print("\n" + "="*60)
        print("📋 创建博客系统开发计划")
        print("="*60)
        
        response = self.tool.run({
            "summary": "开发完整的博客系统",
            "todos": [
                {"content": "设计数据库模型（User, Post, Comment）", "status": "pending"},
                {"content": "实现用户注册和登录", "status": "pending"},
                {"content": "实现文章 CRUD 功能", "status": "pending"},
                {"content": "实现评论系统", "status": "pending"},
                {"content": "实现全文搜索", "status": "pending"},
                {"content": "编写单元测试", "status": "pending"},
                {"content": "部署到生产环境", "status": "pending"}
            ]
        })
        
        print(f"\n✅ 项目计划已创建")
        print(f"📊 {response.text}")
        return response
    
    def start_task(self, task_index: int):
        """开始某个任务"""
        # 获取当前任务列表
        todos = self.tool.current_todos.todos
        
        # 更新状态
        for i, todo in enumerate(todos):
            if i == task_index:
                todo.status = "in_progress"
            elif todo.status == "in_progress":
                todo.status = "pending"  # 将之前的 in_progress 改为 pending
        
        # 提交更新
        response = self.tool.run({
            "summary": self.tool.current_todos.summary,
            "todos": [
                {
                    "content": t.content,
                    "status": t.status,
                    "created_at": t.created_at,
                    "updated_at": t.updated_at
                }
                for t in todos
            ]
        })
        
        print(f"\n🚀 开始任务: {todos[task_index].content}")
        print(f"📊 {response.text}")
        return response
    
    def complete_current_task(self):
        """完成当前任务"""
        todos = self.tool.current_todos.todos
        
        # 找到 in_progress 的任务并标记为 completed
        for todo in todos:
            if todo.status == "in_progress":
                todo.status = "completed"
                print(f"\n✅ 完成任务: {todo.content}")
                break
        
        # 提交更新
        response = self.tool.run({
            "summary": self.tool.current_todos.summary,
            "todos": [
                {
                    "content": t.content,
                    "status": t.status,
                    "created_at": t.created_at,
                    "updated_at": t.updated_at
                }
                for t in todos
            ]
        })
        
        print(f"📊 {response.text}")
        return response
    
    def simulate_development(self):
        """模拟开发过程"""
        print("\n" + "="*60)
        print("🎬 模拟开发过程")
        print("="*60)
        
        # 1. 创建计划
        self.create_project_plan()
        time.sleep(1)
        
        # 2. 开始第一个任务：设计数据库
        print("\n" + "-"*60)
        print("第 1 天：设计数据库模型")
        print("-"*60)
        self.start_task(0)
        time.sleep(1)
        self.complete_current_task()
        
        # 3. 开始第二个任务：用户注册登录
        print("\n" + "-"*60)
        print("第 2 天：实现用户注册和登录")
        print("-"*60)
        self.start_task(1)
        time.sleep(1)
        self.complete_current_task()
        
        # 4. 开始第三个任务：文章 CRUD
        print("\n" + "-"*60)
        print("第 3 天：实现文章 CRUD 功能")
        print("-"*60)
        self.start_task(2)
        time.sleep(1)
        self.complete_current_task()
        
        # 5. 开始第四个任务：评论系统
        print("\n" + "-"*60)
        print("第 4 天：实现评论系统")
        print("-"*60)
        self.start_task(3)
        time.sleep(1)
        self.complete_current_task()
        
        # 6. 开始第五个任务：全文搜索
        print("\n" + "-"*60)
        print("第 5 天：实现全文搜索")
        print("-"*60)
        self.start_task(4)
        time.sleep(1)
        self.complete_current_task()
        
        # 7. 开始第六个任务：单元测试
        print("\n" + "-"*60)
        print("第 6 天：编写单元测试")
        print("-"*60)
        self.start_task(5)
        time.sleep(1)
        self.complete_current_task()
        
        # 8. 开始最后一个任务：部署
        print("\n" + "-"*60)
        print("第 7 天：部署到生产环境")
        print("-"*60)
        self.start_task(6)
        time.sleep(1)
        self.complete_current_task()
        
        print("\n" + "="*60)
        print("🎉 项目开发完成！")
        print("="*60)


def demo_interrupt_and_resume():
    """演示中断和恢复"""
    print("\n" + "="*60)
    print("🔄 演示中断和恢复")
    print("="*60)
    
    manager = BlogProjectManager()
    
    # 创建计划
    manager.create_project_plan()
    
    # 开始第一个任务
    print("\n📍 开始第一个任务...")
    manager.start_task(0)
    
    # 模拟中断（保存状态）
    print("\n⚠️ 模拟中断（网络断开、程序崩溃等）")
    print("💾 任务状态已自动保存到 memory/todos/")
    
    # 模拟恢复
    print("\n🔄 恢复工作...")
    from pathlib import Path
    todos_dir = Path("memory/todos")
    files = sorted(todos_dir.glob("todoList-*.json"))
    if files:
        latest_file = files[-1]
        print(f"📂 加载最新状态: {latest_file.name}")
        
        # 创建新的管理器并加载状态
        manager2 = BlogProjectManager()
        manager2.tool.load_todos(str(latest_file))
        
        print(f"✅ 状态已恢复")
        print(f"📊 当前进度: {manager2.tool.current_todos.get_stats()}")
        
        # 继续工作
        print("\n▶️ 继续完成当前任务...")
        manager2.complete_current_task()


def demo_multi_phase_project():
    """演示多阶段项目"""
    print("\n" + "="*60)
    print("🎯 演示多阶段项目管理")
    print("="*60)
    
    tool = TodoWriteTool(project_root="./", persistence_dir="memory/todos")
    
    # 阶段 1：MVP 开发
    print("\n📌 阶段 1：MVP 开发")
    response = tool.run({
        "summary": "博客系统 MVP 开发",
        "todos": [
            {"content": "实现基础用户功能", "status": "completed"},
            {"content": "实现文章发布", "status": "completed"},
            {"content": "实现简单评论", "status": "in_progress"}
        ]
    })
    print(f"   {response.text}")
    
    # 完成 MVP
    print("\n✅ MVP 开发完成")
    response = tool.run({
        "summary": "博客系统 MVP 开发",
        "todos": [
            {"content": "实现基础用户功能", "status": "completed"},
            {"content": "实现文章发布", "status": "completed"},
            {"content": "实现简单评论", "status": "completed"}
        ]
    })
    print(f"   {response.text}")
    
    # 阶段 2：功能增强
    print("\n📌 阶段 2：功能增强")
    response = tool.run({
        "summary": "博客系统功能增强",
        "todos": [
            {"content": "添加富文本编辑器", "status": "in_progress"},
            {"content": "实现图片上传", "status": "pending"},
            {"content": "添加标签系统", "status": "pending"},
            {"content": "实现文章分类", "status": "pending"}
        ]
    })
    print(f"   {response.text}")


if __name__ == "__main__":
    print("\n🚀 TodoWrite 实战案例：复杂项目开发")
    
    # 案例 1：完整开发流程
    manager = BlogProjectManager()
    manager.simulate_development()
    
    # 案例 2：中断和恢复
    demo_interrupt_and_resume()
    
    # 案例 3：多阶段项目
    demo_multi_phase_project()
    
    print("\n" + "="*60)
    print("✅ 所有案例演示完成")
    print("="*60)

