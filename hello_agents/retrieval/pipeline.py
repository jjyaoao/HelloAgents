"""可组合的检索与重排契约。重排只改变候选次序，不得改写证据。"""

from typing import List, Protocol, Sequence

from .store import RetrievalResult


class SearchBackend(Protocol):
    def search(self, query: str, limit: int = 5) -> List[RetrievalResult]: ...


class Reranker(Protocol):
    def rerank(
        self, query: str, candidates: Sequence[RetrievalResult]
    ) -> Sequence[RetrievalResult]: ...


class RetrievalPipeline:
    """从后端召回后可选重排。后端、重排模型均由宿主注入。

    此类不包含默认向量模型，也不把词项打分称为语义重排。
    重排器须返回所有原候选的排列，保留来源、内容及召回分数；
    独立重排分数可由实现保存在自己的诊断记录中。
    """

    def __init__(
        self,
        backend: SearchBackend,
        reranker: Reranker = None,
        candidate_limit: int = 20,
    ):
        if type(candidate_limit) is not int or not 1 <= candidate_limit <= 100:
            raise ValueError("candidate_limit 必须是 1 到 100 的整数")
        self.backend = backend
        self.reranker = reranker
        self.candidate_limit = candidate_limit

    def search(self, query: str, limit: int = 5) -> List[RetrievalResult]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query 必须是非空字符串")
        if type(limit) is not int or not 1 <= limit <= self.candidate_limit:
            raise ValueError("limit 必须是 1 到 candidate_limit 的整数")
        candidates = list(self.backend.search(query, self.candidate_limit))
        identities = {item.chunk_id: item for item in candidates}
        if len(identities) != len(candidates):
            raise ValueError("检索后端返回了重复片段")
        if self.reranker is not None:
            ranked = list(self.reranker.rerank(query, tuple(candidates)))
            if (
                len(ranked) != len(candidates)
                or {item.chunk_id for item in ranked} != set(identities)
                or any(item != identities[item.chunk_id] for item in ranked)
            ):
                raise ValueError("重排器必须返回原候选的排列，不能增删或改写证据")
            candidates = ranked
        return candidates[:limit]
