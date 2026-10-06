"""只读的局部关系检索；关系入库和实体统一由宿主完成。"""

from typing import Any, Dict, List

from ..base import Tool, ToolParameter
from ..errors import ToolErrorCode
from ..response import ToolResponse
from ...retrieval import RelationStore


class RelationTool(Tool):
    def __init__(self, store: RelationStore):
        super().__init__(
            "relation_lookup", "按精确实体名称查找有来源的局部关系，返回原文与版本"
        )
        self.store = store

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        if not isinstance(parameters, dict):
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "参数必须是对象")
        try:
            results = self.store.neighbors(**parameters)
            return ToolResponse.success(
                text=f"取得 {len(results)} 条局部关系；逐条核对来源，不将关联直接解释为因果。",
                data={"relations": [item.to_dict() for item in results]},
                stats={"count": len(results), "method": "bounded-local-traversal"},
            )
        except (ValueError, TypeError) as exc:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, str(exc))

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="entity",
                type="string",
                description="资料中的精确实体名称，注意地区和同名场馆",
            ),
            ToolParameter(
                name="hops",
                type="integer",
                description="遍历深度 1 到 3",
                required=False,
                default=1,
                json_schema={"type": "integer", "minimum": 1, "maximum": 3},
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="最多返回 1 到 100 条边",
                required=False,
                default=20,
                json_schema={"type": "integer", "minimum": 1, "maximum": 100},
            ),
            ToolParameter(
                name="direction",
                type="string",
                description="out 出边、in 入边或 both",
                required=False,
                default="both",
                json_schema={"type": "string", "enum": ["out", "in", "both"]},
            ),
        ]
