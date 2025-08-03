"""
Training data models and types for Vanna.ai-style RAG training system.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime


class TrainingDataType(Enum):
    """训练数据类型枚举"""
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
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "data_type": self.data_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "db_id": self.db_id,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat(),
            "question": self.question,
            "sql": self.sql,
            "table_names": self.table_names,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrainingData':
        """从字典创建实例"""
        return cls(
            id=data["id"],
            data_type=TrainingDataType(data["data_type"]),
            content=data["content"],
            metadata=data["metadata"],
            db_id=data["db_id"],
            embedding=data.get("embedding"),
            created_at=datetime.fromisoformat(data["created_at"]),
            question=data.get("question"),
            sql=data.get("sql"),
            table_names=data.get("table_names", []),
            tags=data.get("tags", [])
        )


@dataclass
class TrainingDataStats:
    """训练数据统计信息"""
    total_count: int = 0
    ddl_count: int = 0
    doc_count: int = 0
    sql_count: int = 0
    qa_pair_count: int = 0
    domain_count: int = 0
    db_coverage: Dict[str, int] = field(default_factory=dict)
    tag_distribution: Dict[str, int] = field(default_factory=dict)
    
    def update_stats(self, training_data: TrainingData):
        """更新统计信息"""
        self.total_count += 1
        
        # 按类型统计
        if training_data.data_type == TrainingDataType.DDL_STATEMENT:
            self.ddl_count += 1
        elif training_data.data_type == TrainingDataType.DOCUMENTATION:
            self.doc_count += 1
        elif training_data.data_type == TrainingDataType.SQL_QUERY:
            self.sql_count += 1
        elif training_data.data_type == TrainingDataType.QUESTION_SQL_PAIR:
            self.qa_pair_count += 1
        elif training_data.data_type == TrainingDataType.DOMAIN_KNOWLEDGE:
            self.domain_count += 1
        
        # 数据库覆盖度统计
        if training_data.db_id in self.db_coverage:
            self.db_coverage[training_data.db_id] += 1
        else:
            self.db_coverage[training_data.db_id] = 1
        
        # 标签分布统计
        for tag in training_data.tags:
            if tag in self.tag_distribution:
                self.tag_distribution[tag] += 1
            else:
                self.tag_distribution[tag] = 1