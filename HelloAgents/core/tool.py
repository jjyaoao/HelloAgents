# core/tool.py
# 这里我们定义 Agent 可以使用的工具。一个好的工具集能极大地扩展 Agent 的能力。

from langchain_core.tools import tool
from langchain_experimental.tools import PythonREPLTool
from tavily import TavilyClient
import os

# @tool 是一个装饰器，它可以轻松地将任何Python函数转换成一个LangChain工具。
# LangChain会自动推断出工具的输入参数和描述，用于让LLM理解如何使用这个工具。


# 此处是为了展示自定义封装的完整逻辑，实际使用中你可以直接使用langchain已经封装好的tavily工具
# 1、初始化网络搜索工具
@tool
def search_tavily(query: str):
    """
    使用Tavily搜索引擎在互联网上进行搜索，以查找最新、最相关的信息。
    当你需要回答关于时事、特定事实或任何你不知道的知识时，请使用此工具。
    
    Args:
        query (str): 你要搜索的关键词或问题。
    """
    # 从环境变量中获取Tavily API密钥
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    # 检查API密钥是否存在，如果不存在则抛出异常
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY 环境变量未设置！")
    
    # 初始化Tavily客户端
    client = TavilyClient(api_key=tavily_api_key)
    
    # 执行搜索。`include_answer=True` 表示我们希望Tavily不仅返回链接，还尝试直接给出一个总结性的答案。
    # `max_results=3` 指定我们最多需要3个搜索结果。
    response = client.search(query=query, search_depth="advanced", include_answer=True, max_results=3)
    
    # 从Tavily的返回结果中提取有用的信息，并格式化成一个清晰的字符串，这有助于LLM更好地理解搜索结果。
    # 我们将总结性的答案和每个具体的搜索结果都包含进来。
    formatted_result = f"总结性答案: {response['answer']}\n\n详细结果:\n"
    for result in response['results']:
        formatted_result += f"- 标题: {result['title']}\n  URL: {result['url']}\n  内容摘要: {result['content']}\n\n"
        
    # 返回格式化后的搜索结果字符串
    return formatted_result

# 2. 初始化 Python 代码执行器工具
# PythonREPLTool 可以执行 Python 代码片段，非常适合进行计算、数据分析等任务。
python_repl_tool = PythonREPLTool()

# 我们可以创建一个工具列表，方便地传递给Agent，如果你未来创建了更多的工具，比如计算器、代码执行器等，都可以加到这个列表里。
agent_tools = [search_tavily, python_repl_tool]