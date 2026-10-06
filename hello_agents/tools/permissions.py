"""由宿主控制的执行策略，不等同于操作系统沙箱或模型指令。"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: str = ""

    def __post_init__(self):
        if type(self.allowed) is not bool or not isinstance(self.reason, str):
            raise TypeError("PermissionDecision requires bool allowed and str reason")


class ToolPolicy(Protocol):
    def __call__(self, name: str, arguments: Any) -> PermissionDecision: ...


class AllowlistPolicy:
    """拒绝宿主允许列表之外的工具，也适用于后续新增工具。"""

    def __init__(self, names):
        if isinstance(names, str):
            raise TypeError("names must be a collection, not a string")
        self.names = frozenset(names)
        if any(not isinstance(name, str) or not name for name in self.names):
            raise ValueError("names must contain nonempty strings")

    def __call__(self, name, arguments):
        return PermissionDecision(
            name in self.names, "Tool is outside the host allowlist"
        )
