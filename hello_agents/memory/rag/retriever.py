"""检索器实现"""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np
from .embeddings import EmbeddingModel
from ..storage.vector_store import VectorStore
from .document import DocumentChunk

class Retriever(ABC):
    """检索器基类"""
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> List[DocumentChunk]:
        """检索相关文档"""
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[DocumentChunk]) -> List[str]:
        """添加文档到检索器"""
        pass

class VectorRetriever(Retriever):
    """向量检索器"""
    
    def __init__(self, embedding_model: EmbeddingModel, vector_store: VectorStore):
        self.embedding_model = embedding_model
        self.vector_store = vector_store
    
    def add_documents(self, documents: List[DocumentChunk]) -> List[str]:
        """
        添加文档到向量存储
        
        Args:
            documents: 文档块列表
            
        Returns:
            文档ID列表
        """
        if not documents:
            return []
        
        # 提取文本内容
        texts = [doc.content for doc in documents]

        # 如果是TF-IDF模型且未训练，先训练
        if hasattr(self.embedding_model, '_is_fitted') and not self.embedding_model._is_fitted:
            self.embedding_model.fit(texts)

        # 生成嵌入向量
        embeddings = self.embedding_model.encode(texts)

        # 确保embeddings是列表格式
        if isinstance(embeddings, np.ndarray):
            if embeddings.ndim == 1:
                # 单个向量，转换为列表
                embeddings = [embeddings]
            elif embeddings.ndim == 2:
                # 多个向量，转换为列表
                embeddings = [embedding for embedding in embeddings]
        elif not isinstance(embeddings, list):
            # 其他情况，确保是列表
            embeddings = [embeddings]
        
        # 准备元数据
        metadata_list = []
        for doc in documents:
            metadata = doc.metadata.copy()
            metadata.update({
                "content": doc.content,
                "chunk_id": doc.chunk_id,
                "doc_id": doc.doc_id,
                "chunk_index": doc.chunk_index
            })
            metadata_list.append(metadata)
        
        # 添加到向量存储
        ids = [doc.chunk_id for doc in documents]
        return self.vector_store.add(embeddings, metadata_list, ids)
    
    def retrieve(self, query: str, top_k: int = 5) -> List[DocumentChunk]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            相关文档块列表
        """
        # 生成查询向量
        query_embedding = self.embedding_model.encode(query)
        
        # 搜索相似向量
        search_results = self.vector_store.search_similar(query_embedding, top_k)
        
        # 转换为DocumentChunk对象
        document_chunks = []
        for result in search_results:
            chunk = DocumentChunk(
                content=result.get("content", ""),
                metadata={key: value for key, value in result.items() if key not in ["memory_id", "content"]},
                chunk_id=result.get("memory_id"),
                doc_id=result.get("doc_id"),
                chunk_index=result.get("chunk_index", 0)
            )
            # 添加相似度分数到元数据
            chunk.metadata["similarity_score"] = result.get("similarity_score", 0.0)
            document_chunks.append(chunk)
        
        return document_chunks

class KeywordRetriever(Retriever):
    """关键词检索器（基于TF-IDF）"""
    
    def __init__(self):
        self.documents: List[DocumentChunk] = []
        self.vectorizer = None
        self.tfidf_matrix = None
        self._init_vectorizer()
    
    def _init_vectorizer(self):
        """初始化TF-IDF向量化器"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            self.vectorizer = TfidfVectorizer(
                stop_words='english',
                max_features=5000,
                ngram_range=(1, 2)
            )
            self.cosine_similarity = cosine_similarity
        except ImportError:
            raise ImportError("请安装 scikit-learn: pip install scikit-learn")
    
    def add_documents(self, documents: List[DocumentChunk]) -> List[str]:
        """
        添加文档到关键词检索器
        
        Args:
            documents: 文档块列表
            
        Returns:
            文档ID列表
        """
        self.documents.extend(documents)
        
        # 重新训练TF-IDF
        if self.documents:
            texts = [doc.content for doc in self.documents]
            self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        
        return [doc.chunk_id for doc in documents]
    
    def retrieve(self, query: str, top_k: int = 5) -> List[DocumentChunk]:
        """
        基于关键词检索文档
        
        Args:
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            相关文档块列表
        """
        if not self.documents or self.tfidf_matrix is None:
            return []
        
        # 转换查询为TF-IDF向量
        query_vector = self.vectorizer.transform([query])
        
        # 计算相似度
        similarities = self.cosine_similarity(query_vector, self.tfidf_matrix).flatten()
        
        # 获取最相似的文档索引
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        # 构建结果
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:  # 只返回有相似度的结果
                doc = self.documents[idx]
                # 创建副本并添加相似度分数
                result_doc = DocumentChunk(
                    content=doc.content,
                    metadata=doc.metadata.copy(),
                    chunk_id=doc.chunk_id,
                    doc_id=doc.doc_id,
                    chunk_index=doc.chunk_index
                )
                result_doc.metadata["similarity_score"] = float(similarities[idx])
                results.append(result_doc)
        
        return results

class HybridRetriever(Retriever):
    """混合检索器（结合向量和关键词检索）"""
    
    def __init__(
        self,
        vector_retriever: VectorRetriever,
        keyword_retriever: Optional[KeywordRetriever] = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ):
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever or KeywordRetriever()
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
    
    def add_documents(self, documents: List[DocumentChunk]) -> List[str]:
        """
        添加文档到混合检索器
        
        Args:
            documents: 文档块列表
            
        Returns:
            文档ID列表
        """
        # 添加到两个检索器
        vector_ids = self.vector_retriever.add_documents(documents)
        keyword_ids = self.keyword_retriever.add_documents(documents)
        
        return vector_ids  # 返回向量检索器的ID
    
    def retrieve(self, query: str, top_k: int = 5) -> List[DocumentChunk]:
        """
        混合检索文档
        
        Args:
            query: 查询文本
            top_k: 返回数量
            
        Returns:
            相关文档块列表
        """
        # 从两个检索器获取结果
        vector_results = self.vector_retriever.retrieve(query, top_k * 2)
        keyword_results = self.keyword_retriever.retrieve(query, top_k * 2)
        
        # 合并和重新排序结果
        combined_results = self._combine_results(vector_results, keyword_results)
        
        # 返回前top_k个结果
        return combined_results[:top_k]
    
    def _combine_results(
        self,
        vector_results: List[DocumentChunk],
        keyword_results: List[DocumentChunk]
    ) -> List[DocumentChunk]:
        """
        合并两种检索结果
        
        Args:
            vector_results: 向量检索结果
            keyword_results: 关键词检索结果
            
        Returns:
            合并后的结果列表
        """
        # 创建文档ID到分数的映射
        doc_scores = {}
        
        # 处理向量检索结果
        for doc in vector_results:
            doc_id = doc.chunk_id
            vector_score = doc.metadata.get("similarity_score", 0)
            doc_scores[doc_id] = {
                "doc": doc,
                "vector_score": vector_score,
                "keyword_score": 0
            }
        
        # 处理关键词检索结果
        for doc in keyword_results:
            doc_id = doc.chunk_id
            keyword_score = doc.metadata.get("similarity_score", 0)
            
            if doc_id in doc_scores:
                doc_scores[doc_id]["keyword_score"] = keyword_score
            else:
                doc_scores[doc_id] = {
                    "doc": doc,
                    "vector_score": 0,
                    "keyword_score": keyword_score
                }
        
        # 计算综合分数并排序
        scored_docs = []
        for doc_id, scores in doc_scores.items():
            combined_score = (
                self.vector_weight * scores["vector_score"] +
                self.keyword_weight * scores["keyword_score"]
            )
            
            doc = scores["doc"]
            # 更新元数据
            doc.metadata.update({
                "vector_score": scores["vector_score"],
                "keyword_score": scores["keyword_score"],
                "combined_score": combined_score
            })
            
            scored_docs.append((combined_score, doc))
        
        # 按综合分数排序
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        return [doc for _, doc in scored_docs]
    
    def update_weights(self, vector_weight: float, keyword_weight: float):
        """
        更新检索权重
        
        Args:
            vector_weight: 向量检索权重
            keyword_weight: 关键词检索权重
        """
        total_weight = vector_weight + keyword_weight
        self.vector_weight = vector_weight / total_weight
        self.keyword_weight = keyword_weight / total_weight
