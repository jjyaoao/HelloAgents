"""根据显式相关性标注，计算确定性的排序检索指标。"""
from math import isfinite, log2
from time import perf_counter


def ranking_metrics(retrieved, relevance, *, k=5):
    """计算前 k 项的二值 Recall、MRR 与分级 nDCG；无标注时指标未定义。"""
    if type(k) is not int or k < 1:
        raise ValueError('k must be positive')
    if len(retrieved) != len(set(retrieved)):
        raise ValueError('ranked IDs must be unique')
    if any(not isinstance(v, (int,float)) or isinstance(v,bool) or not isfinite(v) or not 0 <= v <= 10 for v in relevance.values()):
        raise ValueError('relevance grades must be finite values from 0 to 10')
    relevant = {key for key, value in relevance.items() if value > 0}
    if not relevant:
        return dict(recall_at_k=None, mrr_at_k=None, ndcg_at_k=None)
    ranked = list(retrieved[:k])
    hits = [i+1 for i, key in enumerate(ranked) if key in relevant]
    dcg = sum((2**relevance.get(key,0)-1)/log2(i+2) for i,key in enumerate(ranked))
    ideal = sum((2**grade-1)/log2(i+2) for i,grade in enumerate(sorted(relevance.values(),reverse=True)[:k]))
    return dict(recall_at_k=len(hits)/len(relevant), mrr_at_k=1/hits[0] if hits else 0.0, ndcg_at_k=dcg/ideal)


def evaluate_retrieval(backend, cases, *, k=5):
    """案例包含查询与基于实际片段 ID 的相关性映射，并保留逐案例证据。"""
    rows = []
    for case in cases:
        started = perf_counter()
        hits = backend.search(case['query'], limit=k)
        ids = [hit.chunk_id for hit in hits]
        rows.append(dict(query=case['query'], retrieved_ids=ids,
                         latency_ms=(perf_counter()-started)*1000,
                         **ranking_metrics(ids, case['relevance'], k=k)))
    means = {}
    for key in ('recall_at_k','mrr_at_k','ndcg_at_k'):
        values = [row[key] for row in rows if row[key] is not None]
        means[key] = sum(values)/len(values) if values else None
    return dict(cases=rows, mean=means, evaluated_queries=sum(row['recall_at_k'] is not None for row in rows))
