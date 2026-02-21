"""熔断器机制 - 防止工具连续失败导致的死循环"""

import time
from typing import Dict, Optional
from collections import defaultdict
from .response import ToolResponse, ToolStatus


class CircuitBreaker:
    """
    工具熔断器

    特性：
    - 连续失败自动禁用工具
    - 超时自动恢复
    - 基于 ToolResponse 协议判断错误

    状态机：
    Closed (正常) → Open (熔断) → Closed (恢复)
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 300,
        enabled: bool = True
    ):
        """
        初始化熔断器

        Args:
            failure_threshold: 连续失败多少次后熔断（默认 3）
            recovery_timeout: 熔断后恢复时间（秒，默认 300）
            enabled: 是否启用熔断器（默认 True）
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.enabled = enabled

        # 失败计数（每个工具）
        self.failure_counts: Dict[str, int] = defaultdict(int)

        # 熔断开启时间
        self.open_timestamps: Dict[str, float] = {}

    def is_open(self, tool_name: str) -> bool:
        """
        检查工具是否被熔断

        Args:
            tool_name: 工具名称

        Returns:
            True: 工具被禁用
            False: 工具可用
        """
        if not self.enabled:
            return False

        # 检查是否在熔断列表
        if tool_name not in self.open_timestamps:
            return False

        # 检查是否可以恢复
        open_time = self.open_timestamps[tool_name]
        if time.time() - open_time > self.recovery_timeout:
            # 自动恢复
            self.close(tool_name)
            return False

        return True

    def record_result(self, tool_name: str, response: ToolResponse):
        """
        记录工具执行结果

        Args:
            tool_name: 工具名称
            response: 工具响应对象
        """
        if not self.enabled:
            return

        # 判断是否是错误
        is_error = response.status == ToolStatus.ERROR

        if is_error:
            self._on_failure(tool_name)
        else:
            self._on_success(tool_name)

    def _on_failure(self, tool_name: str):
        """处理失败"""
        # 增加失败计数
        self.failure_counts[tool_name] += 1

        # 检查是否达到阈值
        if self.failure_counts[tool_name] >= self.failure_threshold:
            self.open_timestamps[tool_name] = time.time()
            print(f"🔴 Circuit Breaker: 工具 '{tool_name}' 已熔断（连续 {self.failure_counts[tool_name]} 次失败）")

    def _on_success(self, tool_name: str):
        """处理成功"""
        # 重置失败计数
        self.failure_counts[tool_name] = 0

    def open(self, tool_name: str):
        """手动开启熔断"""
        if not self.enabled:
            return

        self.open_timestamps[tool_name] = time.time()
        print(f"🔴 Circuit Breaker: 工具 '{tool_name}' 已手动熔断")

    def close(self, tool_name: str):
        """关闭熔断，恢复工具"""
        self.failure_counts[tool_name] = 0
        self.open_timestamps.pop(tool_name, None)
        print(f"🟢 Circuit Breaker: 工具 '{tool_name}' 已恢复")

    def get_status(self, tool_name: str) -> Dict[str, any]:
        """
        获取工具的熔断状态

        Args:
            tool_name: 工具名称

        Returns:
            状态字典，包含：
            - state: "open" | "closed"
            - failure_count: 失败次数
            - open_since: 熔断开始时间（仅 open 状态）
            - recover_in_seconds: 恢复倒计时（仅 open 状态）
        """
        is_open = tool_name in self.open_timestamps

        if is_open:
            open_time = self.open_timestamps[tool_name]
            time_since_open = time.time() - open_time
            time_to_recover = max(0, self.recovery_timeout - time_since_open)

            return {
                "state": "open",
                "failure_count": self.failure_counts[tool_name],
                "open_since": open_time,
                "recover_in_seconds": int(time_to_recover)
            }
        else:
            return {
                "state": "closed",
                "failure_count": self.failure_counts[tool_name]
            }

    def get_all_status(self) -> Dict[str, Dict]:
        """
        获取所有工具的熔断状态

        Returns:
            工具名称 -> 状态字典
        """
        # 收集所有已知的工具名
        all_tools = set(self.failure_counts.keys()) | set(self.open_timestamps.keys())

        return {
            tool_name: self.get_status(tool_name)
            for tool_name in all_tools
        }

