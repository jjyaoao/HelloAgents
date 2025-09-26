"""向量存储实现

支持多种向量数据库后端：
- Chroma: 轻量级向量数据库
- FAISS: 高性能相似性搜索库
- Milvus: 企业级分布式向量数据库（可扩展）
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np
import os

class VectorStore(ABC):
    """向量存储基类"""
    
    @abstractmethod
    def add_vectors(self, memories: List[Dict[str, Any]]) -> List[str]:
        """添加向量到存储
        
        Args:
            memories: 记忆数据列表，每个包含embedding和metadata
            
        Returns:
            向量ID列表
        """
        pass
    
    @abstractmethod
    def search_similar(
        self,
        query_vector: List[float],
        top_k: int = 10,
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索相似向量
        
        Args:
            query_vector: 查询向量
            top_k: 返回数量
            user_id: 用户ID过滤
            memory_type: 记忆类型过滤
            
        Returns:
            相似记忆列表
        """
        pass
    
    @abstractmethod
    def delete_memories(self, memory_ids: List[str]):
        """删除指定记忆"""
        pass
    
    @abstractmethod
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        pass

class ChromaVectorStore(VectorStore):
    """Chroma向量存储实现"""
    
    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "memory_vectors"
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        self._init_chroma()
    
    def _init_chroma(self):
        """初始化Chroma客户端"""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # 创建持久化客户端
            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 获取或创建集合
            try:
                self._collection = self._client.get_collection(self.collection_name)
                print(f"✅ 获取现有Chroma集合: {self.collection_name}")
            except:
                self._collection = self._client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "HelloAgents记忆向量存储"}
                )
                print(f"✅ 创建新Chroma集合: {self.collection_name}")
                
        except ImportError:
            raise ImportError("请安装 chromadb: pip install chromadb")
    
    def add_vectors(self, memories: List[Dict[str, Any]]) -> List[str]:
        """添加向量到Chroma"""
        if not memories:
            return []
        
        # 准备数据
        ids = [mem.get("memory_id", f"mem_{i}") for i, mem in enumerate(memories)]
        embeddings = [mem["embedding"] for mem in memories]
        documents = [mem["content"] for mem in memories]
        metadatas = [
            {
                "user_id": mem["user_id"],
                "memory_type": mem["memory_type"],
                "timestamp": mem["timestamp"],
                "importance": mem["importance"]
            }
            for mem in memories
        ]
        
        # 添加到集合
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        print(f"✅ 成功添加 {len(memories)} 条记忆向量到Chroma")
        return ids

    def add(self, embeddings: List[List[float]], metadata_list: List[Dict[str, Any]], ids: List[str]) -> List[str]:
        """
        添加向量（RAG检索器接口）

        Args:
            embeddings: 嵌入向量列表
            metadata_list: 元数据列表
            ids: ID列表

        Returns:
            添加的ID列表
        """
        if not embeddings or not metadata_list or not ids:
            return []

        # 提取文档内容
        documents = [meta.get("content", "") for meta in metadata_list]

        # 添加到集合
        self._collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadata_list,
            ids=ids
        )

        return ids
    
    def search_similar(
        self,
        query_vector: List[float],
        top_k: int = 10,
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        # 构建过滤条件
        where_filter = {}
        if user_id:
            where_filter["user_id"] = user_id
        if memory_type:
            where_filter["memory_type"] = memory_type
        
        # 执行搜索
        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where_filter if where_filter else None,
            include=["documents", "metadatas", "distances"]
        )
        
        # 处理结果
        similar_memories = []
        if results["ids"] and results["ids"][0]:
            for i, memory_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                result_item = {
                    "memory_id": memory_id,
                    "content": results["documents"][0][i],
                    "similarity_score": 1.0 - results["distances"][0][i]  # 转换为相似度
                }

                # 添加所有元数据字段（兼容记忆系统和RAG系统）
                for key, value in metadata.items():
                    result_item[key] = value

                # 为兼容性添加默认字段（如果不存在）
                if "user_id" not in result_item:
                    result_item["user_id"] = "default"
                if "memory_type" not in result_item:
                    result_item["memory_type"] = "document"
                if "timestamp" not in result_item:
                    result_item["timestamp"] = ""
                if "importance" not in result_item:
                    result_item["importance"] = 0.5

                similar_memories.append(result_item)

        return similar_memories
    
    def delete_memories(self, memory_ids: List[str]):
        """删除指定记忆"""
        if not memory_ids:
            return
        
        self._collection.delete(ids=memory_ids)
        print(f"✅ 成功从Chroma删除 {len(memory_ids)} 条记忆")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        count = self._collection.count()
        return {
            "total_entities": count,
            "collection_name": self.collection_name,
            "persist_directory": self.persist_directory,
            "store_type": "chroma"
        }

class FAISSVectorStore(VectorStore):
    """FAISS向量存储实现"""
    
    def __init__(
        self,
        dimension: int = 768,
        index_type: str = "Flat",
        persist_path: str = "./faiss_db"
    ):
        self.dimension = dimension
        self.index_type = index_type
        self.persist_path = persist_path
        
        # 创建存储目录
        os.makedirs(persist_path, exist_ok=True)
        
        # 初始化FAISS索引
        self._index = None
        self._metadata = {}  # id -> metadata映射
        self._id_counter = 0
        
        self._init_faiss()
        self._load_existing_data()
    
    def _init_faiss(self):
        """初始化FAISS索引"""
        try:
            import faiss
            
            if self.index_type == "IVF":
                # 创建IVF索引
                quantizer = faiss.IndexFlatL2(self.dimension)
                self._index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
            elif self.index_type == "HNSW":
                # 创建HNSW索引
                self._index = faiss.IndexHNSWFlat(self.dimension, 32)
            else:
                # 默认使用平坦索引
                self._index = faiss.IndexFlatL2(self.dimension)
                
            print(f"✅ FAISS向量存储初始化完成: {self.index_type}, 维度: {self.dimension}")
            
        except ImportError:
            raise ImportError("请安装 faiss: pip install faiss-cpu 或 pip install faiss-gpu")
    
    def _load_existing_data(self):
        """加载现有数据"""
        import faiss
        import json
        
        index_path = os.path.join(self.persist_path, "faiss.index")
        metadata_path = os.path.join(self.persist_path, "metadata.json")
        
        if os.path.exists(index_path):
            self._index = faiss.read_index(index_path)
            print(f"✅ 加载现有FAISS索引: {self._index.ntotal} 条向量")
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                self._metadata = json.load(f)
            self._id_counter = max([int(k) for k in self._metadata.keys()], default=0) + 1
            print(f"✅ 加载现有元数据: {len(self._metadata)} 条记录")
    
    def _save_data(self):
        """保存数据"""
        import faiss
        import json
        
        index_path = os.path.join(self.persist_path, "faiss.index")
        metadata_path = os.path.join(self.persist_path, "metadata.json")
        
        # 保存索引
        faiss.write_index(self._index, index_path)
        
        # 保存元数据
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self._metadata, f, ensure_ascii=False, indent=2)
    
    def add_vectors(self, memories: List[Dict[str, Any]]) -> List[str]:
        """添加向量到FAISS"""
        if not memories:
            return []
        
        # 准备向量数据
        vectors = np.array([mem["embedding"] for mem in memories], dtype=np.float32)
        
        # 如果是IVF索引且未训练，先训练
        if self.index_type == "IVF" and not self._index.is_trained:
            if vectors.shape[0] >= 100:
                self._index.train(vectors)
                print("✅ FAISS IVF索引训练完成")
        
        # 生成ID并添加向量
        start_id = self._id_counter
        ids = list(range(start_id, start_id + len(memories)))
        
        self._index.add(vectors)
        
        # 保存元数据
        for i, memory in enumerate(memories):
            memory_id = ids[i]
            self._metadata[str(memory_id)] = {
                "memory_id": memory.get("memory_id", f"mem_{memory_id}"),
                "user_id": memory["user_id"],
                "content": memory["content"],
                "memory_type": memory["memory_type"],
                "timestamp": memory["timestamp"],
                "importance": memory["importance"]
            }
        
        self._id_counter += len(memories)
        
        # 持久化数据
        self._save_data()
        
        print(f"✅ 成功添加 {len(memories)} 条记忆向量到FAISS")
        return [str(id) for id in ids]
    
    def search_similar(
        self,
        query_vector: List[float],
        top_k: int = 10,
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索相似向量"""
        if self._index.ntotal == 0:
            return []
        
        # 转换查询向量
        query_array = np.array([query_vector], dtype=np.float32)
        
        # 执行搜索
        distances, indices = self._index.search(query_array, min(top_k * 2, self._index.ntotal))
        
        # 处理结果并应用过滤
        similar_memories = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:  # FAISS返回-1表示无效结果
                continue
            
            metadata = self._metadata.get(str(idx))
            if not metadata:
                continue
            
            # 应用过滤条件
            if user_id and metadata["user_id"] != user_id:
                continue
            if memory_type and metadata["memory_type"] != memory_type:
                continue
            
            similar_memories.append({
                "id": idx,
                "memory_id": metadata["memory_id"],
                "user_id": metadata["user_id"],
                "content": metadata["content"],
                "memory_type": metadata["memory_type"],
                "timestamp": metadata["timestamp"],
                "importance": metadata["importance"],
                "similarity_score": 1.0 / (1.0 + distances[0][i])  # 转换为相似度分数
            })
            
            if len(similar_memories) >= top_k:
                break
        
        return similar_memories
    
    def delete_memories(self, memory_ids: List[str]):
        """删除指定记忆（FAISS不支持直接删除，标记删除）"""
        if not memory_ids:
            return
        
        # 从元数据中删除
        deleted_count = 0
        for memory_id in memory_ids:
            for idx, metadata in list(self._metadata.items()):
                if metadata["memory_id"] == memory_id:
                    del self._metadata[idx]
                    deleted_count += 1
        
        # 保存元数据
        self._save_data()
        
        print(f"✅ 成功从FAISS删除 {deleted_count} 条记忆")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取集合统计信息"""
        return {
            "total_entities": self._index.ntotal,
            "dimension": self.dimension,
            "index_type": self.index_type,
            "persist_path": self.persist_path,
            "is_trained": getattr(self._index, 'is_trained', True),
            "store_type": "faiss"
        }
