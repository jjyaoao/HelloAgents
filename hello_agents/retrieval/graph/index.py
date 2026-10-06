"""构建带来源引用和版本的 GraphRAG 索引，并原子发布。"""

from dataclasses import asdict
from copy import deepcopy
import json
import threading
import uuid

from ...context.text import count_tokens
from ..qdrant import IndexStaleError, QdrantSearch
from ..store import RAGStore
from .knowledge import assemble, communities, digest, validate_extraction
from .storage import GraphStorage
from .types import (
    BuildReport,
    GraphConfig,
    GraphBudgetError,
    GraphIntegrityError,
    SCHEMAS,
)


class GraphRAGIndex:
    """模型抽取 → Leiden 社区划分 → 带引用的报告 → 局部或全局查询。

    SQLite 保存权威数据。可选的语义实体种子检索复用现有
    QdrantSearch 组件，不另写一套向量检索实现。
    """

    def __init__(
        self, store: RAGStore, path: str, model, *, config=None, embedding=None
    ):
        if (
            not isinstance(getattr(model, "model_id", None), str)
            or not model.model_id.strip()
        ):
            raise ValueError("GraphModel must have a stable nonempty model_id")
        self.store, self.model = store, model
        self.config = config or GraphConfig()
        if not isinstance(self.config, GraphConfig):
            raise TypeError("config must be GraphConfig")
        self.embedding = embedding
        self.storage = GraphStorage(path, store.namespace)
        self.config_id = digest(
            [
                "graph-pipeline-v1",
                model.model_id,
                asdict(self.config),
                [embedding.model_id, embedding.dimension] if embedding else None,
            ]
        )
        self._lock = threading.RLock()
        self.last_local_diagnostics = {}

    def _call(self, stage, payload):
        if (
            count_tokens(json.dumps(payload, ensure_ascii=False))
            > self.config.payload_tokens
        ):
            raise GraphBudgetError(
                f"{stage} input exceeds payload budget; nothing was silently truncated"
            )
        raw = self.model.generate(
            stage,
            deepcopy(payload),
            max_input_tokens=self.config.max_input_tokens,
            max_output_tokens=self.config.max_output_tokens,
        )
        try:
            encoded = json.dumps(raw, ensure_ascii=False, allow_nan=False)
            if count_tokens(encoded) > self.config.max_output_tokens:
                raise GraphBudgetError(f"{stage} output exceeds configured limit")
            return (
                SCHEMAS[stage].model_validate(raw, strict=True).model_dump(mode="json")
            )
        except ValueError as exc:
            raise GraphIntegrityError(
                f"{stage} returned invalid structured data"
            ) from exc

    def _packs(self, items, base, field):
        """每项输入必须恰好分配一次；无法容纳时明确失败，不丢弃超长输入。"""
        batches, current = [], []
        for item in items:
            candidate = {**base, field: [*current, item]}
            if (
                count_tokens(json.dumps(candidate, ensure_ascii=False))
                > self.config.payload_tokens
            ):
                if not current:
                    raise GraphBudgetError(
                        f"One {field} item exceeds the input budget; increase budget or use smaller source chunks"
                    )
                batches.append({**base, field: current})
                current = [item]
                if (
                    count_tokens(
                        json.dumps({**base, field: current}, ensure_ascii=False)
                    )
                    > self.config.payload_tokens
                ):
                    raise GraphBudgetError(f"One {field} item exceeds the input budget")
            else:
                current.append(item)
        if current:
            batches.append({**base, field: current})
        return batches

    @staticmethod
    def _check_claims(raw, allowed):
        for claim in raw["claims"]:
            if not claim["text"].strip() or not set(claim["citations"]).issubset(
                allowed
            ):
                raise GraphIntegrityError(
                    "Generated claim cites evidence not supplied to this model call"
                )
            claim["citations"] = sorted(set(claim["citations"]))
        return raw

    def _evidence_input(self, item, knowledge):
        names = knowledge["entities"]
        return {
            **item,
            "entities": [
                {key: names[eid][key] for key in ("id", "name", "kind", "scope")}
                for eid in item["entity_ids"]
            ],
            "relations": [
                {
                    **relation,
                    "source_name": names[relation["source"]]["name"],
                    "target_name": names[relation["target"]]["name"],
                }
                for relation in item["relations"]
            ],
        }

    def build(self, *, checkpoint=None):
        """缓存已成功的阶段，仅对完整索引版本执行比较并交换式发布。

        checkpoint 可使用 JobContext.checkpoint；调用间发生取消时，保留
        可复用的缓存。外部模型调用必须自行设置网络超时。
        """
        if checkpoint is not None and not callable(checkpoint):
            raise TypeError("checkpoint must be callable or None")
        checkpoint = checkpoint if checkpoint is not None else (lambda: None)
        with self._lock:
            checkpoint()
            active = self.storage.active()
            revision, chunks = self.store.snapshot()
            if (
                active
                and active["revision"] == revision
                and active["config_id"] == self.config_id
            ):
                report = json.loads(active["payload"])["build_report"]
                return BuildReport(**{**report, "reused_generation": True})
            generation = str(uuid.uuid4())
            extracted, extraction_hits, report_hits = [], 0, 0
            for chunk in chunks:
                checkpoint()
                key = digest(
                    [
                        "extract-v1",
                        self.model.model_id,
                        self.config.max_entities_per_chunk,
                        self.config.max_relations_per_chunk,
                        self.config.max_quote_chars,
                        self.config.max_input_tokens,
                        self.config.max_output_tokens,
                        chunk.to_dict(),
                    ]
                )
                raw = self.storage.get_cache(key)
                if raw is None:
                    raw = self._call(
                        "extract",
                        {
                            "chunk_id": chunk.chunk_id,
                            "source": chunk.source,
                            "version": chunk.version,
                            "content": chunk.content,
                            "max_entities": self.config.max_entities_per_chunk,
                            "max_relations": self.config.max_relations_per_chunk,
                            "max_quote_chars": self.config.max_quote_chars,
                        },
                    )
                    raw = validate_extraction(raw, chunk, self.config)
                    self.storage.put_cache(key, raw)
                else:
                    extraction_hits += 1
                    raw = validate_extraction(raw, chunk, self.config)
                extracted.append(raw)
                checkpoint()
            knowledge = assemble(chunks, extracted)
            checkpoint()
            clusters = communities(knowledge, self.config)
            reports = []
            for community in clusters:
                inputs = [
                    self._evidence_input(knowledge["evidence"][key], knowledge)
                    for key in community["evidence_ids"]
                ]
                packs = self._packs(
                    inputs,
                    {"community_id": community["id"], "level": community["level"]},
                    "evidence",
                )
                for part, payload in enumerate(packs):
                    checkpoint()
                    if len(reports) >= self.config.max_reports:
                        raise GraphBudgetError(
                            "Community reports exceed max_reports; index was not published"
                        )
                    payload["part"] = part
                    key = digest(
                        [
                            "report-v1",
                            self.model.model_id,
                            self.config.max_input_tokens,
                            self.config.max_output_tokens,
                            payload,
                        ]
                    )
                    raw = self.storage.get_cache(key)
                    if raw is None:
                        raw = self._call("report", payload)
                        self._check_claims(
                            raw, {item["id"] for item in payload["evidence"]}
                        )
                        self.storage.put_cache(key, raw)
                    else:
                        report_hits += 1
                        raw = (
                            SCHEMAS["report"]
                            .model_validate(raw, strict=True)
                            .model_dump(mode="json")
                        )
                        self._check_claims(
                            raw, {item["id"] for item in payload["evidence"]}
                        )
                    reports.append(
                        {
                            "id": "report-" + key[:24],
                            "community_id": community["id"],
                            "level": community["level"],
                            "part": part,
                            **raw,
                            "evidence_ids": [
                                item["id"] for item in payload["evidence"]
                            ],
                        }
                    )
                    checkpoint()
            if self.embedding is not None and knowledge["entities"]:
                checkpoint()
                assets = self.storage.assets / generation
                entity_store = RAGStore(str(assets / "entities.sqlite"))
                for entity in knowledge["entities"].values():
                    text = json.dumps(entity, ensure_ascii=False)
                    entity_store.add_document(
                        text,
                        "entity://" + entity["id"],
                        document_id=entity["id"],
                        chunk_size=len(text) + 1,
                        overlap=0,
                    )
                with QdrantSearch(
                    entity_store, self.embedding, path=str(assets / "vectors")
                ) as index:
                    index.sync(checkpoint=checkpoint)
                checkpoint()
            report = BuildReport(
                generation,
                revision,
                len(chunks),
                len(knowledge["entities"]),
                len(knowledge["relations"]),
                len(clusters),
                len(reports),
                extraction_hits,
                report_hits,
                knowledge["ambiguous_aliases"],
            )
            snapshot = {
                **knowledge,
                "communities": clusters,
                "reports": reports,
                "chunk_ids": [chunk.chunk_id for chunk in chunks],
                "build_report": report.to_dict(),
            }
            checkpoint()
            if self.store.revision != revision:
                raise IndexStaleError(
                    "Canonical documents changed during GraphRAG build; cache retained, nothing published"
                )
            self.storage.publish(
                generation,
                revision,
                self.config_id,
                snapshot,
                expected_generation=active["id"] if active else None,
            )
            return report

    def _load(self):
        active = self.storage.active()
        if (
            not active
            or active["revision"] != self.store.revision
            or active["config_id"] != self.config_id
        ):
            raise IndexStaleError(
                "GraphRAG index is missing or stale; run build() before querying"
            )
        return active, json.loads(active["payload"])

    def _check_revision(self, revision):
        if self.store.revision != revision:
            raise IndexStaleError(
                "Canonical documents changed during the query; rebuild and retry"
            )

    def inspect(self):
        """返回独立且可序列化的快照，供来源审计使用。"""
        active, snapshot = self._load()
        self._check_revision(active["revision"])
        return snapshot

    def local_context(self, query, limit=5):
        from .query import local_context

        return local_context(self, query, limit)

    def local_search(self, query, limit=5):
        return self.local_context(query, limit)["chunks"]

    def search(self, query, limit=5):
        return self.local_search(query, limit)

    def global_search(self, query, *, level=0, checkpoint=None):
        from .query import global_search

        return global_search(self, query, level, checkpoint)
