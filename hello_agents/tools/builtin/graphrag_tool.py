"""只读 GraphRAG 工具；索引构建与资料修改由宿主负责。"""

from ..base import Tool, ToolParameter, tool_action
from ..response import ToolResponse
from ..errors import ToolErrorCode


class GraphRAGTool(Tool):
    def __init__(self, index):
        super().__init__(
            "graphrag",
            "检索有来源的实体关系，或综合全部社区报告回答跨资料问题",
            expandable=True,
        )
        self.index = index

    @tool_action("graphrag_local", "从问题相关实体扩展图邻域，返回当前版本的原文片段")
    def local(self, query: str, limit: int = 5) -> ToolResponse:
        """检索局部证据。

        Args:
            query: 要核对的实体、依赖或条件。
            limit: 返回片段数，1 到 100。
        """
        hits = self.index.local_search(query, limit)
        return ToolResponse.success(
            "返回图邻域相关的原文；证据仍需核对。",
            data={
                "results": [hit.to_dict() for hit in hits],
                "diagnostics": self.index.last_local_diagnostics,
            },
        )

    @tool_action(
        "graphrag_global",
        "读取所选层级的全部社区报告，汇总跨资料答案及引用；可能调用多次模型",
    )
    def global_query(self, query: str, level: int = 0) -> ToolResponse:
        """综合全局资料。

        Args:
            query: 需要跨社区汇总的问题。
            level: 社区层级，0 为最粗层级。
        """
        answer = self.index.global_search(query, level=level)
        return ToolResponse.success(answer.answer, data=answer.to_dict())

    def run(self, parameters):
        if not isinstance(parameters, dict):
            return ToolResponse.error(
                ToolErrorCode.INVALID_PARAM, "parameters must be an object"
            )
        args = dict(parameters)
        action = args.pop("action", None)
        try:
            if action == "local":
                return self.local(**args)
            if action == "global":
                return self.global_query(**args)
        except (ValueError, TypeError) as exc:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, str(exc))
        return ToolResponse.error(
            ToolErrorCode.INVALID_PARAM, "action must be local or global"
        )

    def get_parameters(self):
        return [
            ToolParameter(name="action", type="string", description="local or global"),
            ToolParameter(name="query", type="string", description="需要查询的问题"),
            ToolParameter(
                name="limit",
                type="integer",
                description="local 返回片段数",
                required=False,
            ),
            ToolParameter(
                name="level",
                type="integer",
                description="global 社区层级",
                required=False,
            ),
        ]
