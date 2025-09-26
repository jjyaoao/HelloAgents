"""图存储实现

支持多种图数据库后端：
- NetworkX: Python图分析库，适合中小规模图数据
- Neo4j: 企业级图数据库（可扩展）
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
import pickle
from datetime import datetime

class GraphStore(ABC):
    """图存储基类"""
    
    @abstractmethod
    def add_concept(self, concept_id: str, name: str, properties: Dict[str, Any] = None) -> str:
        """添加概念节点"""
        pass
    
    @abstractmethod
    def add_relationship(
        self,
        from_concept_id: str,
        to_concept_id: str,
        relationship_type: str,
        properties: Dict[str, Any] = None
    ) -> bool:
        """添加概念间的关系"""
        pass
    
    @abstractmethod
    def add_memory_with_concepts(
        self,
        memory_id: str,
        user_id: str,
        content: str,
        memory_type: str,
        concepts: List[str],
        timestamp: int,
        importance: float = 0.5
    ) -> str:
        """添加记忆节点并关联概念"""
        pass
    
    @abstractmethod
    def find_related_concepts(
        self,
        concept_id: str,
        relationship_types: List[str] = None,
        max_depth: int = 2,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """查找相关概念"""
        pass
    
    @abstractmethod
    def find_memories_by_concepts(
        self,
        concept_ids: List[str],
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """根据概念查找相关记忆"""
        pass
    
    @abstractmethod
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆节点及其关系"""
        pass
    
    @abstractmethod
    def get_graph_stats(self) -> Dict[str, Any]:
        """获取图统计信息"""
        pass

class NetworkXGraphStore(GraphStore):
    """NetworkX内存图存储实现"""
    
    def __init__(self, persist_path: str = "./networkx_graph.pkl"):
        self.persist_path = persist_path
        
        # 创建有向图
        import networkx as nx
        self.graph = nx.DiGraph()
        
        # 加载现有图数据
        self._load_graph()
        
        print(f"✅ NetworkX图存储初始化完成: {self.graph.number_of_nodes()} 节点, {self.graph.number_of_edges()} 边")
    
    def _load_graph(self):
        """加载现有图数据"""
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, 'rb') as f:
                    self.graph = pickle.load(f)
                print(f"✅ 加载现有NetworkX图: {self.graph.number_of_nodes()} 节点")
            except Exception as e:
                print(f"⚠️ 加载图数据失败: {e}")
                import networkx as nx
                self.graph = nx.DiGraph()
    
    def _save_graph(self):
        """保存图数据"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            
            with open(self.persist_path, 'wb') as f:
                pickle.dump(self.graph, f)
        except Exception as e:
            print(f"⚠️ 保存图数据失败: {e}")
    
    def add_concept(self, concept_id: str, name: str, properties: Dict[str, Any] = None) -> str:
        """添加概念节点"""
        properties = properties or {}
        
        # 添加节点属性
        node_attrs = {
            "name": name,
            "type": "concept",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            **properties
        }
        
        self.graph.add_node(concept_id, **node_attrs)
        self._save_graph()
        
        return concept_id
    
    def add_relationship(
        self,
        from_concept_id: str,
        to_concept_id: str,
        relationship_type: str,
        properties: Dict[str, Any] = None
    ) -> bool:
        """添加概念间的关系"""
        properties = properties or {}
        
        # 确保节点存在
        if not self.graph.has_node(from_concept_id) or not self.graph.has_node(to_concept_id):
            return False
        
        # 添加边属性
        edge_attrs = {
            "relationship_type": relationship_type,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            **properties
        }
        
        self.graph.add_edge(from_concept_id, to_concept_id, **edge_attrs)
        self._save_graph()
        
        return True
    
    def add_memory_with_concepts(
        self,
        memory_id: str,
        user_id: str,
        content: str,
        memory_type: str,
        concepts: List[str],
        timestamp: int,
        importance: float = 0.5
    ) -> str:
        """添加记忆节点并关联概念"""
        # 添加用户节点（如果不存在）
        if not self.graph.has_node(user_id):
            self.graph.add_node(user_id, type="user", name=user_id)
        
        # 添加记忆节点
        memory_attrs = {
            "type": "memory",
            "content": content,
            "memory_type": memory_type,
            "timestamp": timestamp,
            "importance": importance,
            "created_at": datetime.now().isoformat()
        }
        
        self.graph.add_node(memory_id, **memory_attrs)
        
        # 连接用户和记忆
        self.graph.add_edge(user_id, memory_id, relationship_type="HAS_MEMORY")
        
        # 连接记忆和概念
        for concept_id in concepts:
            # 确保概念节点存在
            if not self.graph.has_node(concept_id):
                self.add_concept(concept_id, concept_id)
            
            self.graph.add_edge(memory_id, concept_id, relationship_type="RELATES_TO")
        
        self._save_graph()
        return memory_id
    
    def find_related_concepts(
        self,
        concept_id: str,
        relationship_types: List[str] = None,
        max_depth: int = 2,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """查找相关概念"""
        if not self.graph.has_node(concept_id):
            return []
        
        related_concepts = []
        visited = set()
        
        # 使用BFS查找相关概念
        queue = [(concept_id, 0, [])]  # (节点ID, 深度, 路径)
        
        while queue and len(related_concepts) < limit:
            current_id, depth, path = queue.pop(0)
            
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            
            # 获取邻居节点
            neighbors = list(self.graph.neighbors(current_id)) + list(self.graph.predecessors(current_id))
            
            for neighbor_id in neighbors:
                if neighbor_id == concept_id or neighbor_id in visited:
                    continue
                
                # 检查节点类型
                neighbor_attrs = self.graph.nodes[neighbor_id]
                if neighbor_attrs.get("type") != "concept":
                    continue
                
                # 检查关系类型过滤
                edge_data = self.graph.get_edge_data(current_id, neighbor_id) or \
                           self.graph.get_edge_data(neighbor_id, current_id)
                
                if relationship_types and edge_data:
                    if edge_data.get("relationship_type") not in relationship_types:
                        continue
                
                # 添加到结果 - 包括直接邻居（depth >= 0，但排除起始节点本身）
                if neighbor_id != concept_id:  # 排除起始节点
                    related_concepts.append({
                        "id": neighbor_id,
                        "name": neighbor_attrs.get("name", neighbor_id),
                        "distance": depth + 1,  # 邻居的距离是当前深度+1
                        "relationship_path": path + [edge_data.get("relationship_type", "UNKNOWN") if edge_data else "UNKNOWN"]
                    })
                
                # 添加到队列继续搜索
                if depth < max_depth:
                    queue.append((neighbor_id, depth + 1, path + [edge_data.get("relationship_type", "UNKNOWN") if edge_data else "UNKNOWN"]))
        
        return related_concepts[:limit]
    
    def find_memories_by_concepts(
        self,
        concept_ids: List[str],
        user_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """根据概念查找相关记忆"""
        memories = []
        memory_scores = {}  # memory_id -> score
        
        # 遍历所有概念
        for concept_id in concept_ids:
            if not self.graph.has_node(concept_id):
                continue
            
            # 查找连接到此概念的记忆
            predecessors = list(self.graph.predecessors(concept_id))
            
            for pred_id in predecessors:
                pred_attrs = self.graph.nodes[pred_id]
                
                # 检查是否为记忆节点
                if pred_attrs.get("type") != "memory":
                    continue
                
                # 应用过滤条件
                if memory_type and pred_attrs.get("memory_type") != memory_type:
                    continue
                
                if user_id:
                    # 检查记忆是否属于指定用户
                    user_predecessors = list(self.graph.predecessors(pred_id))
                    if user_id not in user_predecessors:
                        continue
                
                # 计算匹配分数
                memory_scores[pred_id] = memory_scores.get(pred_id, 0) + 1
        
        # 按分数排序并构建结果
        sorted_memories = sorted(memory_scores.items(), key=lambda x: x[1], reverse=True)
        
        for memory_id, concept_matches in sorted_memories[:limit]:
            memory_attrs = self.graph.nodes[memory_id]
            
            # 获取用户ID
            memory_user_id = None
            for pred_id in self.graph.predecessors(memory_id):
                if self.graph.nodes[pred_id].get("type") == "user":
                    memory_user_id = pred_id
                    break
            
            memories.append({
                "memory_id": memory_id,
                "content": memory_attrs.get("content", ""),
                "memory_type": memory_attrs.get("memory_type", ""),
                "timestamp": memory_attrs.get("timestamp", 0),
                "importance": memory_attrs.get("importance", 0.5),
                "user_id": memory_user_id,
                "concept_matches": concept_matches
            })
        
        return memories
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆节点及其关系"""
        if not self.graph.has_node(memory_id):
            return False
        
        self.graph.remove_node(memory_id)
        self._save_graph()
        
        return True
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """获取图统计信息"""
        node_types = {}
        edge_types = {}
        
        # 统计节点类型
        for node_id, attrs in self.graph.nodes(data=True):
            node_type = attrs.get("type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        # 统计边类型
        for _, _, attrs in self.graph.edges(data=True):
            edge_type = attrs.get("relationship_type", "unknown")
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "node_types": node_types,
            "edge_types": edge_types,
            "is_directed": self.graph.is_directed(),
            "persist_path": self.persist_path,
            "store_type": "networkx"
        }
