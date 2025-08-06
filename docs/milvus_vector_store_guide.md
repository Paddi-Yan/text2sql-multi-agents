# Milvus Vector Store Guide

本指南介绍如何使用Text2SQL系统中的Milvus向量存储功能。

## 概述

Milvus向量存储系统是Text2SQL多智能体服务的核心组件，负责：

- 存储和检索训练数据的向量表示
- 支持语义相似性搜索
- 提供高性能的向量操作
- 支持多种数据类型（DDL、文档、SQL示例、QA对、领域知识）

## 快速开始

### 1. 环境准备

#### 使用Docker Compose（推荐）

```bash
# 启动Milvus和Redis服务
docker-compose up -d

# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs milvus-standalone
```

#### 手动安装Milvus

请参考[Milvus官方文档](https://milvus.io/docs/install_standalone-docker.md)进行安装。

### 2. 环境变量配置

创建`.env`文件或设置环境变量：

```bash
# Milvus配置
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION=text2sql_vectors
MILVUS_DIMENSION=1536

# 开发模式（使用Mock向量存储）
USE_MOCK_VECTOR_STORE=false

# OpenAI配置（用于生成真实嵌入）
OPENAI_API_KEY=your_openai_api_key_here
EMBEDDING_MODEL=text-embedding-ada-002
```

### 3. 基本使用

#### 初始化向量存储

```python
from storage.vector_store import VectorStore

# 初始化向量存储（使用配置文件中的设置）
vector_store = VectorStore()

# 或者指定自定义参数
vector_store = VectorStore(
    host="localhost",
    port="19530",
    collection_name="my_collection",
    dimension=1536
)
```

#### 插入向量数据

```python
import uuid
from services.embedding_service import EmbeddingService

# 初始化嵌入服务
embedding_service = EmbeddingService()

# 准备数据
text = "SELECT COUNT(*) FROM users WHERE active = 1"
embedding = embedding_service.generate_embedding(text)
metadata = {
    "data_type": "sql",
    "db_id": "ecommerce_db",
    "content": text,
    "sql": text
}

# 插入向量
vector_id = str(uuid.uuid4())
vector_store.insert(vector_id, embedding, metadata)
```

#### 搜索相似向量

```python
# 搜索相似向量
query_text = "Count active users"
query_embedding = embedding_service.generate_embedding(query_text)

results = vector_store.search(
    vector=query_embedding,
    filter={"data_type": "sql", "db_id": "ecommerce_db"},
    limit=5
)

for result in results:
    print(f"ID: {result.id}")
    print(f"Score: {result.score:.3f}")
    print(f"Content: {result.metadata.get('content', 'N/A')}")
    print("---")
```

## 高级功能

### 1. 训练服务集成

```python
from services.training_service import VannaTrainingService

# 初始化训练服务
training_service = VannaTrainingService(
    vector_store=vector_store,
    embedding_service=embedding_service
)

# 训练DDL语句
ddl_statements = [
    "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100));",
    "CREATE TABLE orders (id INT PRIMARY KEY, user_id INT);"
]
training_service.train_ddl(ddl_statements, "ecommerce_db")

# 训练问题-SQL对
qa_pairs = [
    {
        "question": "How many users are there?",
        "sql": "SELECT COUNT(*) FROM users;"
    }
]
training_service.train_qa_pairs(qa_pairs, "ecommerce_db")
```

### 2. 增强型RAG检索

```python
from services.enhanced_rag_retriever import EnhancedRAGRetriever, RetrievalConfig, RetrievalStrategy

# 配置检索策略
config = RetrievalConfig(
    strategy=RetrievalStrategy.QA_FOCUSED,
    similarity_threshold=0.7,
    max_examples_per_type=3
)

# 初始化检索器
retriever = EnhancedRAGRetriever(
    vector_store=vector_store,
    embedding_service=embedding_service,
    config=config
)

# 检索上下文
query = "Show me the top customers by spending"
context = retriever.retrieve_context(query, "ecommerce_db")

# 构建增强提示词
schema_info = "# Database Schema\n[Your schema here]"
prompt = retriever.build_enhanced_prompt(query, context, schema_info)
```

### 3. 批量操作

```python
# 批量插入
texts = ["SQL query 1", "SQL query 2", "SQL query 3"]
embeddings = embedding_service.generate_embeddings_batch(texts)
ids = [str(uuid.uuid4()) for _ in texts]
metadatas = [
    {"data_type": "sql", "db_id": "test_db", "content": text}
    for text in texts
]

vector_store.insert_batch(ids, embeddings, metadatas)

# 批量删除
vector_store.delete_by_filter({"db_id": "test_db"})
```

## 配置选项

### Milvus配置

```python
# 在config/vector_store_config.py中配置
class VectorStoreConfig:
    @staticmethod
    def get_milvus_config():
        return {
            "host": "localhost",
            "port": "19530",
            "collection_name": "text2sql_vectors",
            "dimension": 1536,
        }
```

### 索引配置

```python
# 创建或更新索引
vector_store.create_index(
    field_name="vector",
    index_type="IVF_FLAT",  # 或 "IVF_SQ8", "HNSW"
    metric_type="COSINE",   # 或 "L2", "IP"
    params={"nlist": 1024}
)
```

## 性能优化

### 1. 索引选择

- **IVF_FLAT**: 精确搜索，适合小到中等数据集
- **IVF_SQ8**: 量化索引，节省内存
- **HNSW**: 高性能近似搜索，适合大数据集

### 2. 批量操作

```python
# 推荐：使用批量插入而不是单个插入
vector_store.insert_batch(ids, vectors, metadatas)

# 避免：频繁的单个插入
for id, vector, metadata in zip(ids, vectors, metadatas):
    vector_store.insert(id, vector, metadata)  # 不推荐
```

### 3. 连接管理

```python
# 使用完毕后关闭连接
vector_store.close()
```

## 监控和调试

### 1. 集合统计

```python
stats = vector_store.get_collection_stats()
print(f"Total entities: {stats['total_entities']}")
print(f"Collection name: {stats['collection_name']}")
print(f"Dimension: {stats['dimension']}")
```

### 2. 健康检查

```python
from services.embedding_service import EmbeddingService

embedding_service = EmbeddingService()
health = embedding_service.health_check()
print(f"Service status: {health['status']}")
```

### 3. 日志配置

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("storage.vector_store")
```

## 故障排除

### 常见问题

1. **连接失败**
   ```
   Failed to connect to Milvus: [Errno 111] Connection refused
   ```
   - 检查Milvus服务是否运行：`docker-compose ps`
   - 检查端口是否正确：默认19530

2. **集合不存在**
   ```
   Collection 'text2sql_vectors' doesn't exist
   ```
   - 系统会自动创建集合，检查权限和连接

3. **维度不匹配**
   ```
   Dimension mismatch: expected 1536, got 768
   ```
   - 检查嵌入模型配置和向量存储配置的维度设置

4. **内存不足**
   ```
   Out of memory when loading collection
   ```
   - 增加Docker内存限制或使用量化索引

### 开发环境配置

开发和测试时，请确保Milvus服务正在运行，或使用Docker Compose启动：

```bash
docker-compose up -d milvus-standalone
```

## 示例代码

完整的示例代码请参考：

- `examples/milvus_vector_store_example.py` - 基础使用示例
- `examples/complete_vector_system_example.py` - 完整系统演示
- `tests/unit/test_vector_store.py` - 单元测试示例

## 相关文档

- [Milvus官方文档](https://milvus.io/docs)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [项目架构文档](../design.md)