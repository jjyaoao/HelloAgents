"""独立于对话模型的向量接口；可选模型仅在实际使用时加载。"""

import hashlib
import json
import math
from typing import List, Protocol, Sequence


class EmbeddingProvider(Protocol):
    """model_id 标识模型及预处理配置；配置变化时必须更换标识。"""

    model_id: str
    dimension: int

    def embed_documents(self, texts: Sequence[str]) -> List[List[float]]: ...

    def embed_query(self, text: str) -> List[float]: ...


def validate_vectors(vectors, count: int, dimension: int) -> List[List[float]]:
    """在写入索引前检查数量、维度、有限数值及非零范数。"""
    result = [list(vector) for vector in vectors]
    if len(result) != count:
        raise ValueError("向量数量与输入数量不一致")
    for vector in result:
        if len(vector) != dimension:
            raise ValueError(f"向量维度必须为 {dimension}")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in vector
        ):
            raise ValueError("向量必须包含有限数值")
        if not any(vector):
            raise ValueError("余弦检索不接受零向量")
    return [[float(value) for value in vector] for vector in result]


class OpenAIEmbeddingProvider:
    """调用 OpenAI 兼容 Embeddings 接口，模型和维度由使用者明确配置。

    client 由调用方管理生命周期。dimension 用于校验；只有显式设置
    request_dimensions=True 才向服务发送 dimensions 参数。
    """

    def __init__(
        self,
        client,
        model: str,
        dimension: int,
        *,
        request_dimensions: bool = False,
        model_id: str = None,
    ):
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model 必须是非空字符串")
        if type(dimension) is not int or dimension <= 0:
            raise ValueError("dimension 必须是正整数")
        self.client = client
        self.model = model
        self.dimension = dimension
        self.request_dimensions = request_dimensions
        identity = json.dumps(
            [
                str(getattr(client, "base_url", "custom")),
                model,
                dimension,
                request_dimensions,
            ]
        )
        self.model_id = (
            model_id or "openai:" + hashlib.sha256(identity.encode()).hexdigest()
        )

    def embed_documents(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        kwargs = {"model": self.model, "input": list(texts)}
        if self.request_dimensions:
            kwargs["dimensions"] = self.dimension
        response = self.client.embeddings.create(**kwargs)
        rows = sorted(response.data, key=lambda item: item.index)
        if [item.index for item in rows] != list(range(len(texts))):
            raise ValueError("Embedding 服务返回了缺失或重复的输入索引")
        return validate_vectors(
            (item.embedding for item in rows), len(texts), self.dimension
        )

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


class FastEmbedProvider:
    """本地 ONNX 向量模型；第一次编码可能下载模型权重。

    查询使用 query_embed，文档使用 passage_embed，以遵循模型各自的前缀规则。
    dimension 须与所选模型一致；更换模型时应创建新向量集合。
    """

    def __init__(
        self,
        model_name: str,
        dimension: int,
        *,
        cache_dir: str = None,
        local_files_only: bool = False,
        model_id: str = None,
    ):
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name 必须是非空字符串")
        if type(dimension) is not int or dimension <= 0:
            raise ValueError("dimension 必须是正整数")
        self.model_name = model_name
        self.dimension = dimension
        self.model_id = (
            model_id or f"fastembed:{model_name}:passage-query:v1:{dimension}"
        )
        self.cache_dir = cache_dir
        self.local_files_only = local_files_only
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:
                raise ImportError(
                    "本地向量模型需要 pip install 'hello-agents[fastembed]'"
                ) from exc
            self._model = TextEmbedding(
                model_name=self.model_name,
                cache_dir=self.cache_dir,
                local_files_only=self.local_files_only,
            )
        return self._model

    def embed_documents(self, texts: Sequence[str]) -> List[List[float]]:
        if not texts:
            return []
        vectors = (
            vector.tolist() for vector in self._load().passage_embed(list(texts))
        )
        return validate_vectors(vectors, len(texts), self.dimension)

    def embed_query(self, text: str) -> List[float]:
        vectors = (vector.tolist() for vector in self._load().query_embed(text))
        return validate_vectors(vectors, 1, self.dimension)[0]
