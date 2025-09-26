"""嵌入模型实现"""

from abc import ABC, abstractmethod
from typing import List, Union
import numpy as np

class EmbeddingModel(ABC):
    """嵌入模型基类"""
    
    @abstractmethod
    def encode(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """编码文本为向量"""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """向量维度"""
        pass

class SentenceTransformerEmbedding(EmbeddingModel):
    """基于SentenceTransformers的嵌入模型"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension = None
        self._load_model()
    
    def _load_model(self):
        """加载模型"""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            # 获取模型维度
            test_embedding = self._model.encode("test")
            self._dimension = len(test_embedding)
        except ImportError:
            raise ImportError("请安装 sentence-transformers: pip install sentence-transformers")
    
    def encode(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        编码文本为向量
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            向量或向量列表
        """
        if isinstance(texts, str):
            return self._model.encode(texts)
        else:
            return self._model.encode(texts)
    
    @property
    def dimension(self) -> int:
        """向量维度"""
        return self._dimension

class OpenAIEmbedding(EmbeddingModel):
    """基于OpenAI API的嵌入模型"""
    
    def __init__(self, model_name: str = "text-embedding-ada-002", api_key: str = None):
        self.model_name = model_name
        self.api_key = api_key
        self._dimension = 1536  # ada-002的维度
        self._client = None
        self._init_client()
    
    def _init_client(self):
        """初始化OpenAI客户端"""
        try:
            import openai
            if self.api_key:
                openai.api_key = self.api_key
            self._client = openai
        except ImportError:
            raise ImportError("请安装 openai: pip install openai")
    
    def encode(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        编码文本为向量
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            向量或向量列表
        """
        if isinstance(texts, str):
            texts = [texts]
            single_text = True
        else:
            single_text = False
        
        # 调用OpenAI API
        response = self._client.Embedding.create(
            model=self.model_name,
            input=texts
        )
        
        embeddings = [np.array(item['embedding']) for item in response['data']]
        
        if single_text:
            return embeddings[0]
        else:
            return embeddings
    
    @property
    def dimension(self) -> int:
        """向量维度"""
        return self._dimension

class TFIDFEmbedding(EmbeddingModel):
    """基于TF-IDF的简单嵌入模型"""
    
    def __init__(self, max_features: int = 1000):
        self.max_features = max_features
        self._vectorizer = None
        self._is_fitted = False
        self._dimension = max_features
        self._init_vectorizer()
    
    def _init_vectorizer(self):
        """初始化TF-IDF向量化器"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self._vectorizer = TfidfVectorizer(
                max_features=self.max_features,
                stop_words='english'
            )
        except ImportError:
            raise ImportError("请安装 scikit-learn: pip install scikit-learn")
    
    def fit(self, texts: List[str]):
        """训练TF-IDF模型"""
        self._vectorizer.fit(texts)
        self._is_fitted = True
        # 更新实际维度
        self._dimension = len(self._vectorizer.get_feature_names_out())
    
    def encode(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        编码文本为向量
        
        Args:
            texts: 单个文本或文本列表
            
        Returns:
            向量或向量列表
        """
        if not self._is_fitted:
            raise ValueError("TF-IDF模型未训练，请先调用fit()方法")
        
        if isinstance(texts, str):
            texts = [texts]
            single_text = True
        else:
            single_text = False
        
        # 转换为TF-IDF向量
        tfidf_matrix = self._vectorizer.transform(texts)
        embeddings = tfidf_matrix.toarray()
        
        if single_text:
            return embeddings[0]
        else:
            return [embedding for embedding in embeddings]
    
    @property
    def dimension(self) -> int:
        """向量维度"""
        return self._dimension

class HuggingFaceEmbedding(EmbeddingModel):
    """基于Hugging Face transformers的轻量级嵌入模型"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._tokenizer = None
        self._dimension = None
        self._load_model()

    def _load_model(self):
        """加载模型"""
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name)

            # 获取模型维度
            with torch.no_grad():
                test_inputs = self._tokenizer("test", return_tensors="pt", padding=True, truncation=True)
                test_outputs = self._model(**test_inputs)
                # 使用mean pooling
                test_embedding = test_outputs.last_hidden_state.mean(dim=1)
                self._dimension = test_embedding.shape[1]

        except ImportError:
            raise ImportError("请安装 transformers: pip install transformers torch")

    def encode(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        编码文本为向量

        Args:
            texts: 单个文本或文本列表

        Returns:
            向量或向量列表
        """
        import torch

        if isinstance(texts, str):
            texts = [texts]
            single_text = True
        else:
            single_text = False

        # 分词和编码
        inputs = self._tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=512)

        with torch.no_grad():
            outputs = self._model(**inputs)
            # 使用mean pooling获取句子嵌入
            embeddings = outputs.last_hidden_state.mean(dim=1)
            embeddings = embeddings.cpu().numpy()

        if single_text:
            return embeddings[0]
        else:
            return [embedding for embedding in embeddings]

    @property
    def dimension(self) -> int:
        """向量维度"""
        return self._dimension

def create_embedding_model(model_type: str = "sentence_transformer", **kwargs) -> EmbeddingModel:
    """
    创建嵌入模型的工厂函数

    Args:
        model_type: 模型类型 ("sentence_transformer", "huggingface", "openai", "tfidf")
        **kwargs: 模型参数

    Returns:
        嵌入模型实例
    """
    if model_type == "sentence_transformer":
        try:
            return SentenceTransformerEmbedding(**kwargs)
        except ImportError:
            print("⚠️ sentence-transformers未安装，自动切换到huggingface模式")
            return HuggingFaceEmbedding(**kwargs)
    elif model_type == "huggingface":
        return HuggingFaceEmbedding(**kwargs)
    elif model_type == "openai":
        return OpenAIEmbedding(**kwargs)
    elif model_type == "tfidf":
        return TFIDFEmbedding(**kwargs)
    else:
        raise ValueError(f"不支持的模型类型: {model_type}")

def create_embedding_model_with_fallback(preferred_type: str = "sentence_transformer", **kwargs) -> EmbeddingModel:
    """
    创建嵌入模型，支持自动降级

    Args:
        preferred_type: 首选模型类型
        **kwargs: 模型参数

    Returns:
        嵌入模型实例
    """
    fallback_order = [
        "sentence_transformer",
        "huggingface",
        "tfidf"
    ]

    # 将首选类型放在第一位
    if preferred_type in fallback_order:
        fallback_order.remove(preferred_type)
        fallback_order.insert(0, preferred_type)

    for model_type in fallback_order:
        try:
            model = create_embedding_model(model_type, **kwargs)
            if model_type != preferred_type:
                print(f"⚠️ 自动降级到 {model_type} 嵌入模型")
            return model
        except ImportError as e:
            print(f"⚠️ {model_type} 不可用: {e}")
            continue

    raise RuntimeError("所有嵌入模型都不可用，请安装相关依赖")
