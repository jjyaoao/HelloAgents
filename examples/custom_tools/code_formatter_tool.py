"""代码格式化工具 - 复杂逻辑示例

这是一个代码格式化工具示例，展示如何：
- 处理复杂的文本逻辑
- 实现多种格式化选项
- 提供详细的验证和错误处理
"""

from typing import Dict, Any, List
import re
import logging
from hello_agents.tools import Tool, ToolParameter, ToolResponse
from hello_agents.tools.errors import ToolErrorCode

logger = logging.getLogger(__name__)


class CodeFormatterTool(Tool):
    """代码格式化工具
    
    功能:
        - 格式化 Python 代码
        - 支持多种格式化选项（缩进、行宽等）
        - 自动检测和修复常见问题
    
    使用示例:
        >>> tool = CodeFormatterTool()
        >>> response = tool.run({
        ...     "code": "def hello():print('hi')",
        ...     "indent": 4,
        ...     "max_line_length": 80
        ... })
    """
    
    def __init__(self):
        """初始化代码格式化工具"""
        super().__init__(
            name="code_formatter",
            description="格式化 Python 代码，支持自定义缩进和行宽"
        )
        
        logger.info("初始化代码格式化工具")
    
    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """执行代码格式化
        
        Args:
            parameters: 包含 code, indent, max_line_length 等参数
        
        Returns:
            ToolResponse: 格式化结果
        """
        # 1. 参数验证
        code = parameters.get("code", "").strip()
        if not code:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="参数 'code' 不能为空"
            )
        
        indent = parameters.get("indent", 4)
        max_line_length = parameters.get("max_line_length", 80)
        fix_imports = parameters.get("fix_imports", True)
        
        # 验证参数范围
        if not isinstance(indent, int) or indent < 1 or indent > 8:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="参数 'indent' 必须是 1-8 之间的整数"
            )
        
        if not isinstance(max_line_length, int) or max_line_length < 40:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_PARAM,
                message="参数 'max_line_length' 必须大于等于 40"
            )
        
        logger.info(f"格式化代码，缩进: {indent}, 最大行宽: {max_line_length}")
        
        # 2. 执行格式化
        try:
            formatted_code, changes = self._format_code(
                code, indent, max_line_length, fix_imports
            )
            
            # 3. 构建响应
            if changes:
                change_summary = ", ".join(changes)
                text = f"代码格式化完成，应用了以下修改: {change_summary}"
            else:
                text = "代码已经符合格式规范，无需修改"
            
            return ToolResponse.success(
                text=text,
                data={
                    "original_code": code,
                    "formatted_code": formatted_code,
                    "changes": changes,
                    "original_lines": len(code.split('\n')),
                    "formatted_lines": len(formatted_code.split('\n'))
                },
                stats={
                    "changes_count": len(changes)
                }
            )
        
        except SyntaxError as e:
            return ToolResponse.error(
                code=ToolErrorCode.INVALID_FORMAT,
                message=f"代码语法错误: {str(e)}",
                context={"code": code}
            )
        
        except Exception as e:
            logger.error(f"格式化失败: {e}")
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"格式化失败: {str(e)}",
                context={"code": code}
            )
    
    def get_parameters(self) -> List[ToolParameter]:
        """定义工具参数"""
        return [
            ToolParameter(
                name="code",
                type="string",
                description="要格式化的 Python 代码",
                required=True
            ),
            ToolParameter(
                name="indent",
                type="integer",
                description="缩进空格数（1-8）",
                required=False,
                default=4
            ),
            ToolParameter(
                name="max_line_length",
                type="integer",
                description="最大行宽（>=40）",
                required=False,
                default=80
            ),
            ToolParameter(
                name="fix_imports",
                type="boolean",
                description="是否自动修复 import 语句",
                required=False,
                default=True
            )
        ]
    
    def _format_code(
        self, 
        code: str, 
        indent: int, 
        max_line_length: int,
        fix_imports: bool
    ) -> tuple[str, List[str]]:
        """格式化代码的核心逻辑
        
        Returns:
            (formatted_code, changes): 格式化后的代码和变更列表
        """
        changes = []
        lines = code.split('\n')
        formatted_lines = []
        
        # 1. 修复缩进
        for line in lines:
            stripped = line.lstrip()
            if not stripped:
                formatted_lines.append("")
                continue
            
            # 计算当前缩进级别
            current_indent = len(line) - len(stripped)
            indent_level = current_indent // indent
            
            # 重新应用缩进
            new_line = " " * (indent_level * indent) + stripped
            formatted_lines.append(new_line)
        
        if formatted_lines != lines:
            changes.append("修复缩进")
        
        # 2. 修复 import 语句
        if fix_imports:
            import_fixed = self._fix_imports(formatted_lines)
            if import_fixed != formatted_lines:
                formatted_lines = import_fixed
                changes.append("整理 import 语句")
        
        # 3. 移除多余空行
        cleaned_lines = self._remove_extra_blank_lines(formatted_lines)
        if cleaned_lines != formatted_lines:
            formatted_lines = cleaned_lines
            changes.append("移除多余空行")
        
        # 4. 检查行宽（仅警告，不自动修复）
        long_lines = [i+1 for i, line in enumerate(formatted_lines) if len(line) > max_line_length]
        if long_lines:
            changes.append(f"检测到 {len(long_lines)} 行超过最大行宽")
        
        formatted_code = '\n'.join(formatted_lines)
        return formatted_code, changes
    
    def _fix_imports(self, lines: List[str]) -> List[str]:
        """整理 import 语句"""
        import_lines = []
        from_import_lines = []
        other_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('import '):
                import_lines.append(line)
            elif stripped.startswith('from '):
                from_import_lines.append(line)
            else:
                other_lines.append(line)
        
        # 排序 import 语句
        import_lines.sort()
        from_import_lines.sort()
        
        # 重新组合
        result = []
        if import_lines:
            result.extend(import_lines)
        if from_import_lines:
            if import_lines:
                result.append("")  # 添加空行分隔
            result.extend(from_import_lines)
        if other_lines:
            if import_lines or from_import_lines:
                result.append("")
                result.append("")  # 两个空行分隔
            result.extend(other_lines)
        
        return result
    
    def _remove_extra_blank_lines(self, lines: List[str]) -> List[str]:
        """移除多余的空行（最多保留 2 个连续空行）"""
        result = []
        blank_count = 0
        
        for line in lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 2:
                    result.append(line)
            else:
                blank_count = 0
                result.append(line)
        
        return result


# ============================================
# 使用示例
# ============================================

if __name__ == "__main__":
    from hello_agents import ToolRegistry
    
    # 1. 创建工具
    print("=== 创建代码格式化工具 ===")
    tool = CodeFormatterTool()
    
    # 2. 测试基本格式化
    print("\n=== 测试基本格式化 ===")
    messy_code = """
import os
from typing import Dict
import sys


def hello(  ):
        print(  'hello'  )


class MyClass:
  def __init__(self):
    self.value=42
"""
    
    response = tool.run({
        "code": messy_code,
        "indent": 4,
        "max_line_length": 80
    })
    
    print(f"状态: {response.status}")
    print(f"变更: {response.data['changes']}")
    print(f"\n格式化后的代码:\n{response.data['formatted_code']}")
    print()
    
    # 3. 测试错误处理
    print("=== 测试错误处理 ===")
    response2 = tool.run({"code": ""})
    print(f"状态: {response2.status}")
    print(f"错误: {response2.error_info}")

