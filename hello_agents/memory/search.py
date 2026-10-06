"""语义召回复用可选向量引擎，范围限定于单个 MemoryStore。"""

from typing import List, Protocol

from .store import MemoryRecord, MemoryStore
from ..retrieval.store import DocumentResult, RetrievalResult
from ..retrieval.qdrant import QdrantSearch, IndexStaleError
from ..retrieval.hybrid import HybridSearch


class MemorySearchBackend(Protocol):
    def search(self, query: str = "", limit: int = 10) -> List[MemoryRecord]: ...


class _MemoryDocuments:
    """以原始存储为准的只读视图，不复制 SQLite 语料或另设身份参数。"""

    def __init__(self, store):
        self.memory = store

    @property
    def namespace(self):
        return "memory:" + self.memory.namespace

    @property
    def revision(self):
        return self.memory.revision

    @staticmethod
    def _chunk(record):
        return RetrievalResult(
            record.memory_id,
            record.memory_id,
            record.source,
            record.memory_id,
            record.content,
            0,
            len(record.content),
        )

    def snapshot(self):
        revision, records = self.memory.snapshot()
        return revision, [self._chunk(record) for record in records]

    def read_chunk(self, chunk_id):
        return self._chunk(self.memory.get(chunk_id))

    def read_document(self, document_id, version=None):
        record = self.memory.get(document_id)
        if version is not None and version != record.memory_id:
            raise KeyError(version)
        return DocumentResult(
            record.memory_id,
            record.source,
            record.memory_id,
            record.content,
            record.status == "active",
        )

    def search(self, query, limit=5):
        return [self._chunk(record) for record in self.memory.search(query, limit)]


class SemanticMemorySearch:
    """提供稠密或混合召回，并进行版本校验、显式同步与原始记录回读。

    作用域继承自 ``store``；空查询返回当前有效的近期记录。
    作用域内数据变更后，在 sync() 完成前拒绝检索，避免重新召回已撤回的
    记忆。client、path、url 与嵌入接口的约定与 QdrantSearch 一致。
    """

    def __init__(
        self,
        store: MemoryStore,
        embedding,
        *,
        hybrid: bool = True,
        candidate_limit: int = 20,
        **qdrant_options,
    ):
        if type(hybrid) is not bool:
            raise TypeError("hybrid must be bool")
        if type(candidate_limit) is not int or not 1 <= candidate_limit <= 100:
            raise ValueError("candidate_limit must be 1..100")
        self.store = store
        self.documents = _MemoryDocuments(store)
        self.dense = QdrantSearch(self.documents, embedding, **qdrant_options)
        self.backend = (
            HybridSearch([self.documents, self.dense], candidate_limit=candidate_limit)
            if hybrid
            else self.dense
        )
        self.candidate_limit = candidate_limit

    def sync(self, *, batch_size: int = 64, checkpoint=None):
        return self.dense.sync(batch_size=batch_size, checkpoint=checkpoint)

    def search(self, query: str = "", limit: int = 10) -> List[MemoryRecord]:
        self.dense._ensure_open()
        if not isinstance(query, str):
            raise ValueError("query must be a string")
        if type(limit) is not int or not 1 <= limit <= self.candidate_limit:
            raise ValueError("limit must be 1..candidate_limit")
        if not query.strip():
            return self.store.search("", limit)
        revision = self.store.revision
        hits = self.backend.search(query, limit)
        try:
            records = [self.store.get(hit.chunk_id) for hit in hits]
        except KeyError as exc:
            raise IndexStaleError(
                "Memory changed during recall; resync before retrying"
            ) from exc
        if self.store.revision != revision:
            raise IndexStaleError(
                "Memory changed during recall; resync before retrying"
            )
        return records

    def close(self):
        self.dense.close()

    def __enter__(self):
        self.dense.__enter__()
        return self

    def __exit__(self, *_):
        self.close()
