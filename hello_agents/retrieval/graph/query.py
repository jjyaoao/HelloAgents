"""检索局部图邻域，并通过报告的映射与归约实现全局覆盖。"""

from dataclasses import replace
import json

from ...context.text import count_tokens, lexical_terms
from ..qdrant import QdrantSearch
from ..store import RAGStore
from .knowledge import make_graph, normalize
from .types import GraphAnswer, GraphBudgetError, GraphIntegrityError


def question(query):
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be nonempty")


def local_context(index, query, limit):
    question(query)
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer in 1..100")
    with index._lock:
        active, data = index._load()
        normalized = normalize(query)
        query_terms = set(lexical_terms(query))
        direct, ranked = set(), []
        for alias, identifiers in data["aliases"].items():
            if alias in normalized:
                direct.update(identifiers)
        for identifier, entity in data["entities"].items():
            terms = set(
                lexical_terms(
                    " ".join(
                        [entity["name"], *entity["aliases"], *entity["descriptions"]]
                    )
                )
            )
            overlap = len(query_terms & terms) / (len(query_terms) or 1)
            if overlap:
                ranked.append((overlap, identifier))
        seeds = sorted(direct)
        for _, identifier in (
            sorted(ranked, key=lambda item: (-item[0], item[1])) if not direct else []
        ):
            if identifier not in seeds and len(seeds) < index.config.seed_limit:
                seeds.append(identifier)
        semantic = []
        if index.embedding is not None and data["entities"]:
            assets = index.storage.assets / active["id"]
            entity_store = RAGStore(str(assets / "entities.sqlite"))
            with QdrantSearch(
                entity_store, index.embedding, path=str(assets / "vectors")
            ) as dense:
                semantic = [
                    item.document_id
                    for item in dense.search(query, index.config.seed_limit)
                ]
            seeds = sorted(set(seeds) | set(semantic))
        graph = make_graph(data["entities"], data["relations"])
        vertices = [graph.vs.find(name=identifier).index for identifier in seeds]
        neighborhoods = (
            graph.neighborhood(vertices=vertices, order=index.config.hops)
            if vertices
            else []
        )
        selected = {
            graph.vs[v]["name"] for neighborhood in neighborhoods for v in neighborhood
        }
        distances = graph.distances(source=vertices) if vertices else []
        proximity = (
            {
                graph.vs[v]["name"]: min(row[v] for row in distances)
                for v in range(graph.vcount())
            }
            if distances
            else {}
        )
        scores = {}
        for item in data["evidence"].values():
            related = set(item["entity_ids"]) & selected
            if related:
                score = max(1 / (1 + proximity[key]) for key in related)
                scores[item["chunk_id"]] = max(scores.get(item["chunk_id"], 0), score)
        # 原文词项检索覆盖直接出现的词语与未抽取出实体的材料。
        for rank, hit in enumerate(index.store.search(query, limit), 1):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0) + 1 / (60 + rank)
        chosen = sorted(scores, key=lambda key: (-scores[key], key))[:limit]
        chunks = [
            replace(index.store.read_chunk(key), score=scores[key]) for key in chosen
        ]
        relations = {
            key: value
            for key, value in data["relations"].items()
            if value["source"] in selected and value["target"] in selected
        }
        community_ids = {
            item["id"]
            for item in data["communities"]
            if item["level"] == 0 and set(item["entity_ids"]) & selected
        }
        context = {
            "entities": {key: data["entities"][key] for key in sorted(selected)},
            "relations": relations,
            "reports": [
                item
                for item in data["reports"]
                if item["community_id"] in community_ids
            ],
            "chunks": chunks,
        }
        serializable = {**context, "chunks": [item.to_dict() for item in chunks]}
        if (
            count_tokens(json.dumps(serializable, ensure_ascii=False))
            > index.config.payload_tokens
        ):
            raise GraphBudgetError(
                "Local graph context exceeds budget; reduce hops/seed_limit or raise max_input_tokens"
            )
        index._check_revision(active["revision"])
        diagnostics = {
            "generation": active["id"],
            "seed_entities": seeds,
            "semantic_seeds": semantic,
            "hops": index.config.hops,
            "candidate_chunks": len(scores),
            "returned_chunks": len(chunks),
            "ambiguous_aliases": {
                alias: ids
                for alias, ids in data["ambiguous_aliases"].items()
                if alias in normalized
            },
            "ranking": "graph distance with lexical rank boost; not a calibrated relevance probability",
        }
        index.last_local_diagnostics = diagnostics
        return {**context, "diagnostics": diagnostics}


def global_search(index, query, level, checkpoint=None):
    question(query)
    if type(level) is not int or not 0 <= level < index.config.levels:
        raise ValueError("level must select a configured hierarchy level")
    if checkpoint is not None and not callable(checkpoint):
        raise TypeError("checkpoint must be callable or None")
    checkpoint = checkpoint if checkpoint is not None else (lambda: None)
    active, data = index._load()
    reports = [report for report in data["reports"] if report["level"] == level]
    if len(reports) > index.config.max_reports:
        raise GraphBudgetError(
            "Global query exceeds max_reports; no partial answer was returned"
        )
    mapped, claims = [], []
    for report in reports:
        checkpoint()
        raw = index._call("map", {"question": query, "report": report})
        allowed = {eid for claim in report["claims"] for eid in claim["citations"]}
        index._check_claims(raw, allowed)
        claims.extend(raw["claims"])
        mapped.append(report["id"])
        checkpoint()
    rounds, reduce_calls = 0, 0
    while claims:
        rounds += 1
        if rounds > index.config.max_reduce_rounds:
            raise GraphBudgetError(
                "Global reduction did not converge within max_reduce_rounds; no claims were silently dropped"
            )
        packs = index._packs(claims, {"question": query}, "claims")
        next_claims = []
        for payload in packs:
            checkpoint()
            raw = index._call("reduce", payload)
            index._check_claims(
                raw, {eid for claim in payload["claims"] for eid in claim["citations"]}
            )
            next_claims.extend(raw["claims"])
            reduce_calls += 1
            checkpoint()
        claims = next_claims
        if len(packs) == 1:
            break
    summarized = {
        data["evidence"][eid]["chunk_id"]
        for report in reports
        for claim in report["claims"]
        for eid in claim["citations"]
    }
    unsummarized = sorted(set(data["chunk_ids"]) - summarized)
    citation_ids = sorted({eid for claim in claims for eid in claim["citations"]})
    citations = []
    for eid in citation_ids:
        if eid not in data["evidence"]:
            raise GraphIntegrityError("Answer references an unknown evidence ID")
        item = data["evidence"][eid]
        chunk = index.store.read_chunk(item["chunk_id"])
        start, end = item["start"] - chunk.start, item["end"] - chunk.start
        if (
            chunk.version != item["version"]
            or chunk.content[start:end] != item["quote"]
        ):
            raise GraphIntegrityError(
                "Final citation does not match the canonical quoted source"
            )
        citations.append(item)
    checkpoint()
    index._check_revision(active["revision"])
    complete = len(mapped) == len(reports) and not unsummarized
    numbers = {eid: str(position) for position, eid in enumerate(citation_ids, 1)}
    text = "\n".join(
        claim["text"]
        + " "
        + "".join("[" + numbers[eid] + "]" for eid in claim["citations"])
        for claim in claims
    )
    coverage = {
        "level": level,
        "total_reports": len(reports),
        "mapped_reports": len(mapped),
        "source_chunks": len(data["chunk_ids"]),
        "summarized_chunks": len(summarized),
        "unsummarized_chunk_ids": unsummarized,
        "complete": complete,
        "meaning": "Report processing and source-reference coverage; not proof of semantic completeness",
    }
    return GraphAnswer(
        text or "现有资料不足以支持这个问题的答案。",
        ("answered" if complete else "answered_partial") if claims else "no_answer",
        claims,
        citations,
        coverage,
        {
            "generation": active["id"],
            "revision": active["revision"],
            "map_calls": len(mapped),
            "reduce_calls": reduce_calls,
            "reduce_rounds": rounds,
        },
    )
