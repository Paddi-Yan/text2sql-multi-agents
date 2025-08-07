"""
Data models for the Text2SQL system.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple


class TrainingDataType(Enum):
    """训练数据类型"""
    DDL_STATEMENT = "ddl"           # 数据定义语言语句
    DOCUMENTATION = "doc"           # 业务文档和说明
    SQL_QUERY = "sql"              # SQL查询示例
    QUESTION_SQL_PAIR = "qa_pair"   # 问题-SQL对
    DOMAIN_KNOWLEDGE = "domain"     # 领域知识


@dataclass
class TrainingData:
    """训练数据记录"""
    id: str
    data_type: TrainingDataType
    content: str
    metadata: Dict[str, Any]
    db_id: str
    embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # 特定类型的字段
    question: Optional[str] = None      # 用于QA对
    sql: Optional[str] = None          # 用于QA对和SQL示例
    table_names: List[str] = field(default_factory=list)  # 相关表名
    tags: List[str] = field(default_factory=list)         # 标签


@dataclass
class ErrorRecord:
    """单次错误记录"""
    attempt_number: int                 # 尝试次数
    failed_sql: str                    # 失败的SQL语句
    error_message: str                 # 错误消息
    error_type: str                    # 错误类型（语法错误、模式错误、逻辑错误、执行错误）
    timestamp: float                   # 错误发生时间戳


@dataclass
class ChatMessage:
    """智能体间消息传递的标准格式"""
    db_id: str
    query: str
    evidence: str = ""
    extracted_schema: dict = None
    desc_str: str = ""
    fk_str: str = ""
    final_sql: str = ""
    qa_pairs: str = ""
    send_to: str = "System"
    pruned: bool = False
    fixed: bool = False
    execution_result: dict = None
    chosen_db_schema_dict: dict = None
    
    # 新增多轮错误历史字段
    error_history: List[Dict[str, Any]] = field(default_factory=list)  # 错误历史记录
    error_context_available: bool = False  # 是否有错误上下文可用
    
    def get_context(self, key: str, default=None):
        """获取上下文信息的辅助方法"""
        if hasattr(self, key):
            return getattr(self, key)
        return default


@dataclass
class DatabaseInfo:
    """数据库元数据信息"""
    desc_dict: Dict[str, List[Tuple[str, str, str]]]  # 表->列描述
    value_dict: Dict[str, List[Tuple[str, str]]]      # 表->列值示例
    pk_dict: Dict[str, List[str]]                     # 表->主键列
    fk_dict: Dict[str, List[Tuple[str, str, str]]]    # 表->外键关系


@dataclass
class DatabaseStats:
    """数据库统计信息"""
    table_count: int
    max_column_count: int
    total_column_count: int
    avg_column_count: int


@dataclass
class SQLExecutionResult:
    """SQL执行结果"""
    sql: str
    data: List[Tuple] = None
    sqlite_error: str = ""
    exception_class: str = ""
    execution_time: float = 0.0
    is_successful: bool = False


@dataclass
class MemoryRecord:
    """记忆存储记录"""
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
    """学习效果评估指标"""
    accuracy_trend: List[float]
    pattern_coverage: Dict[str, int]
    error_reduction_rate: float
    improvement_rate: float


class MemoryType(Enum):
    """记忆类型枚举"""
    POSITIVE_EXAMPLE = "positive"  # 正确的查询示例
    NEGATIVE_EXAMPLE = "negative"  # 错误的查询示例
    PATTERN_TEMPLATE = "template"  # 查询模式模板
    DOMAIN_KNOWLEDGE = "domain"    # 领域知识


class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class SecurityValidationResult:
    """安全验证结果"""
    is_safe: bool
    risk_level: RiskLevel
    detected_pattern: Optional[str] = None
    error: Optional[str] = None
    message: str = ""


@dataclass
class VectorSearchFilter:
    """向量搜索过滤器"""
    data_type: Optional[str] = None
    db_id: Optional[str] = None
    table_names: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式用于向量数据库查询"""
        filter_dict = {}
        
        if self.data_type:
            filter_dict["data_type"] = self.data_type
        if self.db_id:
            filter_dict["db_id"] = self.db_id
            
        return filter_dict


@dataclass
class EmbeddingRequest:
    """嵌入生成请求"""
    text: str
    model: str = "text-embedding-ada-002"
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbeddingResponse:
    """嵌入生成响应"""
    embedding: List[float]
    model: str
    usage: Dict[str, int]
    request_id: str
    processing_time: float = 0.0


@dataclass
class AgentResponse:
    """智能体响应标准格式"""
    success: bool
    message: ChatMessage
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


def classify_error_type(error_message: str) -> str:
    """
    简单的错误类型分类函数
    
    Args:
        error_message: 错误消息
        
    Returns:
        错误类型字符串
    """
    if not error_message:
        return 'unknown_error'
    
    error_msg_lower = error_message.lower()
    
    # 语法错误
    syntax_keywords = ['syntax error', 'invalid syntax', 'unexpected token', 'parse error', 'malformed']
    if any(keyword in error_msg_lower for keyword in syntax_keywords):
        return 'syntax_error'
    
    # 模式错误（表名、列名不存在）
    schema_keywords = ['no such table', 'no such column', 'ambiguous column', 'unknown table', 'unknown column']
    if any(keyword in error_msg_lower for keyword in schema_keywords):
        return 'schema_error'
    
    # 逻辑错误（GROUP BY、聚合函数等）
    logic_keywords = ['group by', 'aggregate', 'having clause', 'must appear in the group by', 'not a group by expression']
    if any(keyword in error_msg_lower for keyword in logic_keywords):
        return 'logic_error'
    
    # 执行错误（超时、连接等）
    execution_keywords = ['timeout', 'connection', 'permission denied', 'access denied', 'database locked']
    if any(keyword in error_msg_lower for keyword in execution_keywords):
        return 'execution_error'
    
    # 默认为执行错误
    return 'execution_error'