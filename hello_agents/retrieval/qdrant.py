"""Qdrant 向量索引：SQLite 保存证据，向量集合保存可重建的检索索引。"""

from dataclasses import dataclass, replace
import threading
import uuid
import warnings
from typing import List

from .embeddings import EmbeddingProvider, validate_vectors
from .store import RAGStore, RetrievalResult


class IndexStaleError(RuntimeError):
    """资料已变更或尚未建立索引，需要显式调用 sync。"""


@dataclass(frozen=True)
class QdrantCloudInference:
    """由 Qdrant Cloud 编码文本，无需本地模型或另一份嵌入 API Key。

    默认使用托管的多语言模型；更换模型时须同时核对维度并使用新集合。
    这是一份云端推理配置，不是本地 EmbeddingProvider。
    """

    model: str = "intfloat/multilingual-e5-small"
    dimension: int = 384

    def __post_init__(self):
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model 必须是非空字符串")
        if type(self.dimension) is not int or self.dimension <= 0:
            raise ValueError("dimension 必须是正整数")

    @property
    def model_id(self):
        return f"qdrant-cloud:{self.model}:{self.dimension}"


class QdrantSearch:
    """真实 Qdrant 本地或远程后端，接口与 RAGStore.search 一致。

    path、url、client 三选一；注入的 client 由宿主管理生命周期。
    sync 使用完整新代次并在上传完成后切换清单；失败不发布半成品。
    同一资料库的同步应由一个写入任务执行，跨进程调度由宿主负责。
    本组件不提供分布式索引调度或应用级访问授权。
    """

    def __init__(
        self,
        store: RAGStore,
        embedding: EmbeddingProvider | QdrantCloudInference,
        *,
        path: str = None,
        url: str = None,
        client=None,
        collection: str = "hello_agents",
        api_key: str = None,
        timeout: float = 30,
    ):
        if sum(value is not None for value in (path, url, client)) != 1:
            raise ValueError("path、url、client 必须且只能提供一个")
        self._cloud_inference = isinstance(embedding, QdrantCloudInference)
        if self._cloud_inference:
            if not isinstance(url, str) or not url.startswith("https://"):
                raise ValueError(
                    "云端推理需要 HTTPS 集群 url，不能使用本地 path 或注入 client"
                )
            if not isinstance(api_key, str) or not api_key.strip():
                raise ValueError("云端推理需要 Qdrant 集群 API Key")
        if not isinstance(collection, str) or not collection.strip():
            raise ValueError("collection 必须是非空字符串")
        if (
            type(embedding.dimension) is not int
            or embedding.dimension <= 0
            or not isinstance(embedding.model_id, str)
            or not embedding.model_id.strip()
        ):
            raise ValueError(
                "EmbeddingProvider 必须提供正整数 dimension 和非空 model_id"
            )
        try:
            from qdrant_client import QdrantClient, models
        except ImportError as exc:
            raise ImportError(
                "向量检索需要 pip install 'hello-agents[qdrant]'"
            ) from exc
        self.store = store
        self.embedding = embedding
        self.collection = collection
        self.namespace = store.namespace
        self._models = models
        self._owns_client = client is None
        self._lock = threading.RLock()
        self._closed = False
        self.client = (
            client
            if client is not None
            else (
                QdrantClient(location=":memory:")
                if path == ":memory:"
                else (
                    QdrantClient(path=path)
                    if path is not None
                    else QdrantClient(
                        url=url,
                        api_key=api_key,
                        timeout=timeout,
                        cloud_inference=self._cloud_inference,
                    )
                )
            )
        )
        self._manifest_id = str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"helloagents:{self.namespace}:manifest")
        )
        try:
            if not self.client.collection_exists(collection):
                self.client.create_collection(
                    collection,
                    vectors_config=models.VectorParams(
                        size=embedding.dimension, distance=models.Distance.COSINE
                    ),
                )
            collection_info = self.client.get_collection(collection)
            config = collection_info.config.params.vectors
            if (
                not isinstance(config, models.VectorParams)
                or config.size != embedding.dimension
                or config.distance != models.Distance.COSINE
            ):
                raise ValueError(
                    "集合必须使用与 EmbeddingProvider 维度一致的单个余弦向量；请换用新集合"
                )
            self._manifest()
            if url is not None:
                # 云端严格模式不允许对未建立索引的载荷字段进行过滤。
                # 上传向量点前先创建字段索引，已有索引直接复用。
                for field in ("namespace", "kind", "generation", "model_id"):
                    if field not in collection_info.payload_schema:
                        self.client.create_payload_index(
                            collection,
                            field_name=field,
                            field_schema=models.PayloadSchemaType.KEYWORD,
                            wait=True,
                        )
        except Exception:
            self.close()
            raise

    def _ensure_open(self):
        if self._closed:
            raise RuntimeError("QdrantSearch 已关闭")

    def _manifest(self):
        self._ensure_open()
        points = self.client.retrieve(
            self.collection,
            ids=[self._manifest_id],
            with_payload=True,
            with_vectors=False,
        )
        if not points:
            return None
        payload = points[0].payload or {}
        if (
            payload.get("namespace") != self.namespace
            or payload.get("kind") != "manifest"
        ):
            raise ValueError("索引清单不属于当前资料库")
        if payload.get("model_id") != self.embedding.model_id:
            raise ValueError("索引使用了不同的嵌入模型或预处理配置，请创建新集合")
        if (
            not isinstance(payload.get("generation"), str)
            or type(payload.get("revision")) is not int
        ):
            raise ValueError("索引清单格式无效，请创建新集合")
        return payload

    def _filter(self, generation: str):
        m = self._models
        return m.Filter(
            must=[
                m.FieldCondition(key=key, match=m.MatchValue(value=value))
                for key, value in {
                    "namespace": self.namespace,
                    "kind": "chunk",
                    "generation": generation,
                    "model_id": self.embedding.model_id,
                }.items()
            ]
        )

    def sync(self, *, batch_size: int = 64, checkpoint=None) -> int:
        """同步当前资料版本，返回实际编码的片段数；未变化时不重复编码。

        新代次先完整写入，随后发布清单，最后回收上一代。同步中断可能留下
        不可见的向量，可由运维清理；检索不会读取未发布代次。
        """
        if type(batch_size) is not int or not 1 <= batch_size <= 1024:
            raise ValueError("batch_size 必须是 1 到 1024 的整数")
        if checkpoint is not None and not callable(checkpoint):
            raise TypeError("checkpoint must be callable or None")
        check = checkpoint or (lambda: None)
        with self._lock:
            check()
            previous = self._manifest()
            revision, chunks = self.store.snapshot()
            if previous and previous["revision"] == revision:
                return 0
            generation = str(uuid.uuid4())
            m = self._models
            for start in range(0, len(chunks), batch_size):
                check()
                batch = chunks[start : start + batch_size]
                if self._cloud_inference:
                    vectors = [
                        m.Document(text=item.content, model=self.embedding.model)
                        for item in batch
                    ]
                else:
                    vectors = validate_vectors(
                        self.embedding.embed_documents(
                            [item.content for item in batch]
                        ),
                        len(batch),
                        self.embedding.dimension,
                    )
                points = [
                    m.PointStruct(
                        id=str(
                            uuid.uuid5(
                                uuid.NAMESPACE_URL,
                                f"{self.namespace}:{generation}:{item.chunk_id}",
                            )
                        ),
                        vector=vector,
                        payload={
                            "namespace": self.namespace,
                            "kind": "chunk",
                            "generation": generation,
                            "model_id": self.embedding.model_id,
                            "chunk_id": item.chunk_id,
                        },
                    )
                    for item, vector in zip(batch, vectors)
                ]
                self.client.upsert(self.collection, points=points, wait=True)
            check()
            if self.store.revision != revision:
                raise IndexStaleError(
                    "资料在同步期间发生变化，未发布该代次；请重新 sync()"
                )
            manifest = {
                "namespace": self.namespace,
                "kind": "manifest",
                "generation": generation,
                "model_id": self.embedding.model_id,
                "revision": revision,
                "count": len(chunks),
            }
            self.client.upsert(
                self.collection,
                points=[
                    m.PointStruct(
                        id=self._manifest_id,
                        vector=[1.0] + [0.0] * (self.embedding.dimension - 1),
                        payload=manifest,
                    )
                ],
                wait=True,
            )
            if previous:
                try:
                    self.client.delete(
                        self.collection,
                        points_selector=m.FilterSelector(
                            filter=self._filter(previous["generation"])
                        ),
                        wait=True,
                    )
                except Exception as exc:
                    warnings.warn(
                        f"新索引已发布，旧代次回收失败（{type(exc).__name__}）；旧代次不会参与检索",
                        RuntimeWarning,
                    )
            return len(chunks)

    def search(self, query: str, limit: int = 5) -> List[RetrievalResult]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query 必须是非空字符串")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit 必须是 1 到 100 的整数")
        with self._lock:
            manifest = self._manifest()
            revision = self.store.revision
            if not manifest or manifest["revision"] != revision:
                raise IndexStaleError("资料与向量索引尚未同步，请先调用 sync()")
            if self._cloud_inference:
                vector = self._models.Document(text=query, model=self.embedding.model)
            else:
                vector = validate_vectors(
                    [self.embedding.embed_query(query)], 1, self.embedding.dimension
                )[0]
            hits = self.client.query_points(
                self.collection,
                query=vector,
                query_filter=self._filter(manifest["generation"]),
                limit=limit,
                with_payload=True,
                with_vectors=False,
            ).points
            results = []
            for hit in hits:
                try:
                    item = self.store.read_chunk((hit.payload or {})["chunk_id"])
                    current = self.store.read_document(item.document_id)
                except KeyError as exc:
                    raise IndexStaleError("向量片段已无有效原文，请重建索引") from exc
                if current.version != item.version or not current.active:
                    raise IndexStaleError("向量片段不再属于当前文档版本，请同步索引")
                results.append(replace(item, score=float(hit.score)))
            if self.store.revision != revision:
                raise IndexStaleError("资料在检索期间发生变化，请同步后重试")
            return results

    def purge_namespace(self):
        """仅删除当前存储的向量点与清单；操作前先停止所有写入。

        保留 SQLite 原始记录，需要时可通过 sync 重建索引。
        """
        self._ensure_open()
        with self._lock:
            m = self._models
            self.client.delete(
                self.collection,
                points_selector=m.FilterSelector(
                    filter=m.Filter(
                        must=[
                            m.FieldCondition(
                                key="namespace",
                                match=m.MatchValue(value=self.namespace),
                            )
                        ]
                    )
                ),
                wait=True,
            )

    def close(self):
        if not self._closed:
            self._closed = True
            if self._owns_client:
                self.client.close()

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, *_):
        self.close()
