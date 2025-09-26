"""感知记忆实现

按照第8章架构设计的感知记忆，提供：
- 多模态数据存储
- 跨模态检索
- 感知理解和编码
- 内容生成支持
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import hashlib

from ..base import BaseMemory, MemoryItem, MemoryConfig

class Perception:
    """感知数据实体"""
    
    def __init__(
        self,
        perception_id: str,
        data: Any,
        modality: str,
        encoding: Optional[List[float]] = None,
        metadata: Dict[str, Any] = None
    ):
        self.perception_id = perception_id
        self.data = data
        self.modality = modality  # text, image, audio, video, structured
        self.encoding = encoding or []
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.data_hash = self._calculate_hash()
    
    def _calculate_hash(self) -> str:
        """计算数据哈希"""
        if isinstance(self.data, str):
            return hashlib.md5(self.data.encode()).hexdigest()
        elif isinstance(self.data, bytes):
            return hashlib.md5(self.data).hexdigest()
        else:
            return hashlib.md5(str(self.data).encode()).hexdigest()

class PerceptualMemory(BaseMemory):
    """感知记忆实现
    
    特点：
    - 支持多模态数据（文本、图像、音频等）
    - 跨模态相似性搜索
    - 感知数据的语义理解
    - 支持内容生成和检索
    """
    
    def __init__(self, config: MemoryConfig, storage_backend=None):
        super().__init__(config, storage_backend)
        
        # 感知数据存储
        self.perceptions: Dict[str, Perception] = {}
        self.perceptual_memories: List[MemoryItem] = []
        
        # 模态索引
        self.modality_index: Dict[str, List[str]] = {}  # modality -> perception_ids
        
        # 支持的模态
        self.supported_modalities = set(self.config.perceptual_memory_modalities)
        
        # 编码器（简化实现，实际应用中需要真实的多模态编码器）
        self.encoders = self._init_encoders()
    
    def add(self, memory_item: MemoryItem) -> str:
        """添加感知记忆"""
        # 从元数据中提取感知信息
        modality = memory_item.metadata.get("modality", "text")
        raw_data = memory_item.metadata.get("raw_data", memory_item.content)
        
        if modality not in self.supported_modalities:
            raise ValueError(f"不支持的模态类型: {modality}")
        
        # 编码感知数据
        perception = self._encode_perception(raw_data, modality, memory_item.id)
        
        # 存储感知数据
        self.perceptions[perception.perception_id] = perception
        
        # 更新模态索引
        if modality not in self.modality_index:
            self.modality_index[modality] = []
        self.modality_index[modality].append(perception.perception_id)
        
        # 存储记忆项
        memory_item.metadata["perception_id"] = perception.perception_id
        memory_item.metadata["modality"] = modality
        memory_item.metadata["encoding"] = perception.encoding
        self.perceptual_memories.append(memory_item)
        
        return memory_item.id
    
    def retrieve(self, query: str, limit: int = 5, **kwargs) -> List[MemoryItem]:
        """检索感知记忆"""
        query_modality = kwargs.get("query_modality", "text")
        target_modality = kwargs.get("target_modality")
        
        # 编码查询
        query_encoding = self._encode_data(query, query_modality)
        
        # 计算相似度
        scored_memories = []
        
        for memory in self.perceptual_memories:
            memory_modality = memory.metadata.get("modality", "text")
            
            # 模态过滤
            if target_modality and memory_modality != target_modality:
                continue
            
            # 计算相似度
            memory_encoding = memory.metadata.get("encoding", [])
            similarity = self._calculate_similarity(query_encoding, memory_encoding)
            
            if similarity > 0.1:  # 最小相似度阈值
                scored_memories.append((similarity * memory.importance, memory))
        
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
        """更新感知记忆"""
        for memory in self.perceptual_memories:
            if memory.id == memory_id:
                if content is not None:
                    memory.content = content
                    
                    # 重新编码
                    modality = memory.metadata.get("modality", "text")
                    raw_data = metadata.get("raw_data", content) if metadata else content
                    
                    perception = self._encode_perception(raw_data, modality, memory_id)
                    self.perceptions[perception.perception_id] = perception
                    memory.metadata["encoding"] = perception.encoding
                
                if importance is not None:
                    memory.importance = importance
                
                if metadata is not None:
                    memory.metadata.update(metadata)
                
                return True
        return False
    
    def remove(self, memory_id: str) -> bool:
        """删除感知记忆"""
        for i, memory in enumerate(self.perceptual_memories):
            if memory.id == memory_id:
                removed_memory = self.perceptual_memories.pop(i)
                
                # 删除感知数据
                perception_id = removed_memory.metadata.get("perception_id")
                if perception_id and perception_id in self.perceptions:
                    perception = self.perceptions.pop(perception_id)
                    
                    # 从模态索引中删除
                    modality = perception.modality
                    if modality in self.modality_index:
                        self.modality_index[modality].remove(perception_id)
                        if not self.modality_index[modality]:
                            del self.modality_index[modality]
                
                return True
        return False
    
    def has_memory(self, memory_id: str) -> bool:
        """检查记忆是否存在"""
        return any(memory.id == memory_id for memory in self.perceptual_memories)
    
    def clear(self):
        """清空所有感知记忆"""
        self.perceptual_memories.clear()
        self.perceptions.clear()
        self.modality_index.clear()

    def get_all(self) -> List[MemoryItem]:
        """获取所有感知记忆"""
        return self.perceptual_memories.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取感知记忆统计信息"""
        modality_counts = {modality: len(ids) for modality, ids in self.modality_index.items()}
        
        return {
            "count": len(self.perceptual_memories),
            "perceptions_count": len(self.perceptions),
            "modality_counts": modality_counts,
            "supported_modalities": list(self.supported_modalities),
            "avg_importance": sum(m.importance for m in self.perceptual_memories) / len(self.perceptual_memories) if self.perceptual_memories else 0.0,
            "memory_type": "perceptual"
        }
    
    def cross_modal_search(
        self,
        query: Any,
        query_modality: str,
        target_modality: str = None,
        limit: int = 5
    ) -> List[MemoryItem]:
        """跨模态搜索"""
        return self.retrieve(
            query=str(query),
            limit=limit,
            query_modality=query_modality,
            target_modality=target_modality
        )
    
    def get_by_modality(self, modality: str, limit: int = 10) -> List[MemoryItem]:
        """按模态获取记忆"""
        if modality not in self.modality_index:
            return []
        
        perception_ids = self.modality_index[modality]
        results = []
        
        for memory in self.perceptual_memories:
            if memory.metadata.get("perception_id") in perception_ids:
                results.append(memory)
                if len(results) >= limit:
                    break
        
        return results
    
    def generate_content(self, prompt: str, target_modality: str) -> Optional[str]:
        """基于感知记忆生成内容"""
        # 简化的内容生成实现
        # 实际应用中需要使用生成模型
        
        if target_modality not in self.supported_modalities:
            return None
        
        # 检索相关感知记忆
        relevant_memories = self.retrieve(prompt, limit=3)
        
        if not relevant_memories:
            return None
        
        # 简单的内容组合
        if target_modality == "text":
            contents = [memory.content for memory in relevant_memories]
            return f"基于感知记忆生成的内容：\n" + "\n".join(contents)
        
        return f"生成的{target_modality}内容（基于{len(relevant_memories)}个相关记忆）"
    
    def _init_encoders(self) -> Dict[str, Any]:
        """初始化编码器"""
        # 简化实现，实际应用中需要真实的多模态编码器
        encoders = {}
        
        for modality in self.supported_modalities:
            if modality == "text":
                encoders[modality] = self._text_encoder
            elif modality == "image":
                encoders[modality] = self._image_encoder
            else:
                encoders[modality] = self._default_encoder
        
        return encoders
    
    def _encode_perception(self, data: Any, modality: str, memory_id: str) -> Perception:
        """编码感知数据"""
        encoding = self._encode_data(data, modality)
        
        perception = Perception(
            perception_id=f"perception_{memory_id}",
            data=data,
            modality=modality,
            encoding=encoding,
            metadata={"source": "memory_system"}
        )
        
        return perception
    
    def _encode_data(self, data: Any, modality: str) -> List[float]:
        """编码数据"""
        encoder = self.encoders.get(modality, self._default_encoder)
        return encoder(data)
    
    def _text_encoder(self, text: str) -> List[float]:
        """文本编码器（简化实现）"""
        # 简单的TF-IDF风格编码
        words = text.lower().split()
        word_freq = {}
        
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 生成固定长度的向量
        vector = [0.0] * 128
        for i, word in enumerate(list(word_freq.keys())[:128]):
            vector[i] = word_freq[word] / len(words)
        
        return vector
    
    def _image_encoder(self, image_data: Any) -> List[float]:
        """图像编码器（简化实现）"""
        # 简化实现：基于数据哈希生成向量
        if isinstance(image_data, str):
            # 假设是base64编码的图像
            hash_value = hashlib.md5(image_data.encode()).hexdigest()
        else:
            hash_value = hashlib.md5(str(image_data).encode()).hexdigest()
        
        # 将哈希转换为向量
        vector = []
        for i in range(0, len(hash_value), 2):
            vector.append(int(hash_value[i:i+2], 16) / 255.0)
        
        # 填充到固定长度
        while len(vector) < 128:
            vector.append(0.0)
        
        return vector[:128]
    
    def _default_encoder(self, data: Any) -> List[float]:
        """默认编码器"""
        # 基于数据字符串表示的简单编码
        data_str = str(data)
        return self._text_encoder(data_str)
    
    def _calculate_similarity(self, encoding1: List[float], encoding2: List[float]) -> float:
        """计算编码相似度"""
        if not encoding1 or not encoding2:
            return 0.0
        
        # 确保长度一致
        min_len = min(len(encoding1), len(encoding2))
        if min_len == 0:
            return 0.0
        
        # 计算余弦相似度
        dot_product = sum(a * b for a, b in zip(encoding1[:min_len], encoding2[:min_len]))
        norm1 = sum(a * a for a in encoding1[:min_len]) ** 0.5
        norm2 = sum(a * a for a in encoding2[:min_len]) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
