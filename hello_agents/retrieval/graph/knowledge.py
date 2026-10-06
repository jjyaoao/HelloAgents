"""规范化显式声明的实体标识，并使用 Leiden 算法进行聚类。"""

from collections import defaultdict
import hashlib
import json
import unicodedata

from .types import Extraction, GraphIntegrityError


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def validate_extraction(raw, chunk, config):
    extraction = Extraction.model_validate(raw, strict=True)
    if (
        len(extraction.entities) > config.max_entities_per_chunk
        or len(extraction.relations) > config.max_relations_per_chunk
    ):
        raise GraphIntegrityError(
            "Extraction exceeds configured entity/relation limits"
        )
    keys = set()
    for entity in extraction.entities:
        if (
            entity.key in keys
            or not normalize(entity.name)
            or not normalize(entity.kind)
        ):
            raise GraphIntegrityError(
                "Entity keys must be unique and names/kinds nonempty"
            )
        keys.add(entity.key)
        if not any(
            name and name in entity.quote for name in [entity.name, *entity.aliases]
        ):
            raise GraphIntegrityError(
                "An entity name or alias must occur verbatim in its evidence quote"
            )
        if any(not normalize(alias) for alias in entity.aliases):
            raise GraphIntegrityError("Entity aliases must be nonempty")
    for relation in extraction.relations:
        if (
            relation.source not in keys
            or relation.target not in keys
            or not normalize(relation.predicate)
        ):
            raise GraphIntegrityError(
                "Relations must reference declared chunk-local entity keys"
            )
    for item in [*extraction.entities, *extraction.relations]:
        if item.quote not in chunk.content or len(item.quote) > config.max_quote_chars:
            raise GraphIntegrityError(
                "Evidence quote must be an exact bounded substring of the canonical chunk"
            )
    return extraction.model_dump(mode="json")


def assemble(chunks, extracted):
    entities, relations, evidence = {}, {}, {}
    for chunk, raw in zip(chunks, extracted):
        local = {}

        def cite(quote, entity_ids=(), relation=None):
            offset = chunk.content.index(quote)
            key = "ev-" + digest([chunk.chunk_id, offset, quote])[:24]
            record = evidence.setdefault(
                key,
                {
                    "id": key,
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "source": chunk.source,
                    "version": chunk.version,
                    "start": chunk.start + offset,
                    "end": chunk.start + offset + len(quote),
                    "quote": quote,
                    "entity_ids": [],
                    "relations": [],
                },
            )
            record["entity_ids"] = sorted(set(record["entity_ids"]) | set(entity_ids))
            if relation and relation not in record["relations"]:
                record["relations"].append(relation)
            return key

        for mention in raw["entities"]:
            identity = [normalize(mention[name]) for name in ("kind", "name", "scope")]
            key = "en-" + digest(identity)[:24]
            local[mention["key"]] = key
            entity = entities.setdefault(
                key,
                {
                    "id": key,
                    "name": mention["name"],
                    "kind": mention["kind"],
                    "scope": mention["scope"],
                    "aliases": [],
                    "descriptions": [],
                    "evidence_ids": [],
                },
            )
            entity["aliases"] = sorted(
                set(entity["aliases"]) | {mention["name"], *mention["aliases"]}
            )
            if mention["description"] not in entity["descriptions"]:
                entity["descriptions"].append(mention["description"])
            eid = cite(mention["quote"], [key])
            if eid not in entity["evidence_ids"]:
                entity["evidence_ids"].append(eid)
        for mention in raw["relations"]:
            source, target = local[mention["source"]], local[mention["target"]]
            key = (
                "rel-" + digest([source, target, normalize(mention["predicate"])])[:24]
            )
            relation = relations.setdefault(
                key,
                {
                    "id": key,
                    "source": source,
                    "target": target,
                    "predicate": mention["predicate"],
                    "descriptions": [],
                    "evidence_ids": [],
                },
            )
            if mention["description"] not in relation["descriptions"]:
                relation["descriptions"].append(mention["description"])
            eid = cite(
                mention["quote"],
                [source, target],
                {
                    "source": source,
                    "target": target,
                    "predicate": mention["predicate"],
                    "description": mention["description"],
                },
            )
            if eid not in relation["evidence_ids"]:
                relation["evidence_ids"].append(eid)
        # 全局覆盖时，不能静默遗漏未抽取出实体的原始材料。
        if not raw["entities"]:
            cite(chunk.content)
    aliases = defaultdict(set)
    for entity in entities.values():
        for alias in entity["aliases"]:
            aliases[normalize(alias)].add(entity["id"])
    return {
        "entities": entities,
        "relations": relations,
        "evidence": evidence,
        "aliases": {key: sorted(value) for key, value in sorted(aliases.items())},
        "ambiguous_aliases": {
            key: sorted(value)
            for key, value in sorted(aliases.items())
            if len(value) > 1
        },
    }


def make_graph(entities, relations):
    try:
        import igraph as ig
    except ImportError as exc:
        raise ImportError(
            "GraphRAG requires pip install 'hello-agents[graphrag]'"
        ) from exc
    names = sorted(entities)
    indices = {key: index for index, key in enumerate(names)}
    weights = defaultdict(int)
    for relation in relations.values():
        if relation["source"] != relation["target"]:
            pair = tuple(
                sorted((indices[relation["source"]], indices[relation["target"]]))
            )
            weights[pair] += len(relation["evidence_ids"])
    graph = ig.Graph(n=len(names), edges=list(weights), directed=False)
    graph.vs["name"] = names
    graph.es["weight"] = list(weights.values())
    return graph


def communities(knowledge, config):
    try:
        import leidenalg
    except ImportError as exc:
        raise ImportError(
            "GraphRAG requires pip install 'hello-agents[graphrag]'"
        ) from exc
    graph = make_graph(knowledge["entities"], knowledge["relations"])
    frontier = [(None, sorted(knowledge["entities"]))]
    result = []
    for level in range(config.levels):
        next_frontier = []
        for parent, members in frontier:
            if not members:
                continue
            subgraph = graph.induced_subgraph(
                [graph.vs.find(name=key).index for key in members]
            )
            partition = leidenalg.find_partition(
                subgraph,
                leidenalg.RBConfigurationVertexPartition,
                weights="weight",
                resolution_parameter=config.resolution * (2**level),
                seed=config.seed,
                n_iterations=2,
            )
            groups = sorted(
                sorted(subgraph.vs[index]["name"] for index in group)
                for group in partition
            )
            for group in groups:
                cid = "community-" + digest([level, group])[:24]
                eids = sorted(
                    eid
                    for eid, item in knowledge["evidence"].items()
                    if set(item["entity_ids"]) & set(group)
                )
                result.append(
                    {
                        "id": cid,
                        "level": level,
                        "parent": parent,
                        "entity_ids": group,
                        "evidence_ids": eids,
                        "kind": "leiden",
                    }
                )
                next_frontier.append((cid, group))
        frontier = next_frontier
    unattached = sorted(
        key for key, item in knowledge["evidence"].items() if not item["entity_ids"]
    )
    if unattached:
        for level in range(config.levels):
            result.append(
                {
                    "id": f"unassigned-{level}",
                    "level": level,
                    "parent": None,
                    "entity_ids": [],
                    "evidence_ids": unattached,
                    "kind": "unassigned",
                }
            )
    return result
