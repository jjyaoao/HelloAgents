"""计算器工具"""

from langchain_experimental.tools import PythonREPLTool
from langchain_core.tools import tool

from ..base import Tool
from ...core.exceptions import ToolException

class CalculatorTool(Tool):
    """Python计算器工具"""
    
    def __init__(self):
        super().__init__(
            name="python_calculator",
            description="执行Python代码进行计算、数据处理等操作。可以进行数学计算、字符串处理、数据分析等。"
        )
        self.python_repl = PythonREPLTool()
    
    def run(self, code: str) -> str:
        """
        执行Python代码
        
        Args:
            code: Python代码
            
        Returns:
            执行结果
        """
        try:
            return self.python_repl.run(code)
        except Exception as e:
            raise ToolException(f"代码执行失败: {str(e)}")

# 创建LangChain工具实例
python_repl_tool = PythonREPLTool()