"""搜索工具"""

import os
from typing import Optional
from tavily import TavilyClient
from langchain_core.tools import tool

from ..base import Tool
from ...core.exceptions import ToolException

class SearchTool(Tool):
    """Tavily搜索工具"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            name="search_tavily",
            description="使用Tavily搜索引擎在互联网上进行搜索，以查找最新、最相关的信息。当你需要回答关于时事、特定事实或任何你不知道的知识时，请使用此工具。"
        )
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ToolException("TAVILY_API_KEY 环境变量未设置！")
        
        self.client = TavilyClient(api_key=self.api_key)
    
    def run(self, query: str) -> str:
        """
        执行搜索
        
        Args:
            query: 搜索查询
            
        Returns:
            搜索结果
        """
        try:
            response = self.client.search(
                query=query, 
                search_depth="advanced", 
                include_answer=True, 
                max_results=3
            )
            
            # 格式化搜索结果
            formatted_result = f"总结性答案: {response['answer']}\n\n详细结果:\n"
            for result in response['results']:
                formatted_result += f"- 标题: {result['title']}\n  URL: {result['url']}\n  内容摘要: {result['content']}\n\n"
            
            return formatted_result
        except Exception as e:
            raise ToolException(f"搜索失败: {str(e)}")

# 创建LangChain工具函数
@tool
def search_tavily(query: str) -> str:
    """
    使用Tavily搜索引擎在互联网上进行搜索，以查找最新、最相关的信息。
    当你需要回答关于时事、特定事实或任何你不知道的知识时，请使用此工具。
    
    Args:
        query (str): 你要搜索的关键词或问题。
    """
    tool = SearchTool()
    return tool.run(query)