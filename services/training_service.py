"""
Vanna.ai-style training service for Text2SQL system.
"""
import hashlib
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.models import TrainingData, TrainingDataType
from config.settings import config


class VannaTrainingService:
    """Vanna.ai式训练服务，支持多种类型的训练数据"""
    
    def __init__(self, vector_store, embedding_service):
        """Initialize training service.
        
        Args:
            vector_store: Vector database for storing embeddings
            embedding_service: Service for generating embeddings
        """
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.training_config = config.training_config
        self.training_data_store = {}
    
    def train_ddl(self, ddl_statements: List[str], db_id: str) -> bool:
        """训练DDL语句，让系统理解数据库结构
        
        Args:
            ddl_statements: DDL语句列表
            db_id: 数据库标识符
            
        Returns:
            bool: 训练是否成功
        """
        try:
            for ddl in ddl_statements:
                training_data = TrainingData(
                    id=self._generate_id(),
                    data_type=TrainingDataType.DDL_STATEMENT,
                    content=ddl,
                    db_id=db_id,
                    metadata={
                        "source": "schema_discovery",
                        "table_names": self._extract_table_names(ddl)
                    }
                )
                self._store_training_data(training_data)
            return True
        except Exception as e:
            print(f"Error training DDL: {e}")
            return False
    
    def train_documentation(self, docs: List[Dict[str, str]], db_id: str) -> bool:
        """训练业务文档，提供业务上下文
        
        Args:
            docs: 文档列表，每个文档包含title和content
            db_id: 数据库标识符
            
        Returns:
            bool: 训练是否成功
        """
        try:
            for doc in docs:
                training_data = TrainingData(
                    id=self._generate_id(),
                    data_type=TrainingDataType.DOCUMENTATION,
                    content=doc["content"],
                    db_id=db_id,
                    metadata={
                        "title": doc.get("title", ""),
                        "category": doc.get("category", "general"),
                        "source": "documentation"
                    }
                )
                self._store_training_data(training_data)
            return True
        except Exception as e:
            print(f"Error training documentation: {e}")
            return False
    
    def train_sql(self, sql_queries: List[str], db_id: str) -> bool:
        """训练SQL查询示例
        
        Args:
            sql_queries: SQL查询列表
            db_id: 数据库标识符
            
        Returns:
            bool: 训练是否成功
        """
        try:
            for sql in sql_queries:
                training_data = TrainingData(
                    id=self._generate_id(),
                    data_type=TrainingDataType.SQL_QUERY,
                    content=sql,
                    sql=sql,
                    db_id=db_id,
                    metadata={
                        "source": "sql_examples",
                        "table_names": self._extract_table_names_from_sql(sql)
                    }
                )
                self._store_training_data(training_data)
            return True
        except Exception as e:
            print(f"Error training SQL: {e}")
            return False
    
    def train_qa_pairs(self, qa_pairs: List[Dict[str, str]], db_id: str) -> bool:
        """训练问题-SQL对，这是最直接的训练方式
        
        Args:
            qa_pairs: 问题-SQL对列表
            db_id: 数据库标识符
            
        Returns:
            bool: 训练是否成功
        """
        try:
            for pair in qa_pairs:
                training_data = TrainingData(
                    id=self._generate_id(),
                    data_type=TrainingDataType.QUESTION_SQL_PAIR,
                    content=f"Q: {pair['question']}\nA: {pair['sql']}",
                    question=pair["question"],
                    sql=pair["sql"],
                    db_id=db_id,
                    metadata={
                        "source": "qa_training",
                        "table_names": self._extract_table_names_from_sql(pair["sql"])
                    }
                )
                self._store_training_data(training_data)
            return True
        except Exception as e:
            print(f"Error training QA pairs: {e}")
            return False
    
    def train_domain_knowledge(self, knowledge_items: List[Dict[str, str]], db_id: str) -> bool:
        """训练领域知识
        
        Args:
            knowledge_items: 领域知识项列表
            db_id: 数据库标识符
            
        Returns:
            bool: 训练是否成功
        """
        try:
            for item in knowledge_items:
                training_data = TrainingData(
                    id=self._generate_id(),
                    data_type=TrainingDataType.DOMAIN_KNOWLEDGE,
                    content=item["content"],
                    db_id=db_id,
                    metadata={
                        "category": item.get("category", "general"),
                        "source": "domain_knowledge",
                        "tags": item.get("tags", [])
                    },
                    tags=item.get("tags", [])
                )
                self._store_training_data(training_data)
            return True
        except Exception as e:
            print(f"Error training domain knowledge: {e}")
            return False
    
    def auto_train_from_successful_query(self, question: str, sql: str, db_id: str) -> bool:
        """从成功的查询中自动学习
        
        Args:
            question: 自然语言问题
            sql: 对应的SQL查询
            db_id: 数据库标识符
            
        Returns:
            bool: 训练是否成功
        """
        if not self.training_config.auto_train_successful_queries:
            return False
        
        return self.train_qa_pairs([{"question": question, "sql": sql}], db_id)
    
    def get_training_stats(self, db_id: Optional[str] = None) -> Dict[str, Any]:
        """获取训练统计信息
        
        Args:
            db_id: 可选的数据库标识符，如果提供则只返回该数据库的统计
            
        Returns:
            Dict: 训练统计信息
        """
        # 这里应该从向量数据库查询统计信息
        # 简化实现，返回基本统计
        return {
            "total_training_examples": len(self.training_data_store),
            "by_type": {
                "ddl": 0,
                "documentation": 0,
                "sql": 0,
                "qa_pairs": 0,
                "domain_knowledge": 0
            },
            "db_id": db_id
        }
    
    def _store_training_data(self, training_data: TrainingData):
        """存储训练数据到向量数据库"""
        # 生成向量嵌入
        embedding = self.embedding_service.generate_embedding(training_data.content)
        training_data.embedding = embedding
        
        # 存储到向量数据库
        self.vector_store.insert(
            id=training_data.id,
            vector=embedding,
            metadata={
                "data_type": training_data.data_type.value,
                "db_id": training_data.db_id,
                "content": training_data.content,
                "question": training_data.question,
                "sql": training_data.sql,
                "table_names": training_data.table_names,
                "tags": training_data.tags,
                "created_at": training_data.created_at.isoformat(),
                **training_data.metadata
            }
        )
        
        # 本地缓存
        self.training_data_store[training_data.id] = training_data
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        return str(uuid.uuid4())
    
    def _extract_table_names(self, ddl: str) -> List[str]:
        """从DDL语句中提取表名"""
        # 简化实现，实际应该使用SQL解析器
        import re
        table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`"]?\w+[`"]?)'
        matches = re.findall(table_pattern, ddl, re.IGNORECASE)
        return [match.strip('`"') for match in matches]
    
    def _extract_table_names_from_sql(self, sql: str) -> List[str]:
        """从SQL查询中提取表名"""
        # 简化实现，实际应该使用SQL解析器
        import re
        # 匹配FROM和JOIN后的表名
        table_pattern = r'(?:FROM|JOIN)\s+([`"]?\w+[`"]?)'
        matches = re.findall(table_pattern, sql, re.IGNORECASE)
        return [match.strip('`"') for match in matches]


class EnhancedRAGRetriever:
    """增强型RAG检索器，结合Vanna.ai的检索策略"""
    
    def __init__(self, vector_store, embedding_service):
        """Initialize retriever.
        
        Args:
            vector_store: Vector database for searching
            embedding_service: Service for generating embeddings
        """
        self.vector_store = vector_store
        self.embedding_service = embedding_service
    
    def retrieve_context(self, query: str, db_id: str, top_k: int = 5) -> Dict[str, List]:
        """检索与查询相关的上下文信息
        
        Args:
            query: 用户查询
            db_id: 数据库标识符
            top_k: 每种类型返回的最大结果数
            
        Returns:
            Dict: 分类的上下文信息
        """
        query_embedding = self.embedding_service.generate_embedding(query)
        
        # 多类型检索策略
        context = {
            "ddl_statements": [],
            "documentation": [],
            "sql_examples": [],
            "qa_pairs": [],
            "domain_knowledge": []
        }
        
        # 1. 检索相关的DDL语句
        ddl_results = self.vector_store.search(
            vector=query_embedding,
            filter={"data_type": "ddl", "db_id": db_id},
            limit=top_k
        )
        context["ddl_statements"] = [r.metadata["content"] for r in ddl_results]
        
        # 2. 检索相关的文档
        doc_results = self.vector_store.search(
            vector=query_embedding,
            filter={"data_type": "doc", "db_id": db_id},
            limit=top_k
        )
        context["documentation"] = [r.metadata["content"] for r in doc_results]
        
        # 3. 检索相似的SQL示例
        sql_results = self.vector_store.search(
            vector=query_embedding,
            filter={"data_type": "sql", "db_id": db_id},
            limit=top_k
        )
        context["sql_examples"] = [r.metadata["sql"] for r in sql_results if r.metadata.get("sql")]
        
        # 4. 检索相似的问题-SQL对
        qa_results = self.vector_store.search(
            vector=query_embedding,
            filter={"data_type": "qa_pair", "db_id": db_id},
            limit=top_k
        )
        context["qa_pairs"] = [
            {"question": r.metadata["question"], "sql": r.metadata["sql"]}
            for r in qa_results
            if r.metadata.get("question") and r.metadata.get("sql")
        ]
        
        # 5. 检索领域知识
        domain_results = self.vector_store.search(
            vector=query_embedding,
            filter={"data_type": "domain", "db_id": db_id},
            limit=top_k
        )
        context["domain_knowledge"] = [r.metadata["content"] for r in domain_results]
        
        return context
    
    def build_enhanced_prompt(self, query: str, context: Dict[str, List], schema_info: str) -> str:
        """构建增强的提示词，结合检索到的上下文
        
        Args:
            query: 用户查询
            context: 检索到的上下文信息
            schema_info: 数据库模式信息
            
        Returns:
            str: 增强的提示词
        """
        prompt_parts = [
            "# Text2SQL Task",
            f"Convert the following natural language question to SQL:",
            f"Question: {query}",
            "",
            "# Database Schema",
            schema_info,
            ""
        ]
        
        # 添加相关的DDL语句
        if context["ddl_statements"]:
            prompt_parts.extend([
                "# Relevant Database Definitions",
                *context["ddl_statements"],
                ""
            ])
        
        # 添加业务文档上下文
        if context["documentation"]:
            prompt_parts.extend([
                "# Business Context",
                *context["documentation"][:2],  # 限制数量
                ""
            ])
        
        # 添加相似的SQL示例
        if context["sql_examples"]:
            prompt_parts.extend([
                "# Similar SQL Examples",
                *context["sql_examples"][:3],  # 限制数量
                ""
            ])
        
        # 添加相似的问题-SQL对
        if context["qa_pairs"]:
            prompt_parts.append("# Similar Question-SQL Pairs")
            for pair in context["qa_pairs"][:2]:  # 限制数量
                prompt_parts.extend([
                    f"Q: {pair['question']}",
                    f"A: {pair['sql']}",
                    ""
                ])
        
        # 添加领域知识
        if context["domain_knowledge"]:
            prompt_parts.extend([
                "# Domain Knowledge",
                *context["domain_knowledge"][:2],  # 限制数量
                ""
            ])
        
        prompt_parts.extend([
            "# Instructions",
            "Based on the above context, generate a SQL query that answers the question.",
            "Ensure the SQL is syntactically correct and follows best practices.",
            "",
            "SQL:"
        ])
        
        return "\n".join(prompt_parts)