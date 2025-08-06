"""
Application settings and configuration.
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration class."""
    
    def __init__(self):
        self.training_config = TrainingConfig()
        self.vector_store_config = VectorStoreConfig()
        self.embedding_config = EmbeddingConfig()
        self.database_config = DatabaseConfig()
        self.cache_config = CacheConfig()
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return os.getenv("ENVIRONMENT", "development").lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"


class TrainingConfig:
    """Training service configuration."""
    
    def __init__(self):
        self.auto_train_successful_queries = os.getenv("AUTO_TRAIN_SUCCESSFUL", "true").lower() == "true"
        self.max_training_examples_per_type = int(os.getenv("MAX_TRAINING_EXAMPLES", "1000"))
        self.embedding_batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
        self.training_data_retention_days = int(os.getenv("TRAINING_RETENTION_DAYS", "365"))


class VectorStoreConfig:
    """Vector store configuration."""
    
    def __init__(self):
        self.host = os.getenv("MILVUS_HOST", "localhost")
        self.port = os.getenv("MILVUS_PORT", "19530")
        self.collection_name = os.getenv("MILVUS_COLLECTION", "text2sql_vectors")
        self.dimension = int(os.getenv("MILVUS_DIMENSION", "1024"))
        self.use_mock = os.getenv("USE_MOCK_VECTOR_STORE", "false").lower() == "true"
        
        # Index configuration
        self.index_type = os.getenv("MILVUS_INDEX_TYPE", "IVF_FLAT")
        self.metric_type = os.getenv("MILVUS_METRIC_TYPE", "COSINE")
        self.nlist = int(os.getenv("MILVUS_NLIST", "1024"))


class EmbeddingConfig:
    """Embedding model configuration."""
    
    def __init__(self):
        self.model = os.getenv("EMBEDDING_MODEL")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.dimension = int(os.getenv("EMBEDDING_DIMENSION", "1024"))
        self.batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "10"))
        self.max_retries = int(os.getenv("EMBEDDING_MAX_RETRIES", "3"))


class DatabaseConfig:
    """Database configuration."""
    
    def __init__(self):
        self.default_db_type = os.getenv("DEFAULT_DB_TYPE", "sqlite")
        self.connection_timeout = int(os.getenv("DB_CONNECTION_TIMEOUT", "30"))
        self.max_connections = int(os.getenv("DB_MAX_CONNECTIONS", "10"))
        self.connection_retry_attempts = int(os.getenv("DB_RETRY_ATTEMPTS", "3"))


class CacheConfig:
    """Cache configuration."""
    
    def __init__(self):
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        self.redis_password = os.getenv("REDIS_PASSWORD")
        
        # Cache settings
        self.l1_cache_size = int(os.getenv("L1_CACHE_SIZE", "1000"))
        self.l2_cache_ttl = int(os.getenv("L2_CACHE_TTL", "86400"))  # 24 hours
        self.use_mock_cache = os.getenv("USE_MOCK_CACHE", "false").lower() == "true"


# Global configuration instance
config = Config()