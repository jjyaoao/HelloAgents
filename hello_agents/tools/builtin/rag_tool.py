"""RAG 工具：仅暴露检索与回读，索引导入由宿主负责。"""

from typing import Any, Dict, List

from ..base import Tool, ToolParameter, tool_action
from ..errors import ToolErrorCode
from ..response import ToolResponse
from ...retrieval import RAGStore
from ...retrieval import SearchBackend


class RAGTool(Tool):
    def __init__(self, store: RAGStore, search_backend: SearchBackend = None):
        super().__init__("rag", "搜索资料并按来源片段回读原文", expandable=True)
        self.store = store
        self.search_backend = search_backend if search_backend is not None else store

    @tool_action("rag_search", "在当前资料版本中检索相关片段，返回来源与回读标识")
    def search(self, query: str, limit: int = 5) -> ToolResponse:
        """搜索资料。

        Args:
            query: 搜索关键词或问题。
            limit: 最多返回的片段数，范围为 1 到 100。
        """
        try:
            results = [r.to_dict() for r in self.search_backend.search(query, limit)]
            return ToolResponse.success(
                text=f"检索到 {len(results)} 个片段；使用 chunk_id 回读确切版本。",
                data={"results": results},
                stats={
                    "count": len(results),
                    "backend": type(self.search_backend).__name__,
                },
            )
        except ValueError as exc:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, str(exc))

    @tool_action("rag_read", "根据 chunk_id 回读片段原文及来源，可能是历史版本")
    def read(self, chunk_id: str) -> ToolResponse:
        """回读原文。

        Args:
            chunk_id: 检索结果中的片段标识。
        """
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "chunk_id 不能为空")
        try:
            result = self.store.read_chunk(chunk_id)
            return ToolResponse.success(
                text=result.content, data={"result": result.to_dict()}
            )
        except KeyError:
            return ToolResponse.error(ToolErrorCode.NOT_FOUND, "未找到片段")

    @tool_action(
        "rag_read_document",
        "回读片段所属文档的完整原文；传入检索结果的 document_id 和 version",
    )
    def read_document(self, document_id: str, version: str) -> ToolResponse:
        """回读确切版本，不自动跳到新版本。

        Args:
            document_id: 检索结果中的文档标识。
            version: 检索结果中的版本标识。
        """
        if not isinstance(version, str) or not version.strip():
            return ToolResponse.error(
                ToolErrorCode.INVALID_PARAM, "version 必须显式提供非空字符串"
            )
        try:
            document = self.store.read_document(document_id, version)
            return ToolResponse.success(
                text=document.content, data={"document": document.to_dict()}
            )
        except ValueError as exc:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, str(exc))
        except KeyError:
            return ToolResponse.error(ToolErrorCode.NOT_FOUND, "未找到指定文档版本")

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        if not isinstance(parameters, dict):
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, "参数必须是对象")
        args = dict(parameters)
        action = args.pop("action", None)
        try:
            if action == "search":
                return self.search(**args)
            if action == "read":
                return self.read(**args)
            if action == "read_document":
                return self.read_document(**args)
        except TypeError as exc:
            return ToolResponse.error(ToolErrorCode.INVALID_PARAM, str(exc))
        return ToolResponse.error(
            ToolErrorCode.INVALID_PARAM, "action 必须是 search、read 或 read_document"
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="search、read 或 read_document",
            ),
            ToolParameter(
                name="document_id",
                type="string",
                description="文档标识",
                required=False,
            ),
            ToolParameter(
                name="version", type="string", description="确切版本", required=False
            ),
            ToolParameter(
                name="query", type="string", description="search 的查询", required=False
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="返回条数",
                required=False,
                default=5,
            ),
            ToolParameter(
                name="chunk_id",
                type="string",
                description="read 的片段标识",
                required=False,
            ),
        ]
