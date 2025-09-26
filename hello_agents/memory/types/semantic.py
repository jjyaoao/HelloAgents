"""语义记忆实现

按照第8章架构设计的语义记忆，提供：
- 抽象知识和概念存储
- 知识图谱构建
- 语义搜索和推理
- 概念关系管理
"""

from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import re


from ..base import BaseMemory, MemoryItem, MemoryConfig

class Concept:
    """概念实体"""
    
    def __init__(
        self,
        concept_id: str,
        name: str,
        description: str = "",
        concept_type: str = "general",
        properties: Dict[str, Any] = None
    ):
        self.concept_id = concept_id
        self.name = name
        self.description = description
        self.concept_type = concept_type
        self.properties = properties or {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

class ConceptRelation:
    """概念关系"""
    
    def __init__(
        self,
        from_concept: str,
        to_concept: str,
        relation_type: str,
        strength: float = 1.0,
        properties: Dict[str, Any] = None
    ):
        self.from_concept = from_concept
        self.to_concept = to_concept
        self.relation_type = relation_type
        self.strength = strength
        self.properties = properties or {}
        self.created_at = datetime.now()

class SemanticMemory(BaseMemory):
    """语义记忆实现
    
    特点：
    - 存储抽象的知识和概念
    - 构建知识图谱
    - 支持语义搜索和推理
    - 跨场景适用的通用知识
    """
    
    def __init__(self, config: MemoryConfig, storage_backend=None):
        super().__init__(config, storage_backend)
        
        # 概念存储
        self.concepts: Dict[str, Concept] = {}
        self.relations: List[ConceptRelation] = []
        
        # 知识图谱索引
        self.concept_index: Dict[str, Set[str]] = {}  # concept_name -> concept_ids
        self.relation_index: Dict[str, List[ConceptRelation]] = {}  # from_concept -> relations
        
        # 语义记忆项
        self.semantic_memories: List[MemoryItem] = []
    
    def add(self, memory_item: MemoryItem) -> str:
        """添加语义记忆"""
        # 提取概念
        concepts = self._extract_concepts(memory_item.content)
        
        # 添加概念到知识图谱
        for concept in concepts:
            self._add_concept(concept)
        
        # 建立概念关系
        self._build_concept_relations(concepts, memory_item.content)
        
        # 存储语义记忆
        memory_item.metadata["extracted_concepts"] = [c.concept_id for c in concepts]
        self.semantic_memories.append(memory_item)
        
        # 持久化
        if self.storage:
            self._persist_semantic_memory(memory_item, concepts)
        
        return memory_item.id
    
    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """检索语义记忆"""
        user_id = kwargs.get("user_id")

        # 按用户ID过滤（如果提供）
        filtered_memories = self.semantic_memories
        if user_id:
            filtered_memories = [m for m in self.semantic_memories if m.user_id == user_id]

        if not filtered_memories:
            return []

        # 提取查询概念
        query_concepts = self._extract_concepts(query)

        # 语义搜索
        scored_memories = []

        for memory in filtered_memories:
            score = self._calculate_semantic_similarity(query, memory, query_concepts)
            if score > self.config.semantic_memory_concept_threshold:
                scored_memories.append((score, memory))

        # 排序并返回
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [memory for _, memory in scored_memories[:limit]]
    
    def update(
        self,
        memory_id: str,
        content: str = None,
        importance: float = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """更新语义记忆"""
        for memory in self.semantic_memories:
            if memory.id == memory_id:
                if content is not None:
                    # 重新提取概念
                    old_concepts = memory.metadata.get("extracted_concepts", [])
                    memory.content = content
                    
                    new_concepts = self._extract_concepts(content)
                    self._update_concept_relations(old_concepts, new_concepts, content)
                    memory.metadata["extracted_concepts"] = [c.concept_id for c in new_concepts]
                
                if importance is not None:
                    memory.importance = importance
                
                if metadata is not None:
                    memory.metadata.update(metadata)
                
                return True
        return False
    
    def remove(self, memory_id: str) -> bool:
        """删除语义记忆"""
        for i, memory in enumerate(self.semantic_memories):
            if memory.id == memory_id:
                removed_memory = self.semantic_memories.pop(i)
                
                # 清理相关概念关系
                concepts = removed_memory.metadata.get("extracted_concepts", [])
                self._cleanup_concept_relations(concepts)
                
                return True
        return False
    
    def has_memory(self, memory_id: str) -> bool:
        """检查记忆是否存在"""
        return any(memory.id == memory_id for memory in self.semantic_memories)
    
    def clear(self):
        """清空所有语义记忆"""
        self.semantic_memories.clear()
        self.concepts.clear()
        self.relations.clear()
        self.concept_index.clear()
        self.relation_index.clear()

    def get_all(self) -> List[MemoryItem]:
        """获取所有语义记忆"""
        return self.semantic_memories.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取语义记忆统计信息"""
        return {
            "count": len(self.semantic_memories),
            "concepts_count": len(self.concepts),
            "relations_count": len(self.relations),
            "avg_importance": sum(m.importance for m in self.semantic_memories) / len(self.semantic_memories) if self.semantic_memories else 0.0,
            "memory_type": "semantic"
        }
    
    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """获取概念"""
        return self.concepts.get(concept_id)
    
    def search_concepts(self, query: str, limit: int = 10) -> List[Concept]:
        """搜索概念"""
        query_lower = query.lower()
        scored_concepts = []
        
        for concept in self.concepts.values():
            score = 0.0
            
            # 名称匹配
            if query_lower in concept.name.lower():
                score += 1.0
            
            # 描述匹配
            if query_lower in concept.description.lower():
                score += 0.5
            
            # 属性匹配
            for key, value in concept.properties.items():
                if query_lower in str(value).lower():
                    score += 0.3
            
            if score > 0:
                scored_concepts.append((score, concept))
        
        scored_concepts.sort(key=lambda x: x[0], reverse=True)
        return [concept for _, concept in scored_concepts[:limit]]
    
    def get_related_concepts(
        self,
        concept_id: str,
        relation_types: List[str] = None,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """获取相关概念"""
        if concept_id not in self.concepts:
            return []
        
        related = []
        visited = set()
        queue = [(concept_id, 0)]
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if current_id in visited or depth > max_depth:
                continue
            
            visited.add(current_id)
            
            # 查找直接关系
            if current_id in self.relation_index:
                for relation in self.relation_index[current_id]:
                    if relation_types and relation.relation_type not in relation_types:
                        continue
                    
                    target_concept = self.concepts.get(relation.to_concept)
                    if target_concept and relation.to_concept not in visited:
                        related.append({
                            "concept": target_concept,
                            "relation_type": relation.relation_type,
                            "strength": relation.strength,
                            "depth": depth + 1
                        })
                        
                        if depth + 1 < max_depth:
                            queue.append((relation.to_concept, depth + 1))
        
        return related
    
    def reason(self, query: str) -> List[Dict[str, Any]]:
        """基于知识图谱的推理"""
        # 简单的推理实现
        query_concepts = self._extract_concepts(query)
        
        inferences = []
        
        for concept in query_concepts:
            # 查找相关概念
            related = self.get_related_concepts(concept.concept_id, max_depth=2)
            
            for rel in related:
                if rel["strength"] > 0.7:  # 高置信度关系
                    inferences.append({
                        "type": "concept_relation",
                        "from_concept": concept.name,
                        "to_concept": rel["concept"].name,
                        "relation": rel["relation_type"],
                        "confidence": rel["strength"]
                    })
        
        return inferences
    
    def _extract_concepts(self, text: str) -> List[Concept]:
        """从文本中提取概念"""
        concepts = []
        
        # 简单的概念提取（实际应用中可以使用NLP工具）
        # 提取名词短语
        words = re.findall(r'\b[A-Za-z\u4e00-\u9fff]+\b', text)
        
        # 过滤和去重
        concept_names = set()
        for word in words:
            if len(word) > 2 and word.lower() not in ['the', 'and', 'or', 'but']:
                concept_names.add(word.lower())
        
        # 创建或获取概念
        for name in concept_names:
            concept_id = f"concept_{hash(name) % 10000}"
            
            if concept_id not in self.concepts:
                concept = Concept(
                    concept_id=concept_id,
                    name=name,
                    description=f"Concept extracted from: {text[:50]}...",
                    concept_type="extracted"
                )
                concepts.append(concept)
            else:
                concepts.append(self.concepts[concept_id])
        
        return concepts
    
    def _add_concept(self, concept: Concept):
        """添加概念到知识图谱"""
        self.concepts[concept.concept_id] = concept
        
        # 更新索引
        name_key = concept.name.lower()
        if name_key not in self.concept_index:
            self.concept_index[name_key] = set()
        self.concept_index[name_key].add(concept.concept_id)
    
    def _build_concept_relations(self, concepts: List[Concept], context: str):
        """建立概念关系"""
        # 简单的共现关系
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i+1:]:
                # 创建共现关系
                relation = ConceptRelation(
                    from_concept=concept1.concept_id,
                    to_concept=concept2.concept_id,
                    relation_type="co_occurs",
                    strength=0.5,
                    properties={"context": context[:100]}
                )
                
                self.relations.append(relation)
                
                # 更新关系索引
                if concept1.concept_id not in self.relation_index:
                    self.relation_index[concept1.concept_id] = []
                self.relation_index[concept1.concept_id].append(relation)
    
    def _calculate_semantic_similarity(
        self,
        query: str,
        memory: MemoryItem,
        query_concepts: List[Concept]
    ) -> float:
        """计算语义相似度"""
        memory_concepts = memory.metadata.get("extracted_concepts", [])
        
        if not query_concepts or not memory_concepts:
            return 0.0
        
        # 概念重叠度
        query_concept_ids = {c.concept_id for c in query_concepts}
        memory_concept_ids = set(memory_concepts)
        
        intersection = query_concept_ids.intersection(memory_concept_ids)
        union = query_concept_ids.union(memory_concept_ids)
        
        concept_similarity = len(intersection) / len(union) if union else 0.0
        
        # 结合重要性
        return concept_similarity * memory.importance
    
    def _update_concept_relations(self, old_concepts: List[str], new_concepts: List[Concept], content: str):
        """更新概念关系"""
        # 删除旧关系
        self._cleanup_concept_relations(old_concepts)
        
        # 建立新关系
        self._build_concept_relations(new_concepts, content)
    
    def _cleanup_concept_relations(self, concept_ids: List[str]):
        """清理概念关系"""
        # 删除相关关系
        self.relations = [
            r for r in self.relations
            if r.from_concept not in concept_ids and r.to_concept not in concept_ids
        ]
        
        # 重建关系索引
        self.relation_index.clear()
        for relation in self.relations:
            if relation.from_concept not in self.relation_index:
                self.relation_index[relation.from_concept] = []
            self.relation_index[relation.from_concept].append(relation)
    
    def _persist_semantic_memory(self, memory_item: MemoryItem, concepts: List[Concept]):
        """持久化语义记忆"""
        if self.storage:
            # 持久化概念
            if hasattr(self.storage, 'add_concept'):
                for concept in concepts:
                    self.storage.add_concept(concept.concept_id, concept.name, concept.properties)
            
            # 持久化记忆
            if hasattr(self.storage, 'add_memory_with_concepts'):
                concept_ids = [c.concept_id for c in concepts]
                self.storage.add_memory_with_concepts(
                    memory_item.id,
                    memory_item.user_id,
                    memory_item.content,
                    memory_item.memory_type,
                    concept_ids,
                    int(memory_item.timestamp.timestamp()),
                    memory_item.importance
                )
