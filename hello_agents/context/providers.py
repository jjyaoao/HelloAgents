"""资料收集与消息组装协议，通过显式注入组合组件。"""

from typing import Any, Dict, Iterable, List, Protocol, TYPE_CHECKING

from .types import ContextBuildResult, ContextPacket

if TYPE_CHECKING:
    from ..retrieval import SearchBackend
    from ..memory import MemoryStore


class ContextProvider(Protocol):
    """每次模型调用前重新收集候选；不要在实例中固定历史检索快照。"""

    def get_context(self, query: str) -> Iterable[ContextPacket]: ...


class ContextAssembler(Protocol):
    """SimpleAgent 所需的最小组装接口，ContextBuilder 是默认实现。"""

    def build_messages(
        self,
        messages: List[Dict[str, Any]],
        additional_packets: Iterable[ContextPacket] = (),
        tool_schemas: Iterable[Dict[str, Any]] = (),
    ) -> ContextBuildResult: ...


class RetrievalContextProvider:
    """固定 RAG：每次用当前任务检索。Agentic RAG 可改用 RAGTool 自选查询。"""

    def __init__(self, store: "SearchBackend", limit: int = 5):
        self.store = store
        self.limit = limit

    def get_context(self, query: str) -> Iterable[ContextPacket]:
        return [
            result.to_context_packet()
            for result in self.store.search(query, self.limit)
        ]


class MemoryContextProvider:
    """每次读取当前范围的有效记忆，支持将宿主选定的约束设为必需包。

    默认读取最近记录；use_query=True 时按当前任务查询选定的检索后端。
    required 由宿主决定，不是记忆内容可以自行申请的权限。
    """

    def __init__(
        self,
        store: "MemoryStore",
        limit: int = 10,
        required: bool = False,
        use_query: bool = False,
        search_backend=None,
    ):
        self.store = store
        self.limit = limit
        self.required = required
        self.use_query = use_query
        self.search_backend = search_backend if search_backend is not None else store

    def get_context(self, query: str) -> Iterable[ContextPacket]:
        return [
            record.to_context_packet(required=self.required)
            for record in self.search_backend.search(
                query if self.use_query else "", self.limit
            )
        ]
