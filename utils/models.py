"""
Core data models and interfaces for Text2SQL system.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum


@dataclass
class ChatMessage:
    """Standard message format for inter-agent communication."""
    db_id: str
    query: str
    evidence: str = ""
    extracted_schema: Optional[Dict] = None
    desc_str: str = ""
    fk_str: str = ""
    final_sql: str = ""
    qa_pairs: str = ""
    send_to: str = "System"
    pruned: bool = False
    fixed: bool = False
    execution_result: Optional[Dict] = None
    chosen_db_schema_dict: Optional[Dict] = None
    
    # Enhanced fields for better message tracking and routing
    message_id: str = field(default_factory=lambda: str(id(object())))
    timestamp: datetime = field(default_factory=datetime.now)
    sender: str = "System"
    priority: int = 1  # 1=low, 2=normal, 3=high, 4=urgent
    retry_count: int = 0
    max_retries: int = 3
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def copy(self) -> 'ChatMessage':
        """Create a copy of the message."""
        import copy
        return copy.deepcopy(self)
    
    def route_to(self, agent_name: str) -> 'ChatMessage':
        """Create a copy of message routed to specific agent.
        
        Args:
            agent_name: Target agent name
            
        Returns:
            New message instance with updated routing
        """
        new_message = self.copy()
        new_message.send_to = agent_name
        new_message.sender = self.send_to if self.send_to != "System" else "System"
        return new_message
    
    def add_context(self, key: str, value: Any) -> 'ChatMessage':
        """Add context information to message.
        
        Args:
            key: Context key
            value: Context value
            
        Returns:
            Self for method chaining
        """
        self.context[key] = value
        return self
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get context value.
        
        Args:
            key: Context key
            default: Default value
            
        Returns:
            Context value or default
        """
        return self.context.get(key, default)
    
    def increment_retry(self) -> bool:
        """Increment retry count.
        
        Returns:
            True if retry is allowed, False if max retries exceeded
        """
        self.retry_count += 1
        return self.retry_count <= self.max_retries
    
    def is_high_priority(self) -> bool:
        """Check if message has high priority.
        
        Returns:
            True if priority is high or urgent
        """
        return self.priority >= 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary.
        
        Returns:
            Dictionary representation of message
        """
        return {
            "message_id": self.message_id,
            "timestamp": self.timestamp.isoformat(),
            "db_id": self.db_id,
            "query": self.query,
            "evidence": self.evidence,
            "send_to": self.send_to,
            "sender": self.sender,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "final_sql": self.final_sql,
            "pruned": self.pruned,
            "fixed": self.fixed,
            "context": self.context,
            "metadata": self.metadata
        }


@dataclass
class DatabaseInfo:
    """Database metadata information."""
    desc_dict: Dict[str, List[Tuple[str, str, str]]]  # table -> column descriptions
    value_dict: Dict[str, List[Tuple[str, str]]]      # table -> column value examples
    pk_dict: Dict[str, List[str]]                     # table -> primary key columns
    fk_dict: Dict[str, List[Tuple[str, str, str]]]    # table -> foreign key relations


@dataclass
class DatabaseStats:
    """Database statistics information."""
    table_count: int
    max_column_count: int
    total_column_count: int
    avg_column_count: int


@dataclass
class SQLExecutionResult:
    """SQL execution result container."""
    sql: str
    data: Optional[List[Tuple]] = None
    sqlite_error: str = ""
    exception_class: str = ""
    execution_time: float = 0.0
    is_successful: bool = False


class MemoryType(Enum):
    """Types of memory records."""
    POSITIVE_EXAMPLE = "positive"
    NEGATIVE_EXAMPLE = "negative"
    PATTERN_TEMPLATE = "template"
    DOMAIN_KNOWLEDGE = "domain"


class TrainingDataType(Enum):
    """Training data types for Vanna.ai-style RAG system."""
    DDL_STATEMENT = "ddl"           # Data Definition Language statements
    DOCUMENTATION = "doc"           # Business documentation
    SQL_QUERY = "sql"              # SQL query examples
    QUESTION_SQL_PAIR = "qa_pair"   # Question-SQL pairs
    DOMAIN_KNOWLEDGE = "domain"     # Domain-specific knowledge


@dataclass
class TrainingData:
    """Training data record for Vanna.ai-style RAG system."""
    id: str
    data_type: TrainingDataType
    content: str
    metadata: Dict[str, Any]
    db_id: str
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # Type-specific fields
    question: Optional[str] = None      # For QA pairs
    sql: Optional[str] = None          # For QA pairs and SQL examples
    table_names: List[str] = field(default_factory=list)  # Related table names
    tags: List[str] = field(default_factory=list)         # Tags for categorization


@dataclass
class MemoryRecord:
    """Memory storage record for learning system."""
    id: str
    natural_query: str
    sql_query: str
    db_id: str
    is_correct: bool
    user_feedback: str
    execution_result: SQLExecutionResult
    embedding: List[float]
    similarity_score: float = 0.0
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class LearningMetrics:
    """Learning effectiveness evaluation metrics."""
    accuracy_trend: List[float]
    pattern_coverage: Dict[str, int]
    error_reduction_rate: float
    improvement_rate: float


class RiskLevel(Enum):
    """Security risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityValidationResult:
    """SQL security validation result."""
    is_safe: bool
    risk_level: RiskLevel
    detected_pattern: Optional[str] = None
    error: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RetryPolicy:
    """Retry policy configuration."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        return delay


@dataclass
class SystemMetrics:
    """System performance metrics."""
    query_count: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    average_response_time: float = 0.0
    cache_hit_rate: float = 0.0
    accuracy_rate: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.query_count == 0:
            return 0.0
        return self.successful_queries / self.query_count
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.query_count == 0:
            return 0.0
        return self.failed_queries / self.query_count


@dataclass
class QueryContext:
    """Context information for query processing."""
    user_id: str
    session_id: str
    timestamp: datetime
    db_id: str
    query: str
    evidence: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Standard response format from agents."""
    success: bool
    message: ChatMessage
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)