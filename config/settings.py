"""
Application settings and configuration management.
"""
import os
from dataclasses import dataclass
from typing import Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, skip loading .env file
    pass


@dataclass
class LLMConfig:
    """LLM configuration settings."""
    model_name: str = "gpt-4"
    api_key: Optional[str] = None
    max_tokens: int = 2000
    temperature: float = 0.1
    timeout: int = 30
    
    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("OPENAI_API_KEY")


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    host: str = "127.0.0.1"
    port: int = 3306
    username: Optional[str] = "root"
    password: Optional[str] = "123456"
    database: Optional[str] = "text2sql_db"
    driver: str = "mysql+pymysql"
    charset: str = "utf8mb4"
    
    def __post_init__(self):
        self.host = os.getenv("DB_HOST", self.host)
        self.port = int(os.getenv("DB_PORT", str(self.port)))
        self.username = os.getenv("DB_USER", self.username)
        self.password = os.getenv("DB_PASSWORD", self.password)
        self.database = os.getenv("DB_NAME", self.database)
    
    @property
    def connection_string(self) -> str:
        """Get database connection string."""
        return f"{self.driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}?charset={self.charset}"


@dataclass
class CacheConfig:
    """Redis cache configuration."""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    ttl: int = 86400  # 24 hours
    max_connections: int = 10
    
    def __post_init__(self):
        self.host = os.getenv("REDIS_HOST", self.host)
        self.port = int(os.getenv("REDIS_PORT", str(self.port)))
        self.password = os.getenv("REDIS_PASSWORD", self.password)


@dataclass
class VectorStoreConfig:
    """Milvus vector store configuration."""
    host: str = "localhost"
    port: int = 19530
    collection_name: str = "text2sql_memory"
    dimension: int = 1536  # OpenAI embedding dimension
    
    def __post_init__(self):
        self.host = os.getenv("MILVUS_HOST", self.host)
        self.port = int(os.getenv("MILVUS_PORT", str(self.port)))


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    enable_sql_injection_check: bool = True
    max_query_length: int = 10000
    allowed_operations: list = None
    
    def __post_init__(self):
        if self.allowed_operations is None:
            self.allowed_operations = ["SELECT", "WITH"]


@dataclass
class MonitoringConfig:
    """Monitoring and logging configuration."""
    log_level: str = "INFO"
    enable_tracing: bool = True
    metrics_port: int = 8080
    
    def __post_init__(self):
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)


@dataclass
class TrainingConfig:
    """Vanna.ai-style training configuration."""
    embedding_model: str = "text-embedding-ada-002"
    auto_train_ddl: bool = True
    auto_train_successful_queries: bool = True
    training_batch_size: int = 100
    similarity_threshold: float = 0.8
    max_training_examples: int = 10000
    enable_incremental_learning: bool = True
    
    def __post_init__(self):
        self.embedding_model = os.getenv("EMBEDDING_MODEL", self.embedding_model)


@dataclass
class SystemConfig:
    """Main system configuration."""
    llm_config: LLMConfig
    database_config: DatabaseConfig
    cache_config: CacheConfig
    vector_store_config: VectorStoreConfig
    training_config: TrainingConfig
    security_config: SecurityConfig
    monitoring_config: MonitoringConfig
    
    def __init__(self):
        self.llm_config = LLMConfig()
        self.database_config = DatabaseConfig()
        self.cache_config = CacheConfig()
        self.vector_store_config = VectorStoreConfig()
        self.training_config = TrainingConfig()
        self.security_config = SecurityConfig()
        self.monitoring_config = MonitoringConfig()


# Global configuration instance
config = SystemConfig()