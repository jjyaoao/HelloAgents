"""宿主绑定范围的记忆工具。授权与用户确认由应用在注册前决定。"""

from typing import Any, Callable, Dict, List

from ..base import Tool, ToolParameter, tool_action
from ..errors import ToolErrorCode
from ..response import ToolResponse
from ...memory import MemoryStore
from ...retrieval.qdrant import IndexStaleError


class MemoryTool(Tool):
    def __init__(self, store: MemoryStore, search_backend=None):
        super().__init__(
            "memory", "保存、检索、修订和撤回当前用户任务中的记忆", expandable=True
        )
        self.store = store
        self.search_backend = search_backend if search_backend is not None else store

    @staticmethod
    def _response(operation: Callable) -> ToolResponse:
        try:
            result = operation()
            records = result if isinstance(result, list) else [result]
            return ToolResponse.success(
                text=f"返回 {len(records)} 条记忆记录；来源与状态见 records。",
                data={"records": [r.to_dict() for r in records]},
            )
        except KeyError:
            return ToolResponse.error(ToolErrorCode.NOT_FOUND, "当前范围内未找到记录")
        except IndexStaleError:
            return ToolResponse.error(
                ToolErrorCode.CONFLICT, "记忆索引已过期，需由宿主同步后再查询"
            )
        except ValueError as exc:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, str(exc))

    @tool_action(
        "memory_add", "保存有来源的记忆；推断应标记为 inference，不代表已核实事实"
    )
    def add(self, content: str, source: str, kind: str = "preference") -> ToolResponse:
        """保存记忆。

        Args:
            content: 需要保存的内容。
            source: 内容来源，例如用户本轮明确陈述或证据标识。
            kind: preference、fact、episode、inference 或 procedure。
        """
        return self._response(lambda: self.store.add(content, source, kind))

    @tool_action("memory_search", "查询当前用户任务范围中的有效记忆")
    def search(self, query: str = "", limit: int = 10) -> ToolResponse:
        """读取有效记忆。

        Args:
            query: 查询内容，空字符串按更新时间读取。
            limit: 最多返回的记录数；不可超过宿主检索后端设置的候选上限。
        """
        return self._response(lambda: self.search_backend.search(query, limit))

    @tool_action("memory_revise", "替代当前有效记忆，保留旧版本及修订关系")
    def revise(self, memory_id: str, content: str, source: str) -> ToolResponse:
        """修订记忆。

        Args:
            memory_id: 需要修订的当前记录标识。
            content: 新内容。
            source: 修改依据或用户陈述来源。
        """
        if not isinstance(memory_id, str) or not memory_id.strip():
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "memory_id 不能为空")
        return self._response(lambda: self.store.revise(memory_id, content, source))

    @tool_action("memory_retract", "撤回当前记忆，后续查询排除它并保留审计记录")
    def retract(self, memory_id: str) -> ToolResponse:
        """撤回记忆。

        Args:
            memory_id: 需要撤回的当前记录标识。
        """
        if not isinstance(memory_id, str) or not memory_id.strip():
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "memory_id 不能为空")
        return self._response(lambda: self.store.retract(memory_id))

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        if not isinstance(parameters, dict):
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "参数必须是对象")
        args = dict(parameters)
        action = args.pop("action", None)
        actions = {
            "add": self.add,
            "search": self.search,
            "revise": self.revise,
            "retract": self.retract,
        }
        if action not in actions:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "未知 memory action")
        try:
            return actions[action](**args)
        except TypeError as exc:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, str(exc))

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action", type="string", description="add/search/revise/retract"
            ),
            ToolParameter(
                name="content", type="string", description="记忆内容", required=False
            ),
            ToolParameter(
                name="source", type="string", description="内容来源", required=False
            ),
            ToolParameter(
                name="kind",
                type="string",
                description="记忆种类",
                required=False,
                default="preference",
            ),
            ToolParameter(
                name="query",
                type="string",
                description="检索内容",
                required=False,
                default="",
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="返回条数",
                required=False,
                default=10,
            ),
            ToolParameter(
                name="memory_id",
                type="string",
                description="待修订或撤回的记录标识",
                required=False,
            ),
        ]
