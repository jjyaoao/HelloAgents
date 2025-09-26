"""HelloAgents记忆系统模块

按照第8章架构设计的分层记忆系统：
- Memory Core Layer: 记忆核心层
- Memory Types Layer: 记忆类型层
- Storage Layer: 存储层
- Integration Layer: 集成层
"""

# Memory Core Layer (记忆核心层)
from .core.manager import MemoryManager
from .core.store import MemoryStore
from .core.retriever import MemoryRetriever

# Memory Types Layer (记忆类型层)
from .types.working import WorkingMemory
from .types.episodic import EpisodicMemory
from .types.semantic import SemanticMemory
from .types.perceptual import PerceptualMemory

# Storage Layer (存储层)
from .storage.vector_store import VectorStore, ChromaVectorStore, FAISSVectorStore
from .storage.graph_store import GraphStore, NetworkXGraphStore
from .storage.document_store import DocumentStore, SQLiteDocumentStore
from .storage.storage_manager import UnifiedStorageManager, create_storage_manager

# Base classes and utilities
from .base import MemoryItem, MemoryConfig, BaseMemory

__all__ = [
    # Core Layer
    "MemoryManager",
    "MemoryStore",
    "MemoryRetriever",

    # Memory Types
    "WorkingMemory",
    "EpisodicMemory",
    "SemanticMemory",
    "PerceptualMemory",

    # Storage Layer
    "VectorStore",
    "ChromaVectorStore",
    "FAISSVectorStore",
    "GraphStore",
    "NetworkXGraphStore",
    "DocumentStore",
    "SQLiteDocumentStore",
    "UnifiedStorageManager",
    "create_storage_manager",

    # Base
    "MemoryItem",
    "MemoryConfig",
    "BaseMemory"
]
