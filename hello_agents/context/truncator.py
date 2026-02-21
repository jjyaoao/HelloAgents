"""ObservationTruncator - 工具输出截断器

职责：
- 统一截断工具输出（避免每个工具自己实现）
- 支持多种截断方向（head/tail/head_tail）
- 返回 ToolResponse.partial() 状态
- 保存完整输出到文件
"""

import os
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class ObservationTruncator:
    """工具输出截断器
    
    特性：
    - 多方向截断（head/tail/head_tail）
    - 自动保存完整输出
    - 返回标准 ToolResponse.partial() 响应
    
    用法示例：
    ```python
    truncator = ObservationTruncator(
        max_lines=2000,
        max_bytes=51200,
        truncate_direction="head"
    )
    
    # 截断工具输出
    result = truncator.truncate(
        tool_name="search",
        output=long_output,
        metadata={"query": "test"}
    )
    
    # result 是一个字典，包含：
    # - truncated: bool
    # - preview: str (截断后的预览)
    # - full_output_path: str (完整输出路径)
    # - stats: dict (统计信息)
    ```
    """
    
    def __init__(
        self,
        max_lines: int = 2000,
        max_bytes: int = 51200,
        truncate_direction: str = "head",
        output_dir: str = "tool-output"
    ):
        """初始化截断器
        
        Args:
            max_lines: 最大保留行数
            max_bytes: 最大保留字节数
            truncate_direction: 截断方向 (head/tail/head_tail)
            output_dir: 完整输出保存目录
        """
        self.max_lines = max_lines
        self.max_bytes = max_bytes
        self.truncate_direction = truncate_direction
        self.output_dir = output_dir
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
    
    def truncate(
        self,
        tool_name: str,
        output: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """截断工具输出
        
        Args:
            tool_name: 工具名称
            output: 原始输出
            metadata: 元数据（可选）
        
        Returns:
            截断结果字典，包含：
            - truncated: bool - 是否被截断
            - preview: str - 预览内容
            - full_output_path: str - 完整输出路径（如果被截断）
            - stats: dict - 统计信息
        """
        start = time.time()
        lines = output.splitlines()
        bytes_size = len(output.encode('utf-8'))
        
        # 检查是否需要截断
        if len(lines) <= self.max_lines and bytes_size <= self.max_bytes:
            # 无需截断
            return {
                "truncated": False,
                "preview": output,
                "full_output_path": None,
                "stats": {
                    "original_lines": len(lines),
                    "original_bytes": bytes_size,
                    "time_ms": int((time.time() - start) * 1000)
                }
            }
        
        # 需要截断
        truncated_lines = self._truncate_lines(lines)
        preview = "\n".join(truncated_lines)
        truncated_bytes = len(preview.encode('utf-8'))
        
        # 保存完整输出
        output_path = self._save_full_output(tool_name, output, metadata)
        
        return {
            "truncated": True,
            "preview": preview,
            "full_output_path": output_path,
            "stats": {
                "direction": self.truncate_direction,
                "original_lines": len(lines),
                "original_bytes": bytes_size,
                "kept_lines": len(truncated_lines),
                "kept_bytes": truncated_bytes,
                "time_ms": int((time.time() - start) * 1000)
            }
        }
    
    def _truncate_lines(self, lines: list) -> list:
        """根据方向截断行
        
        Args:
            lines: 原始行列表
        
        Returns:
            截断后的行列表
        """
        if self.truncate_direction == "head":
            return lines[:self.max_lines]
        elif self.truncate_direction == "tail":
            return lines[-self.max_lines:]
        elif self.truncate_direction == "head_tail":
            half = self.max_lines // 2
            return lines[:half] + ["...(中间省略)..."] + lines[-half:]
        else:
            # 默认 head
            return lines[:self.max_lines]
    
    def _save_full_output(
        self,
        tool_name: str,
        output: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """保存完整输出到文件
        
        Args:
            tool_name: 工具名称
            output: 完整输出
            metadata: 元数据
        
        Returns:
            保存的文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"tool_{timestamp}_{tool_name}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        data = {
            "tool": tool_name,
            "output": output,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return filepath

