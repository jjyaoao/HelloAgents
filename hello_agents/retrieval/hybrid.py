"""用排名融合不同召回器，不混加 BM25 与余弦相似度。"""

from dataclasses import replace
from typing import List, Sequence

from .pipeline import SearchBackend
from .store import RetrievalResult


class HybridSearch:
    """多路候选的 Reciprocal Rank Fusion。

    一路内排名从 1 开始，每路贡献 1 / (rrf_k + rank)。rrf_k 默认 60，
    这是本组件的参数，并非 Qdrant 服务端的默认值。每路最多召回
    candidate_limit 条；融合不能找回所有召回器都遗漏的证据。
    """

    def __init__(
        self,
        backends: Sequence[SearchBackend],
        *,
        candidate_limit: int = 20,
        rrf_k: int = 60,
    ):
        if len(backends) < 2:
            raise ValueError("混合检索至少需要两个召回器")
        if type(candidate_limit) is not int or not 1 <= candidate_limit <= 100:
            raise ValueError("candidate_limit 必须是 1 到 100 的整数")
        if type(rrf_k) is not int or rrf_k < 0:
            raise ValueError("rrf_k 必须是非负整数")
        self.backends = tuple(backends)
        self.candidate_limit = candidate_limit
        self.rrf_k = rrf_k

    def search(self, query: str, limit: int = 5) -> List[RetrievalResult]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query 必须是非空字符串")
        if type(limit) is not int or not 1 <= limit <= self.candidate_limit:
            raise ValueError("limit 必须在 1 到 candidate_limit 之间")
        evidence, scores = {}, {}
        # 对含 RAGStore 的后端核对读取前后的修订号，避免混合两个资料版本。
        stores = [getattr(backend, "store", backend) for backend in self.backends]
        revisions = [getattr(store, "revision", None) for store in stores]
        for backend in self.backends:
            seen = set()
            for rank, item in enumerate(backend.search(query, self.candidate_limit), 1):
                if item.chunk_id in seen:
                    raise ValueError("召回器返回了重复片段")
                seen.add(item.chunk_id)
                canonical = replace(item, score=0.0)
                if item.chunk_id in evidence and evidence[item.chunk_id] != canonical:
                    raise ValueError("不同召回器对同一片段返回了不同证据")
                evidence[item.chunk_id] = canonical
                scores[item.chunk_id] = scores.get(item.chunk_id, 0.0) + 1 / (
                    self.rrf_k + rank
                )
        if any(
            getattr(store, "revision", None) != revision
            for store, revision in zip(stores, revisions)
        ):
            raise RuntimeError("检索期间资料发生变化，请重新检索")
        ids = sorted(scores, key=lambda key: (-scores[key], key))[:limit]
        return [replace(evidence[key], score=scores[key]) for key in ids]
