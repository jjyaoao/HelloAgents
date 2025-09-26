"""记忆存储 - 多类型记忆的统一存储接口"""

from typing import List, Dict, Any, Optional

import logging
import os

from ..base import MemoryItem, MemoryConfig

logger = logging.getLogger(__name__)

class MemoryStore:
    """记忆存储 - 统一存储接口
    
    负责：
    - 多类型记忆的统一存储接口
    - 支持向量、图、文档等多种存储后端
    - 记忆的持久化和序列化
    - 存储性能优化
    """
    
    def __init__(self, config: MemoryConfig):
        self.config = config
        
        # 初始化存储后端
        from ..storage import ChromaVectorStore, NetworkXGraphStore, SQLiteDocumentStore

        self.vector_store = ChromaVectorStore(
            collection_name=f"memory_{config.vector_store_type}",
            persist_directory=config.storage_path
        )
        self.graph_store = NetworkXGraphStore()
        self.document_store = SQLiteDocumentStore(
            db_path=os.path.join(config.storage_path, "memory.db")
        )
        
        logger.info("MemoryStore初始化完成")
    
    def store_memory(self, memory: MemoryItem) -> bool:
        """存储记忆到适当的后端
        
        Args:
            memory: 记忆项
            
        Returns:
            是否存储成功
        """
        try:
            # 根据记忆类型选择存储后端
            if memory.memory_type in ["working", "episodic"]:
                # 工作记忆和情景记忆主要存储在文档数据库
                success = self.document_store.store(memory)
                
                # 同时在向量数据库中存储嵌入
                if success and memory.embedding is not None:
                    self.vector_store.store(memory)
                    
            elif memory.memory_type == "semantic":
                # 语义记忆存储在向量数据库和图数据库
                success = self.vector_store.store(memory)
                if success:
                    self.graph_store.store(memory)
                    
            elif memory.memory_type == "perceptual":
                # 感知记忆主要存储在向量数据库
                success = self.vector_store.store(memory)
                
            else:
                logger.warning(f"未知的记忆类型: {memory.memory_type}")
                return False
            
            return success
            
        except Exception as e:
            logger.error(f"存储记忆失败: {e}")
            return False
    
    def retrieve_memory(self, memory_id: str) -> Optional[MemoryItem]:
        """根据ID检索记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            记忆项或None
        """
        # 首先尝试从文档存储检索
        memory = self.document_store.retrieve(memory_id)
        if memory:
            return memory
        
        # 然后尝试从向量存储检索
        memory = self.vector_store.retrieve(memory_id)
        if memory:
            return memory
        
        # 最后尝试从图存储检索
        memory = self.graph_store.retrieve(memory_id)
        return memory
    
    def update_memory(self, memory: MemoryItem) -> bool:
        """更新记忆
        
        Args:
            memory: 更新后的记忆项
            
        Returns:
            是否更新成功
        """
        try:
            # 更新所有相关的存储后端
            success = True
            
            if memory.memory_type in ["working", "episodic"]:
                success &= self.document_store.update(memory)
                if memory.embedding is not None:
                    success &= self.vector_store.update(memory)
                    
            elif memory.memory_type == "semantic":
                success &= self.vector_store.update(memory)
                success &= self.graph_store.update(memory)
                
            elif memory.memory_type == "perceptual":
                success &= self.vector_store.update(memory)
            
            return success
            
        except Exception as e:
            logger.error(f"更新记忆失败: {e}")
            return False
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            是否删除成功
        """
        try:
            # 从所有存储后端删除
            success = True
            success &= self.document_store.delete(memory_id)
            success &= self.vector_store.delete(memory_id)
            success &= self.graph_store.delete(memory_id)
            
            return success
            
        except Exception as e:
            logger.error(f"删除记忆失败: {e}")
            return False
    
    def search_memories(
        self,
        query: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 10,
        **kwargs
    ) -> List[MemoryItem]:
        """搜索记忆
        
        Args:
            query: 搜索查询
            memory_types: 记忆类型过滤
            limit: 返回数量限制
            **kwargs: 其他搜索参数
            
        Returns:
            搜索结果列表
        """
        results = []
        
        # 向量搜索（语义搜索）
        vector_results = self.vector_store.search(
            query, memory_types, limit, **kwargs
        )
        results.extend(vector_results)
        
        # 文档搜索（关键词搜索）
        doc_results = self.document_store.search(
            query, memory_types, limit, **kwargs
        )
        results.extend(doc_results)
        
        # 图搜索（关系搜索）
        graph_results = self.graph_store.search(
            query, memory_types, limit, **kwargs
        )
        results.extend(graph_results)
        
        # 去重并按相关性排序
        unique_results = self._deduplicate_results(results)
        return sorted(unique_results, key=lambda x: x.relevance_score, reverse=True)[:limit]
    
    def get_memories_by_type(
        self,
        memory_type: str,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[MemoryItem]:
        """根据类型获取记忆
        
        Args:
            memory_type: 记忆类型
            user_id: 用户ID
            limit: 返回数量限制
            
        Returns:
            记忆列表
        """
        if memory_type in ["working", "episodic"]:
            return self.document_store.get_by_type(memory_type, user_id, limit)
        elif memory_type == "semantic":
            return self.vector_store.get_by_type(memory_type, user_id, limit)
        elif memory_type == "perceptual":
            return self.vector_store.get_by_type(memory_type, user_id, limit)
        else:
            return []
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        return {
            "vector_store": self.vector_store.get_stats(),
            "graph_store": self.graph_store.get_stats(),
            "document_store": self.document_store.get_stats()
        }
    
    def cleanup_expired_memories(self, max_age_days: int = 30) -> int:
        """清理过期记忆
        
        Args:
            max_age_days: 最大保存天数
            
        Returns:
            清理的记忆数量
        """
        total_cleaned = 0
        
        # 清理各个存储后端的过期记忆
        total_cleaned += self.document_store.cleanup_expired(max_age_days)
        total_cleaned += self.vector_store.cleanup_expired(max_age_days)
        total_cleaned += self.graph_store.cleanup_expired(max_age_days)
        
        logger.info(f"清理了 {total_cleaned} 条过期记忆")
        return total_cleaned
    
    def backup_memories(self, backup_path: str) -> bool:
        """备份记忆数据
        
        Args:
            backup_path: 备份路径
            
        Returns:
            是否备份成功
        """
        try:
            # 备份各个存储后端
            success = True
            success &= self.document_store.backup(f"{backup_path}/documents")
            success &= self.vector_store.backup(f"{backup_path}/vectors")
            success &= self.graph_store.backup(f"{backup_path}/graphs")
            
            logger.info(f"记忆数据备份到: {backup_path}")
            return success
            
        except Exception as e:
            logger.error(f"备份记忆数据失败: {e}")
            return False
    
    def restore_memories(self, backup_path: str) -> bool:
        """恢复记忆数据
        
        Args:
            backup_path: 备份路径
            
        Returns:
            是否恢复成功
        """
        try:
            # 恢复各个存储后端
            success = True
            success &= self.document_store.restore(f"{backup_path}/documents")
            success &= self.vector_store.restore(f"{backup_path}/vectors")
            success &= self.graph_store.restore(f"{backup_path}/graphs")
            
            logger.info(f"从 {backup_path} 恢复记忆数据")
            return success
            
        except Exception as e:
            logger.error(f"恢复记忆数据失败: {e}")
            return False
    
    def _deduplicate_results(self, results: List[MemoryItem]) -> List[MemoryItem]:
        """去重搜索结果"""
        seen_ids = set()
        unique_results = []
        
        for result in results:
            if result.id not in seen_ids:
                seen_ids.add(result.id)
                unique_results.append(result)
        
        return unique_results
    
    def close(self):
        """关闭存储连接"""
        self.vector_store.close()
        self.graph_store.close()
        self.document_store.close()
        logger.info("MemoryStore已关闭")
