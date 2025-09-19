"""网页浏览工具 - 纯Python实现"""

import requests
from bs4 import BeautifulSoup

from ..base import Tool
from ...core.exceptions import ToolException

class WebBrowserTool(Tool):
    """网页浏览工具"""
    
    def __init__(self):
        super().__init__(
            name="web_browser",
            description="浏览指定URL的网页内容，提取文本信息。"
        )
    
    def run(self, parameters: dict) -> str:
        """
        浏览网页
        
        Args:
            parameters: 包含url参数的字典
            
        Returns:
            网页文本内容
        """
        url = parameters.get("url", "")
        if not url:
            raise ToolException("URL不能为空")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 移除脚本和样式元素
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 获取文本
            text = soup.get_text()
            
            # 清理文本
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # 限制长度
            if len(text) > 2000:
                text = text[:2000] + "..."
            
            return text
        except Exception as e:
            raise ToolException(f"网页浏览失败: {str(e)}")
    
    def get_parameters(self):
        """获取工具参数定义"""
        from ..base import ToolParameter
        return [
            ToolParameter(
                name="url",
                type="string",
                description="要浏览的网页URL",
                required=True
            )
        ]

# 便捷函数
def browse_web(url: str) -> str:
    """
    浏览指定URL的网页内容
    
    Args:
        url: 网页URL
    """
    tool = WebBrowserTool()
    return tool.run({"url": url})
