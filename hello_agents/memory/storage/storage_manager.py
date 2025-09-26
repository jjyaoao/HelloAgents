"""统一存储管理器

按照第8章架构设计的统一存储管理器，提供：
- 多种存储后端的统一接口
- 灵活的配置管理
- 自动初始化和连接管理
"""

from typing import Dict, Any, List, Union
from enum import Enum
import logging

class StorageType(Enum):
    """存储类型枚举"""
    VECTOR_CHROMA = "vector_chroma"
    VECTOR_FAISS = "vector_faiss"
    VECTOR_MILVUS = "vector_milvus"
    GRAPH_NETWORKX = "graph_networkx"
    GRAPH_NEO4J = "graph_neo4j"
    DOCUMENT_SQLITE = "document_sqlite"
    DOCUMENT_POSTGRESQL = "document_postgresql"

class UnifiedStorageManager:
    """统一存储管理器
    
    提供多种存储后端的统一管理和访问接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化存储管理器
        
        Args:
            config: 存储配置字典
        """
        self.config = config
        self.stores = {}
        self.logger = logging.getLogger(__name__)
        
        # 初始化各种存储
        self._init_stores()
    
    def _init_stores(self):
        """初始化存储实例"""
        for store_type, store_config in self.config.items():
            if not store_config.get("enabled", False):
                continue
            
            try:
                if store_type == StorageType.VECTOR_CHROMA.value:
                    from .vector_store import ChromaVectorStore
                    self.stores[store_type] = ChromaVectorStore(**store_config.get("params", {}))
                
                elif store_type == StorageType.VECTOR_FAISS.value:
                    from .vector_store import FAISSVectorStore
                    self.stores[store_type] = FAISSVectorStore(**store_config.get("params", {}))
                
                elif store_type == StorageType.GRAPH_NETWORKX.value:
                    from .graph_store import NetworkXGraphStore
                    self.stores[store_type] = NetworkXGraphStore(**store_config.get("params", {}))
                
                elif store_type == StorageType.DOCUMENT_SQLITE.value:
                    from .document_store import SQLiteDocumentStore
                    self.stores[store_type] = SQLiteDocumentStore(**store_config.get("params", {}))
                
                # 可扩展其他存储类型
                # elif store_type == StorageType.VECTOR_MILVUS.value:
                #     from .vector_store import MilvusVectorStore
                #     self.stores[store_type] = MilvusVectorStore(**store_config.get("params", {}))
                
                self.logger.info(f"✅ 成功初始化存储: {store_type}")
                
            except ImportError as e:
                self.logger.warning(f"⚠️ 跳过存储初始化 {store_type}: 缺少依赖 - {e}")
            except Exception as e:
                self.logger.error(f"❌ 初始化存储失败 {store_type}: {e}")
    
    def get_vector_store(self, store_type: str = None):
        """获取向量存储实例
        
        Args:
            store_type: 指定存储类型，如果为None则返回第一个可用的
            
        Returns:
            向量存储实例
        """
        if store_type:
            return self.stores.get(store_type)
        
        # 返回第一个可用的向量存储
        for store_type in [
            StorageType.VECTOR_CHROMA.value,
            StorageType.VECTOR_FAISS.value,
            StorageType.VECTOR_MILVUS.value
        ]:
            if store_type in self.stores:
                return self.stores[store_type]
        
        return None
    
    def get_graph_store(self, store_type: str = None):
        """获取图存储实例
        
        Args:
            store_type: 指定存储类型，如果为None则返回第一个可用的
            
        Returns:
            图存储实例
        """
        if store_type:
            return self.stores.get(store_type)
        
        # 返回第一个可用的图存储
        for store_type in [
            StorageType.GRAPH_NEO4J.value,
            StorageType.GRAPH_NETWORKX.value
        ]:
            if store_type in self.stores:
                return self.stores[store_type]
        
        return None
    
    def get_document_store(self, store_type: str = None):
        """获取文档存储实例
        
        Args:
            store_type: 指定存储类型，如果为None则返回第一个可用的
            
        Returns:
            文档存储实例
        """
        if store_type:
            return self.stores.get(store_type)
        
        # 返回第一个可用的文档存储
        for store_type in [
            StorageType.DOCUMENT_POSTGRESQL.value,
            StorageType.DOCUMENT_SQLITE.value
        ]:
            if store_type in self.stores:
                return self.stores[store_type]
        
        return None
    
    def get_store(self, store_type: str):
        """获取指定类型的存储实例
        
        Args:
            store_type: 存储类型
            
        Returns:
            存储实例
        """
        return self.stores.get(store_type)
    
    def list_available_stores(self) -> List[str]:
        """列出所有可用的存储类型
        
        Returns:
            可用存储类型列表
        """
        return list(self.stores.keys())
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有存储的统计信息
        
        Returns:
            所有存储的统计信息
        """
        stats = {}
        
        for store_type, store in self.stores.items():
            try:
                if hasattr(store, 'get_collection_stats'):
                    stats[store_type] = store.get_collection_stats()
                elif hasattr(store, 'get_graph_stats'):
                    stats[store_type] = store.get_graph_stats()
                elif hasattr(store, 'get_database_stats'):
                    stats[store_type] = store.get_database_stats()
                else:
                    stats[store_type] = {"status": "available"}
            except Exception as e:
                stats[store_type] = {"error": str(e)}
        
        return stats
    
    def health_check(self) -> Dict[str, bool]:
        """检查所有存储的健康状态
        
        Returns:
            各存储的健康状态
        """
        health_status = {}
        
        for store_type, store in self.stores.items():
            try:
                # 尝试获取统计信息来检查健康状态
                if hasattr(store, 'get_collection_stats'):
                    store.get_collection_stats()
                elif hasattr(store, 'get_graph_stats'):
                    store.get_graph_stats()
                elif hasattr(store, 'get_database_stats'):
                    store.get_database_stats()
                
                health_status[store_type] = True
            except Exception as e:
                self.logger.error(f"存储健康检查失败 {store_type}: {e}")
                health_status[store_type] = False
        
        return health_status
    
    def close_all(self):
        """关闭所有存储连接"""
        for store_type, store in self.stores.items():
            try:
                if hasattr(store, 'close'):
                    store.close()
                self.logger.info(f"✅ 关闭存储连接: {store_type}")
            except Exception as e:
                self.logger.error(f"❌ 关闭存储连接失败 {store_type}: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close_all()

# 默认配置示例
DEFAULT_STORAGE_CONFIG = {
    "vector_chroma": {
        "enabled": True,
        "params": {
            "persist_directory": "./data/chroma_db",
            "collection_name": "hello_agents_vectors"
        }
    },
    "vector_faiss": {
        "enabled": False,
        "params": {
            "dimension": 768,
            "index_type": "Flat",
            "persist_path": "./data/faiss_db"
        }
    },
    "graph_networkx": {
        "enabled": True,
        "params": {
            "persist_path": "./data/networkx_graph.pkl"
        }
    },
    "document_sqlite": {
        "enabled": True,
        "params": {
            "db_path": "./data/memory.db"
        }
    }
}

def create_storage_manager(config: Dict[str, Any] = None) -> UnifiedStorageManager:
    """创建存储管理器的便捷函数
    
    Args:
        config: 存储配置，如果为None则使用默认配置
        
    Returns:
        存储管理器实例
    """
    if config is None:
        config = DEFAULT_STORAGE_CONFIG
    
    return UnifiedStorageManager(config)
