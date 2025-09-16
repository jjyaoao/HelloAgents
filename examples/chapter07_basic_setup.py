"""
第7章示例：基础设置和简单Agent使用

本示例展示如何：
1. 配置HelloAgents环境
2. 创建简单的Agent
3. 进行基本对话
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from hello_agents import SimpleAgent, HelloAgentsLLM, Config

def main():
    """主函数"""
    print("=== HelloAgents 基础设置示例 ===\n")
    
    # 1. 创建配置
    config = Config(
        default_provider="deepseek",
        debug=True
    )
    
    # 2. 创建LLM实例
    llm = HelloAgentsLLM(
        provider="deepseek",
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY")
    )
    
    # 3. 创建简单Agent
    agent = SimpleAgent(
        name="助手",
        llm=llm,
        system_prompt="你是一个友好的AI助手，擅长回答各种问题。",
        config=config
    )
    
    # 4. 进行对话
    questions = [
        "你好，请介绍一下自己",
        "你能帮我做什么？",
        "请解释一下什么是人工智能"
    ]
    
    for question in questions:
        print(f"用户: {question}")
        response = agent.run(question)
        print(f"助手: {response}\n")
        print("-" * 50)

if __name__ == "__main__":
    main()