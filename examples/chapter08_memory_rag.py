"""第八章：记忆与RAG工具增强Agent示例

展示如何使用MemoryTool和RAGTool来增强HelloAgents框架中的Agent，
实现记忆能力和知识检索功能。

本文件展示：
1. 🧠 SimpleAgent + MemoryTool：智能记忆助手
2. 🔍 SimpleAgent + RAGTool：知识检索助手
3. 🚀 Memory + RAG 组合：超级智能助手
4. 🔧 底层组件测试：全面验证各个模块

特色功能：
- 自动工具调用：Agent智能选择和使用工具
- 智能降级：自动适配不同环境和依赖
- 完整记忆系统：工作/情景/语义/感知记忆
- 强大RAG能力：文档处理、向量检索、知识问答
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools import MemoryTool, RAGTool


def demo_simple_agent_with_memory():
    """演示1: SimpleAgent + MemoryTool - 智能记忆助手"""
    print("🧠 演示1: SimpleAgent + 记忆工具（自动工具调用）")
    print("=" * 50)

    # 创建LLM
    llm = HelloAgentsLLM()

    # 创建记忆工具
    memory_tool = MemoryTool(
        user_id="demo_user_001",
        memory_types=["working", "episodic", "semantic"]
    )

    # 创建工具注册表
    tool_registry = ToolRegistry()
    tool_registry.register_tool(memory_tool)

    # 创建支持工具的SimpleAgent
    agent = SimpleAgent(
        name="记忆助手",
        llm=llm,
        tool_registry=tool_registry,
        system_prompt="""你是一个有记忆能力的AI助手。你能记住我们的对话历史和重要信息。

工具使用指南：
- 当用户提供个人信息时，使用 [TOOL_CALL:memory:store=信息内容] 存储
- 当需要回忆用户信息时，使用 [TOOL_CALL:memory:recall=查询关键词] 检索
- 当用户询问历史对话时，使用 [TOOL_CALL:memory:action=summary] 获取摘要

重要原则：
- 主动记录用户的重要信息（姓名、职业、兴趣等）
- 在回答时参考相关的历史记忆
- 提供个性化的建议和服务"""
    )

    print("💬 开始智能对话演示...")

    # 模拟多轮对话
    conversations = [
        "你好！我叫李明，是一名软件工程师，专门做Python开发",
        "我最近在学习机器学习，特别对深度学习感兴趣",
        "你能推荐一些Python机器学习的库吗？",
        "你还记得我的名字和职业吗？请结合我的背景给我一些学习建议"
    ]

    for i, user_input in enumerate(conversations, 1):
        print(f"\n--- 对话轮次 {i} ---")
        print(f"👤 用户: {user_input}")

        # SimpleAgent会自动使用memory工具
        response = agent.run(user_input)
        print(f"🤖 助手: {response}")

    # 显示记忆摘要
    print(f"\n📊 最终记忆系统状态:")
    summary = memory_tool.run({"action": "summary"})
    print(summary)

    return memory_tool

def demo_simple_agent_with_rag():
    """演示2: SimpleAgent + RAGTool - 智能知识助手"""
    print("\n\n🔍 演示2: SimpleAgent + RAG工具（自动工具调用）")
    print("=" * 50)

    # 创建LLM
    llm = HelloAgentsLLM()

    # 创建RAG工具 - 使用本地嵌入（推荐）
    rag_tool = RAGTool(
        knowledge_base_path="./demo_knowledge_base"
    )

    # 创建工具注册表
    tool_registry = ToolRegistry()
    tool_registry.register_tool(rag_tool)

    # 创建支持工具的SimpleAgent
    agent = SimpleAgent(
        name="知识助手",
        llm=llm,
        tool_registry=tool_registry,
        system_prompt="""你是一个专业的知识助手，可以从知识库中检索准确信息。

工具使用指南：
- 当用户询问技术问题时，使用 [TOOL_CALL:rag:search=关键词] 搜索知识库
- 基于检索到的信息提供准确回答
- 如果知识库中没有相关信息，诚实告知用户

工作流程：
1. 分析用户问题，提取关键词
2. 搜索知识库获取相关信息
3. 基于搜索结果给出专业回答"""
    )

    print("📚 正在构建知识库...")

    # 添加技术知识到RAG系统
    knowledge_items = [
        ("Python是一种高级编程语言，由Guido van Rossum在1989年开始开发，1991年首次发布。Python以其简洁的语法和强大的功能而闻名，广泛应用于Web开发、数据科学、人工智能等领域。", "python_intro"),
        ("机器学习是人工智能的一个分支，它使计算机能够在没有明确编程的情况下学习和改进。主要包括监督学习、无监督学习和强化学习三种类型。常用的Python机器学习库包括scikit-learn、pandas、numpy等。", "ml_basics"),
        ("深度学习是机器学习的一个子集，使用多层神经网络来模拟人脑的工作方式。深度学习在图像识别、自然语言处理、语音识别等领域取得了突破性进展。主要的深度学习框架包括TensorFlow、PyTorch、Keras等。", "deep_learning"),
        ("自然语言处理(NLP)是人工智能的一个重要分支，专注于计算机与人类语言之间的交互。NLP的主要任务包括文本分类、情感分析、机器翻译、问答系统等。常用的Python NLP库包括NLTK、spaCy、transformers等。", "nlp_intro")
    ]

    for content, doc_id in knowledge_items:
        result = rag_tool.run({"action": "add_text", "text": content, "document_id": doc_id})
        print(f"  ✅ 已添加: {doc_id}")

    print(f"\n📊 知识库统计:")
    stats = rag_tool.run({"action": "stats"})
    print(stats)

    # 测试智能问答
    queries = [
        "Python是什么时候发明的？谁发明的？",
        "什么是深度学习？它和机器学习有什么关系？",
        "推荐一些Python机器学习的库",
        "什么是量子计算？"  # 知识库中没有的信息
    ]

    print(f"\n💬 开始智能问答演示...")

    for i, query in enumerate(queries, 1):
        print(f"\n--- 查询 {i} ---")
        print(f"👤 用户: {query}")

        # SimpleAgent会自动使用RAG工具搜索并回答
        response = agent.run(query)
        print(f"🤖 助手: {response}")

    return rag_tool

def demo_combined_memory_and_rag():
    """演示3: Memory + RAG 组合 - 超级智能助手"""
    print("\n\n🚀 演示3: Memory + RAG 组合（超级智能助手）")
    print("=" * 50)

    # 创建LLM
    llm = HelloAgentsLLM()

    # 创建记忆工具
    memory_tool = MemoryTool(
        user_id="combo_user",
        memory_types=["working", "episodic", "semantic"]
    )

    # 创建RAG工具
    rag_tool = RAGTool(
        knowledge_base_path="./combo_knowledge_base",
        embedding_model="local"  # 使用本地嵌入，稳定可靠
    )

    # 创建工具注册表并注册两个工具
    tool_registry = ToolRegistry()
    tool_registry.register_tool(memory_tool)
    tool_registry.register_tool(rag_tool)

    # 创建超级智能助手
    agent = SimpleAgent(
        name="超级助手",
        llm=llm,
        tool_registry=tool_registry,
        system_prompt="""你是一个超级AI助手，同时具备记忆能力和知识检索能力。

工具使用指南：
- 记忆工具：[TOOL_CALL:memory:store=内容] 存储，[TOOL_CALL:memory:recall=查询] 检索
- 知识工具：[TOOL_CALL:rag:search=关键词] 搜索专业知识

智能策略：
1. 用户提供个人信息时，主动存储到记忆
2. 回答问题时，先检索相关记忆了解用户背景
3. 遇到技术问题时，搜索知识库获取准确信息
4. 结合个人记忆和专业知识提供个性化回答"""
    )

    print("📚 构建专业知识库...")

    # 添加编程学习知识
    knowledge_items = [
        ("Python编程最佳实践：1. 使用虚拟环境管理依赖 2. 遵循PEP8代码规范 3. 编写单元测试 4. 使用类型提示 5. 编写清晰的文档字符串", "python_best_practices"),
        ("初学者Python学习路径：基础语法 → 数据结构 → 面向对象编程 → 标准库 → 第三方库 → 项目实践", "python_learning_path"),
        ("Python数据科学工具栈：NumPy(数值计算) → Pandas(数据处理) → Matplotlib/Seaborn(可视化) → Scikit-learn(机器学习) → Jupyter Notebook(交互式开发)", "data_science_stack")
    ]

    for content, doc_id in knowledge_items:
        result = rag_tool.run({"action": "add_text", "text": content, "document_id": doc_id})
        print(f"  ✅ 已添加: {doc_id}")

    print(f"\n💬 开始超级智能对话演示...")

    # 模拟复杂的个性化学习对话
    conversations = [
        "你好！我是王小明，刚开始学习Python编程，目标是成为数据科学家",
        "我应该按什么顺序学习Python？",
        "我已经掌握了基础语法，下一步应该学什么？",
        "根据我的学习目标和进度，给我制定一个详细的学习计划"
    ]

    for i, user_input in enumerate(conversations, 1):
        print(f"\n--- 对话轮次 {i} ---")
        print(f"👤 用户: {user_input}")

        # SimpleAgent会智能地使用memory和rag工具
        response = agent.run(user_input)
        print(f"🤖 助手: {response}")

    print(f"\n📊 最终系统状态:")
    print("🧠 记忆系统:")
    memory_summary = memory_tool.run({"action": "summary"})
    print(memory_summary)

    print(f"\n🔍 知识库系统:")
    rag_stats = rag_tool.run({"action": "stats"})
    print(rag_stats)

    return memory_tool, rag_tool

def demo_four_memory_types():
    """演示4: 四种记忆类型详细展示"""
    print("\n\n🧠 演示4: 四种记忆类型详细展示")
    print("=" * 50)

    # 创建支持所有记忆类型的工具
    memory_tool = MemoryTool(
        user_id="memory_types_demo",
        memory_types=["working", "episodic", "semantic", "perceptual"]
    )

    print("📋 四种记忆类型特点和使用场景:")

    # 1. 工作记忆演示
    print("\n1️⃣ WorkingMemory (工作记忆) - 临时信息，容量有限")
    working_memories = [
        "用户刚才询问了Python函数的定义",
        "当前正在讨论面向对象编程概念",
        "用户表示对装饰器概念感到困惑",
        "需要为用户提供更多实例说明"
    ]

    for i, content in enumerate(working_memories):
        result = memory_tool.run({
            "action": "add",
            "content": content,
            "memory_type": "working",
            "importance": 0.5 + i * 0.1,
            "context_type": "conversation"
        })
        print(f"  ✅ 工作记忆 {i+1}: {content[:30]}...")

    # 2. 情景记忆演示
    print("\n2️⃣ EpisodicMemory (情景记忆) - 具体事件，时间序列")
    episodic_memories = [
        {
            "content": "2024年3月15日，用户张三首次使用系统学习Python",
            "event_type": "first_interaction",
            "location": "在线学习平台",
            "emotional_tone": "curious"
        },
        {
            "content": "用户完成了第一个Python练习：Hello World程序",
            "event_type": "milestone",
            "achievement": "first_program",
            "difficulty": "beginner"
        },
        {
            "content": "用户在学习列表操作时遇到困难，经过指导后理解了概念",
            "event_type": "problem_solving",
            "topic": "python_lists",
            "outcome": "success"
        }
    ]

    for i, memory_data in enumerate(episodic_memories):
        content = memory_data.pop("content")
        result = memory_tool.run({
            "action": "add",
            "content": content,
            "memory_type": "episodic",
            "importance": 0.7 + i * 0.05,
            **memory_data
        })
        print(f"  ✅ 情景记忆 {i+1}: {content[:40]}...")

    # 3. 语义记忆演示
    print("\n3️⃣ SemanticMemory (语义记忆) - 抽象知识，概念关联")
    semantic_memories = [
        {
            "content": "用户张三是计算机专业大二学生，Python基础薄弱",
            "category": "user_profile",
            "concepts": ["student", "computer_science", "python", "beginner"]
        },
        {
            "content": "Python是解释型、面向对象的高级编程语言",
            "category": "programming_concepts",
            "concepts": ["python", "interpreted", "oop", "high_level"]
        },
        {
            "content": "用户偏好通过实例学习，不喜欢纯理论讲解",
            "category": "learning_preferences",
            "concepts": ["practical_learning", "examples", "hands_on"]
        }
    ]

    for i, memory_data in enumerate(semantic_memories):
        content = memory_data.pop("content")
        result = memory_tool.run({
            "action": "add",
            "content": content,
            "memory_type": "semantic",
            "importance": 0.8 + i * 0.05,
            **memory_data
        })
        print(f"  ✅ 语义记忆 {i+1}: {content[:40]}...")

    # 4. 感知记忆演示
    print("\n4️⃣ PerceptualMemory (感知记忆) - 多模态信息")
    perceptual_memories = [
        {
            "content": "用户上传的Python代码截图，包含函数定义示例",
            "modality": "image",
            "file_path": "./uploads/python_function.png",
            "extracted_text": "def greet(name): return f'Hello, {name}!'"
        },
        {
            "content": "用户录制的语音问题：如何使用Python处理文件？",
            "modality": "audio",
            "file_path": "./audio/question_001.wav",
            "duration": 12.5,
            "language": "chinese"
        },
        {
            "content": "用户分享的编程教程视频链接",
            "modality": "video",
            "file_path": "https://example.com/python_tutorial.mp4",
            "topic": "python_basics"
        }
    ]

    for i, memory_data in enumerate(perceptual_memories):
        content = memory_data.pop("content")
        result = memory_tool.run({
            "action": "add",
            "content": content,
            "memory_type": "perceptual",
            "importance": 0.6 + i * 0.1,
            **memory_data
        })
        print(f"  ✅ 感知记忆 {i+1}: {content[:40]}...")

    # 演示跨类型搜索
    print("\n🔍 跨类型记忆搜索演示:")
    search_queries = [
        ("Python", "搜索所有与Python相关的记忆"),
        ("用户", "搜索用户相关信息"),
        ("学习", "搜索学习相关记忆")
    ]

    for query, desc in search_queries:
        print(f"\n  {desc} ('{query}'):")
        result = memory_tool.run({
            "action": "search",
            "query": query,
            "limit": 3,
            "min_importance": 0.5
        })
        print(f"    {result}")

    # 显示记忆统计
    print(f"\n📊 记忆系统统计:")
    stats = memory_tool.run({"action": "stats"})
    print(stats)

    summary = memory_tool.run({"action": "summary", "limit": 8})
    print(f"\n📋 记忆摘要:")
    print(summary)

    return memory_tool

def demo_tool_features():
    """演示5: 工具功能全面展示"""
    print("\n\n🔧 演示5: 工具功能全面展示")
    print("=" * 50)

    # 创建工具实例
    memory_tool = MemoryTool(user_id="feature_test")
    rag_tool = RAGTool(knowledge_base_path="./feature_test_kb", embedding_model="local")

    print("🧠 MemoryTool 完整操作演示:")

    # 展示记忆工具的各种操作
    actions = [
        ("添加工作记忆", {"action": "add", "content": "正在学习HelloAgents框架", "memory_type": "working", "importance": 0.8}),
        ("添加情景记忆", {"action": "add", "content": "用户首次使用系统", "memory_type": "episodic", "importance": 0.9}),
        ("添加语义记忆", {"action": "add", "content": "Python是编程语言", "memory_type": "semantic", "importance": 0.7}),
        ("搜索记忆", {"action": "search", "query": "Python", "limit": 3}),
        ("获取统计", {"action": "stats"}),
        ("获取摘要", {"action": "summary"}),
        ("记忆整合", {"action": "consolidate", "from_type": "working", "to_type": "episodic", "importance_threshold": 0.7}),
        ("记忆遗忘", {"action": "forget", "strategy": "importance_based", "threshold": 0.3})
    ]

    for desc, params in actions:
        print(f"\n  {desc}:")
        result = memory_tool.run(params)
        print(f"    {result}")

    print(f"\n🔍 RAGTool 完整操作演示:")

    # 展示RAG工具的各种操作
    rag_actions = [
        ("添加文本1", {"action": "add_text", "text": "机器学习是AI的重要分支", "document_id": "ml_intro"}),
        ("添加文本2", {"action": "add_text", "text": "深度学习使用神经网络", "document_id": "dl_intro"}),
        ("搜索知识", {"action": "search", "query": "机器学习", "limit": 2}),
        ("获取上下文", {"action": "get_context", "query": "深度学习", "limit": 2}),
        ("获取统计", {"action": "stats"}),
        ("更新文档", {"action": "update_document", "document_id": "ml_intro", "text": "机器学习是人工智能的核心分支"}),
        ("删除文档", {"action": "remove_document", "document_id": "dl_intro"})
    ]

    for desc, params in rag_actions:
        print(f"\n  {desc}:")
        try:
            result = rag_tool.run(params)
            print(f"    {result}")
        except Exception as e:
            print(f"    ⚠️ {desc}操作暂不支持: {str(e)}")

    return memory_tool, rag_tool

def demo_advanced_features():
    """演示6: 高级功能展示"""
    print("\n\n⚡ 演示6: 高级功能展示")
    print("=" * 50)

    print("🧠 记忆系统高级功能:")
    memory_tool = MemoryTool(user_id="advanced_user")

    # 演示记忆整合功能
    print("\n  1. 记忆整合演示:")
    # 添加一些工作记忆
    for i in range(3):
        memory_tool.run({
            "action": "add",
            "content": f"重要工作任务 {i+1}",
            "memory_type": "working",
            "importance": 0.8 + i * 0.05
        })

    # 整合到长期记忆
    result = memory_tool.run({
        "action": "consolidate",
        "from_type": "working",
        "to_type": "episodic",
        "importance_threshold": 0.7
    })
    print(f"    整合结果: {result}")

    print("\n🔍 RAG系统高级功能:")
    rag_tool = RAGTool(knowledge_base_path="./advanced_kb", embedding_model="local")

    # 演示批量添加和智能搜索
    print("\n  1. 批量知识添加:")
    knowledge_batch = [
        "人工智能包括机器学习、深度学习、自然语言处理等多个领域",
        "机器学习算法可以分为监督学习、无监督学习和强化学习",
        "深度学习是机器学习的一个子集，使用多层神经网络"
    ]

    for i, text in enumerate(knowledge_batch):
        result = rag_tool.run({
            "action": "add_text",
            "text": text,
            "document_id": f"ai_knowledge_{i}"
        })
        print(f"    添加文档 {i+1}: ✅")

    # 演示智能搜索
    print("\n  2. 智能搜索演示:")
    search_queries = ["什么是机器学习", "深度学习的特点"]

    for query in search_queries:
        result = rag_tool.run({
            "action": "search",
            "query": query,
            "limit": 2,
            "min_score": 0.1
        })
        print(f"    查询 '{query}': 找到相关内容")

    return memory_tool, rag_tool

def demo_enhanced_pdf_and_local_embedding():
    """演示7: 增强PDF处理和本地嵌入"""
    print("\n\n📄 演示7: 增强PDF处理和本地嵌入")
    print("=" * 50)

    # 确保使用本地嵌入
    print("🚀 配置本地嵌入模型...")
    os.environ["EMBED_MODEL_TYPE"] = "local"
    os.environ["EMBED_MODEL_NAME"] = "sentence-transformers/all-MiniLM-L6-v2"
    
    # 测试嵌入模型
    from hello_agents.memory.embedding import get_text_embedder, get_dimension
    embedder = get_text_embedder()
    dimension = get_dimension()
    print(f"✅ 嵌入模型类型: {embedder.__class__.__name__}")
    print(f"✅ 向量维度: {dimension}")
    
    # 创建RAG工具
    rag_tool = RAGTool(
        knowledge_base_path="./pdf_demo_kb",
        embedding_model="local",
        rag_namespace="pdf_test"
    )
    
    print(f"\n📊 初始知识库状态:")
    stats = rag_tool.run({"action": "stats", "namespace": "pdf_test"})
    print(stats)
    
    # 检查是否有PDF文件可以测试
    pdf_files = []
    test_files = ["Happy-LLM-0727.pdf"]
    for pdf_file in test_files:
        if os.path.exists(pdf_file):
            pdf_files.append(pdf_file)
    
    if pdf_files:
        print(f"\n📄 测试PDF文档处理...")
        pdf_file = pdf_files[0]
        print(f"处理文件: {pdf_file}")
        
        # 添加PDF文档（使用增强处理）
        result = rag_tool.run({
            "action": "add_document",
            "file_path": pdf_file,
            "namespace": "pdf_test"
        })
        print(result)
        
        # 显示处理后统计
        stats_after = rag_tool.run({"action": "stats", "namespace": "pdf_test"})
        print(f"\n📊 处理后知识库状态:")
        print(stats_after)
        
        # 测试智能问答
        test_questions = [
            "什么是大语言模型？",
            "如何训练神经网络？",
            "Python在机器学习中的应用",
            "深度学习的核心概念"
        ]
        
        print(f"\n💬 测试智能问答（基于PDF内容）...")
        for i, question in enumerate(test_questions[:2], 1):  # 测试前2个问题
            print(f"\n--- 问答 {i} ---")
            print(f"❓ 问题: {question}")
            
            answer = rag_tool.run({
                "action": "ask",
                "question": question,
                "namespace": "pdf_test",
                "include_citations": True
            })
            print(answer)
    else:
        # 如果没有PDF文件，演示文本添加和本地嵌入
        print(f"\n📝 没有PDF文件，演示文本添加和本地嵌入...")
        
        sample_texts = [
            "大语言模型（LLM）是基于Transformer架构的深度学习模型，通过海量文本数据预训练获得强大的自然语言理解和生成能力。",
            "机器学习是人工智能的核心分支，包括监督学习、无监督学习和强化学习三大范式，广泛应用于图像识别、自然语言处理等领域。",
            "Python是机器学习和数据科学的首选编程语言，拥有丰富的生态系统，包括NumPy、Pandas、Scikit-learn、TensorFlow等强大库。"
        ]
        
        for i, text in enumerate(sample_texts):
            result = rag_tool.run({
                "action": "add_text",
                "text": text,
                "namespace": "pdf_test",
                "document_id": f"sample_text_{i+1}"
            })
            print(f"✅ 添加文本 {i+1}: 成功")
        
        # 测试搜索和问答
        print(f"\n💬 测试本地嵌入搜索效果...")
        test_query = "什么是机器学习？"
        
        search_result = rag_tool.run({
            "action": "search",
            "query": test_query,
            "namespace": "pdf_test",
            "limit": 2
        })
        print(f"🔍 搜索结果:")
        print(search_result)
        
        ask_result = rag_tool.run({
            "action": "ask",
            "question": test_query,
            "namespace": "pdf_test"
        })
        print(f"\n🤖 智能问答:")
        print(ask_result)
    
    print(f"\n✅ 本地嵌入优势展示:")
    print("  🚀 快速响应：无网络延迟")
    print("  💰 零成本：无API调用费用")
    print("  🔒 隐私保护：数据不离开本地")
    print("  ⚡ 稳定可靠：避免网络超时")
    
    return rag_tool

def demo_real_world_scenario():
    """演示8: 真实场景应用"""
    print("\n\n🌟 演示8: 真实场景应用 - 个人学习助手")
    print("=" * 50)

    # 创建LLM
    llm = HelloAgentsLLM()

    # 创建完整的学习助手系统
    memory_tool = MemoryTool(user_id="student_001")
    rag_tool = RAGTool(knowledge_base_path="./learning_assistant_kb", embedding_model="local")

    # 注册工具
    tool_registry = ToolRegistry()
    tool_registry.register_tool(memory_tool)
    tool_registry.register_tool(rag_tool)

    # 创建学习助手
    learning_assistant = SimpleAgent(
        name="个人学习助手",
        llm=llm,
        tool_registry=tool_registry,
        system_prompt="""你是一个个人学习助手，帮助用户制定学习计划和回答学习问题。

核心能力：
1. 记住用户的学习目标、进度和偏好
2. 从知识库中检索准确的学习资料
3. 提供个性化的学习建议

工具使用：
- [TOOL_CALL:memory:store=信息] 记录用户信息
- [TOOL_CALL:memory:recall=查询] 回忆用户历史
- [TOOL_CALL:rag:search=关键词] 搜索学习资料

请主动记录用户的重要信息，并基于历史记录提供个性化建议。"""
    )

    print("📚 构建学习资料库...")

    # 添加学习资料
    learning_materials = [
        ("Python基础语法包括变量、数据类型、控制结构、函数等。建议初学者从变量和数据类型开始，逐步掌握列表、字典等数据结构。", "python_basics"),
        ("机器学习入门需要掌握数学基础（线性代数、概率统计）、Python编程、以及主要算法（线性回归、决策树、神经网络等）。", "ml_intro"),
        ("数据科学项目流程：问题定义 → 数据收集 → 数据清洗 → 探索性分析 → 建模 → 评估 → 部署。每个阶段都有对应的工具和技术。", "data_science_workflow"),
        ("编程学习最佳实践：多动手练习、阅读优秀代码、参与开源项目、定期复习基础知识、保持学习新技术的习惯。", "programming_best_practices")
    ]

    for content, doc_id in learning_materials:
        rag_tool.run({"action": "add_text", "text": content, "document_id": doc_id})
        print(f"  ✅ 已添加: {doc_id}")

    print(f"\n💬 模拟真实学习对话...")

    # 模拟真实的学习对话场景
    learning_conversation = [
        "你好！我是张三，计算机专业大三学生，想学习数据科学，但不知道从哪里开始",
        "我已经学过Python基础，现在想学机器学习，需要什么数学基础？",
        "我的数学基础一般，有什么推荐的学习路径吗？",
        "根据我的情况，能帮我制定一个3个月的学习计划吗？"
    ]

    for i, message in enumerate(learning_conversation, 1):
        print(f"\n--- 学习对话 {i} ---")
        print(f"👤 学生: {message}")

        response = learning_assistant.run(message)
        print(f"🎓 助手: {response}")

    print(f"\n📊 学习助手系统状态:")
    print("🧠 学生档案记忆:")
    memory_summary = memory_tool.run({"action": "summary"})
    print(memory_summary)

    print(f"\n📚 学习资料库:")
    rag_stats = rag_tool.run({"action": "stats"})
    print(rag_stats)

    return learning_assistant, memory_tool, rag_tool

def show_system_capabilities():
    """展示系统能力总结"""
    print("\n\n🎯 系统能力总结")
    print("=" * 50)

    print("🧠 MemoryTool 核心能力:")
    print("  ✅ 四种记忆类型：工作/情景/语义/感知记忆")
    print("  ✅ 完整操作集：add/search/summary/stats/update/remove/forget/consolidate")
    print("  ✅ 智能检索：基于内容和重要性的记忆搜索")
    print("  ✅ 自动管理：记忆整合、遗忘、容量控制")
    print("  ✅ 上下文感知：为查询提供相关记忆上下文")

    print(f"\n🔍 RAGTool 核心能力:")
    print("  ✅ 本地嵌入：sentence-transformers本地运行，无网络依赖")
    print("  ✅ 增强PDF处理：智能段落重组，保持语义完整性")
    print("  ✅ 智能降级：local → sentence-transformers → huggingface → tfidf")
    print("  ✅ 完整操作集：add_document/add_text/search/ask/stats/clear")
    print("  ✅ 文档处理：自动分块、元数据管理、多格式支持")
    print("  ✅ 向量检索：高效的相似度搜索和过滤（384维高质量向量）")
    print("  ✅ 知识管理：文档添加、命名空间隔离、统计、清理")

    print(f"\n🤖 SimpleAgent 增强能力:")
    print("  ✅ 自动工具调用：智能识别并使用合适的工具")
    print("  ✅ 参数解析：灵活的工具参数格式支持")
    print("  ✅ 错误处理：优雅的降级和错误恢复")
    print("  ✅ 向后兼容：不提供工具时保持原有行为")

    print(f"\n🎯 四种记忆类型特点:")
    print("  🔄 WorkingMemory：临时信息，容量限制，快速访问")
    print("  📅 EpisodicMemory：具体事件，时间序列，上下文丰富")
    print("  🧩 SemanticMemory：抽象知识，概念关联，跨场景适用")
    print("  🎭 PerceptualMemory：多模态信息，跨模态检索，特征提取")

    print(f"\n🚀 组合应用场景:")
    print("  ✅ 个人助手：记住用户偏好，提供个性化服务")
    print("  ✅ 知识问答：基于专业知识库的准确回答")
    print("  ✅ 学习辅导：个性化学习计划和进度跟踪")
    print("  ✅ 客服系统：记住客户历史，提供专业支持")
    print("  ✅ 多模态AI：处理文本、图像、音频等多种信息")

    print(f"\n💡 技术亮点:")
    print("  ✅ 本地优先：优先使用本地模型，避免网络依赖和超时")
    print("  ✅ 增强PDF处理：解决文档转换信息损失问题")
    print("  ✅ 智能降级机制：确保在任何环境下都能正常工作")
    print("  ✅ 工具化封装：完全符合HelloAgents框架规范")
    print("  ✅ 协同工作：Memory和RAG系统的深度集成")

def main():
    """主函数 - 第八章记忆与RAG工具演示"""
    print("🎯 第八章：记忆与RAG工具增强Agent演示")
    print("展示如何使用MemoryTool和RAGTool增强HelloAgents框架")
    print("=" * 70)

    # 询问用户想要运行哪种演示
    print("\n请选择演示类型：")
    print("1. 🧠 记忆助手 - SimpleAgent + MemoryTool")
    print("2. 🔍 知识助手 - SimpleAgent + RAGTool")
    print("3. 🚀 超级助手 - Memory + RAG 组合")
    print("4. 🧠 四种记忆类型 - 详细展示工作/情景/语义/感知记忆")
    print("5. 🔧 功能展示 - 工具能力全面演示")
    print("6. ⚡ 高级功能 - 记忆整合和智能搜索")
    print("7. 📄 PDF处理 - 增强PDF处理和本地嵌入演示")
    print("8. 🌟 真实场景 - 个人学习助手应用")
    print("9. 🎪 完整演示 - 运行所有演示")

    try:
        choice = input("\n请输入选择 (1-9): ").strip()

        if choice == "1" or choice == "9":
            demo_simple_agent_with_memory()

        if choice == "2" or choice == "9":
            demo_simple_agent_with_rag()

        if choice == "3" or choice == "9":
            demo_combined_memory_and_rag()

        if choice == "4" or choice == "9":
            demo_four_memory_types()

        if choice == "5" or choice == "9":
            demo_tool_features()

        if choice == "6" or choice == "9":
            demo_advanced_features()

        if choice == "7" or choice == "9":
            demo_enhanced_pdf_and_local_embedding()

        if choice == "8" or choice == "9":
            demo_real_world_scenario()

        if choice == "9":
            show_system_capabilities()

        print("\n" + "=" * 70)
        print("🎉 演示完成！")

        # 显示对应的总结
        if choice == "1":
            print("\n💡 记忆助手特点:")
            print("✅ 自动记录用户信息和对话历史")
            print("✅ 智能检索相关记忆提供上下文")
            print("✅ 支持多种记忆类型和重要性评估")
        elif choice == "2":
            print("\n💡 知识助手特点:")
            print("✅ 从专业知识库检索准确信息")
            print("✅ 智能降级确保系统稳定运行")
            print("✅ 支持文档管理和统计分析")
        elif choice == "3":
            print("\n💡 超级助手特点:")
            print("✅ 记忆+知识双重能力")
            print("✅ 个性化专业服务")
            print("✅ 智能工具协同工作")
        elif choice == "4":
            print("\n💡 四种记忆类型特点:")
            print("✅ 工作记忆：临时信息，快速访问")
            print("✅ 情景记忆：具体事件，时间序列")
            print("✅ 语义记忆：抽象知识，概念关联")
            print("✅ 感知记忆：多模态信息，跨模态检索")
        elif choice in ["5", "6"]:
            print("\n💡 高级功能亮点:")
            print("✅ 完整的工具生态系统")
            print("✅ 智能记忆管理和知识检索")
            print("✅ 灵活的扩展机制")
        elif choice == "7":
            print("\n💡 PDF处理和本地嵌入特点:")
            print("✅ 增强PDF处理：智能段落重组和内容清理")
            print("✅ 本地嵌入：无网络依赖，稳定可靠")
            print("✅ 高质量向量：384维sentence-transformers")
            print("✅ 实时问答：基于优化后的文档内容")
        elif choice == "8":
            print("\n💡 真实场景应用特点:")
            print("✅ 个性化学习助手")
            print("✅ 记忆和知识双重能力")
            print("✅ 智能学习规划和进度跟踪")
        elif choice == "9":
            print("\n🎯 完整演示总结:")
            print("✅ 基础功能：Memory + RAG 工具集成")
            print("✅ 记忆类型：四种记忆类型的详细展示")
            print("✅ 高级功能：智能记忆管理和知识检索")
            print("✅ 实际应用：个人学习助手等真实场景")
            print("✅ 系统能力：完整的工具生态和扩展机制")
            print("\n🚀 HelloAgents框架展现了强大的AI工具集成能力！")

        print("✅ HelloAgents记忆与RAG系统运行正常")

    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断演示")
    except Exception as e:
        print(f"❌ 演示过程中出现错误: {str(e)}")
        print("请检查依赖是否正确安装")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()