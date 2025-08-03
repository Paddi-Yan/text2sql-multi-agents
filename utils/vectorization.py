"""
Vectorization utilities for training data.
"""

import hashlib
from typing import List, Dict, Any, Optional
import numpy as np

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False


class VectorizationService:
    """向量化服务"""
    
    def __init__(self, embedding_model: str = "text-embedding-ada-002", model_type: str = "openai"):
        self.embedding_model = embedding_model
        self.model_type = model_type
        self._model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """初始化嵌入模型"""
        if self.model_type == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI library not available. Install with: pip install openai")
            # OpenAI模型不需要预加载
            self._model = None
        elif self.model_type == "sentence_transformers":
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError("Sentence Transformers library not available. Install with: pip install sentence-transformers")
            self._model = SentenceTransformer(self.embedding_model)
        else:
            raise ValueError(f"Unsupported model type: {self.model_type}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """生成文本的向量嵌入"""
        try:
            if self.model_type == "openai":
                # Use new OpenAI API format (v1.0+)
                from openai import OpenAI
                client = OpenAI()
                response = client.embeddings.create(
                    input=text,
                    model=self.embedding_model
                )
                return response.data[0].embedding
            elif self.model_type == "sentence_transformers":
                embedding = self._model.encode(text)
                return embedding.tolist()
            else:
                raise ValueError(f"Unsupported model type: {self.model_type}")
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # 返回零向量作为fallback
            return [0.0] * 1536  # OpenAI ada-002的维度
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量生成向量嵌入"""
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # 计算余弦相似度
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            print(f"Error calculating similarity: {e}")
            return 0.0
    
    def find_most_similar(self, query_embedding: List[float], 
                         candidate_embeddings: List[List[float]], 
                         top_k: int = 5) -> List[int]:
        """找到最相似的向量索引"""
        similarities = []
        for i, candidate in enumerate(candidate_embeddings):
            similarity = self.calculate_similarity(query_embedding, candidate)
            similarities.append((i, similarity))
        
        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # 返回top-k的索引
        return [idx for idx, _ in similarities[:top_k]]


class MetadataManager:
    """元数据管理器"""
    
    @staticmethod
    def extract_table_names_from_ddl(ddl: str) -> List[str]:
        """从DDL语句中提取表名"""
        table_names = []
        lines = ddl.upper().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('CREATE TABLE'):
                # 提取表名
                parts = line.split()
                if len(parts) >= 3:
                    table_name = parts[2].strip('(').strip(';').strip('`').strip('"')
                    table_names.append(table_name.lower())
        
        return table_names
    
    @staticmethod
    def extract_table_names_from_sql(sql: str) -> List[str]:
        """从SQL语句中提取表名"""
        table_names = []
        sql_upper = sql.upper()
        
        # 简单的表名提取（可以后续优化为使用SQL解析器）
        keywords = ['FROM', 'JOIN', 'UPDATE', 'INSERT INTO', 'DELETE FROM']
        
        for keyword in keywords:
            if keyword in sql_upper:
                parts = sql_upper.split(keyword)
                for part in parts[1:]:  # 跳过第一部分
                    # 提取第一个单词作为表名
                    words = part.strip().split()
                    if words:
                        table_name = words[0].strip('(').strip(')').strip(',').strip(';')
                        if table_name and not table_name in ['SELECT', 'WHERE', 'GROUP', 'ORDER', 'HAVING']:
                            table_names.append(table_name.lower())
        
        return list(set(table_names))  # 去重
    
    @staticmethod
    def generate_content_hash(content: str) -> str:
        """生成内容哈希"""
        return hashlib.md5(content.encode()).hexdigest()
    
    @staticmethod
    def create_metadata(data_type: str, source: str = "manual", 
                       additional_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建元数据"""
        metadata = {
            "source": source,
            "data_type": data_type,
            "created_at": str(np.datetime64('now')),
            "version": "1.0"
        }
        
        if additional_info:
            metadata.update(additional_info)
        
        return metadata
    
    @staticmethod
    def extract_tags_from_content(content: str, data_type: str) -> List[str]:
        """从内容中提取标签"""
        tags = []
        content_lower = content.lower()
        
        # 基于数据类型的标签
        tags.append(data_type)
        
        # 基于内容的标签
        if 'select' in content_lower:
            tags.append('query')
        if 'join' in content_lower:
            tags.append('join')
        if 'group by' in content_lower:
            tags.append('aggregation')
        if 'order by' in content_lower:
            tags.append('sorting')
        if 'where' in content_lower:
            tags.append('filtering')
        if 'create table' in content_lower:
            tags.append('schema')
        if 'insert' in content_lower:
            tags.append('insert')
        if 'update' in content_lower:
            tags.append('update')
        if 'delete' in content_lower:
            tags.append('delete')
        
        return list(set(tags))  # 去重