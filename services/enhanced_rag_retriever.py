"""
Enhanced RAG retriever with advanced features for Text2SQL system.
"""
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from utils.models import TrainingDataType
from config.settings import config
from storage.vector_store import vector_store
from services.embedding_service import embedding_service


class RetrievalStrategy(Enum):
    """检索策略枚举"""
    BALANCED = "balanced"           # 平衡检索各种类型
    QA_FOCUSED = "qa_focused"       # 重点检索QA对
    SQL_FOCUSED = "sql_focused"     # 重点检索SQL示例
    CONTEXT_FOCUSED = "context_focused"  # 重点检索上下文信息


@dataclass
class RetrievalConfig:
    """检索配置"""
    similarity_threshold: float = 0.7      # 相似度阈值
    max_context_length: int = 8000          # 最大上下文长度
    max_examples_per_type: int = 3          # 每种类型最大示例数
    enable_quality_filter: bool = True     # 启用质量过滤
    enable_diversity_filter: bool = True   # 启用多样性过滤
    strategy: RetrievalStrategy = RetrievalStrategy.BALANCED


@dataclass
class RetrievalResult:
    """检索结果"""
    id: str
    content: str
    score: float
    data_type: str
    metadata: Dict[str, Any]
    
    @property
    def is_high_quality(self) -> bool:
        """判断是否为高质量结果"""
        return self.score >= 0.8


class QualityFilter:
    """质量过滤器"""
    
    @staticmethod
    def filter_by_similarity(results: List[RetrievalResult], 
                           threshold: float = 0.7) -> List[RetrievalResult]:
        """基于相似度过滤"""
        return [r for r in results if r.score >= threshold]
    
    @staticmethod
    def filter_by_content_quality(results: List[RetrievalResult]) -> List[RetrievalResult]:
        """基于内容质量过滤"""
        filtered = []
        for result in results:
            # 过滤掉过短或过长的内容
            content_length = len(result.content.strip())
            if 10 <= content_length <= 2000:
                # 过滤掉包含明显错误的SQL
                if result.data_type in ["sql", "qa_pair"]:
                    if not QualityFilter._has_sql_errors(result.content):
                        filtered.append(result)
                else:
                    filtered.append(result)
        return filtered
    
    @staticmethod
    def _has_sql_errors(content: str) -> bool:
        """检查SQL是否有明显错误"""
        # 简单的SQL错误检查
        sql_content = content.lower()
        error_patterns = [
            r'syntax\s+error',
            r'invalid\s+syntax',
            r'missing\s+from',
            r'unknown\s+column',
            r'table.*doesn\'t\s+exist'
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, sql_content):
                return True
        return False


class DiversityFilter:
    """多样性过滤器"""
    
    @staticmethod
    def ensure_diversity(results: List[RetrievalResult], 
                        max_similar: int = 2) -> List[RetrievalResult]:
        """确保结果多样性，避免过于相似的结果"""
        if len(results) <= max_similar:
            return results
        
        diverse_results = []
        for result in results:
            is_similar_to_existing = False
            for existing in diverse_results:
                if DiversityFilter._are_similar(result, existing):
                    is_similar_to_existing = True
                    break
            
            if not is_similar_to_existing:
                diverse_results.append(result)
            elif len(diverse_results) < max_similar:
                diverse_results.append(result)
        
        return diverse_results
    
    @staticmethod
    def _are_similar(result1: RetrievalResult, result2: RetrievalResult) -> bool:
        """判断两个结果是否过于相似"""
        # 简单的相似性判断
        content1 = result1.content.lower().strip()
        content2 = result2.content.lower().strip()
        
        # 如果内容长度差异很大，认为不相似
        if abs(len(content1) - len(content2)) > max(len(content1), len(content2)) * 0.5:
            return False
        
        # 计算简单的词汇重叠度
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        if not words1 or not words2:
            return False
        
        overlap = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        jaccard_similarity = overlap / union if union > 0 else 0
        
        # 降低阈值，使相似的SQL查询更容易被识别为相似
        return jaccard_similarity >= 0.5


class ContextBuilder:
    """上下文构建器"""
    
    def __init__(self, config: RetrievalConfig):
        self.config = config
    
    def build_context(self, results_by_type: Dict[str, List[RetrievalResult]]) -> Dict[str, List]:
        """构建分类的上下文"""
        context = {
            "ddl_statements": [],
            "documentation": [],
            "sql_examples": [],
            "qa_pairs": [],
            "domain_knowledge": []
        }
        
        # 根据策略调整各类型的权重
        type_limits = self._get_type_limits()
        
        # 处理DDL语句
        if "ddl" in results_by_type:
            context["ddl_statements"] = [
                r.content for r in results_by_type["ddl"][:type_limits["ddl"]]
            ]
        
        # 处理文档
        if "doc" in results_by_type:
            context["documentation"] = [
                r.content for r in results_by_type["doc"][:type_limits["doc"]]
            ]
        
        # 处理SQL示例
        if "sql" in results_by_type:
            context["sql_examples"] = [
                r.metadata.get("sql", r.content) 
                for r in results_by_type["sql"][:type_limits["sql"]]
                if r.metadata.get("sql")
            ]
        
        # 处理QA对
        if "qa_pair" in results_by_type:
            context["qa_pairs"] = [
                {
                    "question": r.metadata.get("question", ""),
                    "sql": r.metadata.get("sql", ""),
                    "score": r.score
                }
                for r in results_by_type["qa_pair"][:type_limits["qa_pair"]]
                if r.metadata.get("question") and r.metadata.get("sql")
            ]
        
        # 处理领域知识
        if "domain" in results_by_type:
            context["domain_knowledge"] = [
                r.content for r in results_by_type["domain"][:type_limits["domain"]]
            ]
        
        return context
    
    def _get_type_limits(self) -> Dict[str, int]:
        """根据策略获取各类型的限制数量"""
        base_limit = self.config.max_examples_per_type
        
        if self.config.strategy == RetrievalStrategy.QA_FOCUSED:
            return {
                "ddl": max(1, base_limit // 2),
                "doc": max(1, base_limit // 2),
                "sql": base_limit,
                "qa_pair": base_limit * 2,
                "domain": max(1, base_limit // 2)
            }
        elif self.config.strategy == RetrievalStrategy.SQL_FOCUSED:
            return {
                "ddl": max(1, base_limit // 2),
                "doc": max(1, base_limit // 2),
                "sql": base_limit * 2,
                "qa_pair": base_limit,
                "domain": max(1, base_limit // 2)
            }
        elif self.config.strategy == RetrievalStrategy.CONTEXT_FOCUSED:
            return {
                "ddl": base_limit * 2,
                "doc": base_limit * 2,
                "sql": max(1, base_limit // 2),
                "qa_pair": max(1, base_limit // 2),
                "domain": base_limit * 2
            }
        else:  # BALANCED
            return {
                "ddl": base_limit,
                "doc": base_limit,
                "sql": base_limit,
                "qa_pair": base_limit,
                "domain": base_limit
            }


class PromptBuilder:
    """提示词构建器"""
    
    def __init__(self, config: RetrievalConfig):
        self.config = config
    
    def build_enhanced_prompt(self, query: str, context: Dict[str, List], 
                            schema_info: str, additional_instructions: str = "") -> str:
        """构建增强的提示词"""
        prompt_parts = [
            "# Text2SQL Generation Task",
            f"Convert the following natural language question to SQL:",
            f"**Question:** {query}",
            "",
            "# Database Schema",
            schema_info,
            ""
        ]
        
        # 添加相关的DDL语句
        if context.get("ddl_statements"):
            prompt_parts.extend([
                "# Relevant Database Definitions",
                "The following DDL statements define the database structure:",
                ""
            ])
            for i, ddl in enumerate(context["ddl_statements"], 1):
                prompt_parts.extend([
                    f"## DDL {i}:",
                    f"```sql",
                    ddl.strip(),
                    f"```",
                    ""
                ])
        
        # 添加高质量的问题-SQL对
        if context.get("qa_pairs"):
            high_quality_pairs = [
                pair for pair in context["qa_pairs"] 
                if pair.get("score", 0) >= 0.8
            ]
            if high_quality_pairs:
                prompt_parts.extend([
                    "# Similar High-Quality Examples",
                    "The following are similar questions with their SQL solutions:",
                    ""
                ])
                for i, pair in enumerate(high_quality_pairs, 1):
                    prompt_parts.extend([
                        f"## Example {i} (Score: {pair.get('score', 0):.2f}):",
                        f"**Question:** {pair['question']}",
                        f"**SQL:**",
                        f"```sql",
                        pair['sql'].strip(),
                        f"```",
                        ""
                    ])
        
        # 添加相似的SQL示例
        if context.get("sql_examples"):
            prompt_parts.extend([
                "# Relevant SQL Patterns",
                "The following SQL examples show relevant query patterns:",
                ""
            ])
            for i, sql in enumerate(context["sql_examples"], 1):
                prompt_parts.extend([
                    f"## Pattern {i}:",
                    f"```sql",
                    sql.strip(),
                    f"```",
                    ""
                ])
        
        # 添加业务文档上下文
        if context.get("documentation"):
            prompt_parts.extend([
                "# Business Context",
                "The following documentation provides business context:",
                ""
            ])
            for i, doc in enumerate(context["documentation"], 1):
                prompt_parts.extend([
                    f"## Context {i}:",
                    doc.strip(),
                    ""
                ])
        
        # 添加领域知识
        if context.get("domain_knowledge"):
            prompt_parts.extend([
                "# Domain Knowledge",
                "The following domain knowledge may be relevant:",
                ""
            ])
            for i, knowledge in enumerate(context["domain_knowledge"], 1):
                prompt_parts.extend([
                    f"## Knowledge {i}:",
                    knowledge.strip(),
                    ""
                ])
        
        # 添加生成指令
        prompt_parts.extend([
            "# Generation Instructions",
            "Based on the above context, generate a SQL query that answers the question.",
            "",
            "**Requirements:**",
            "1. The SQL must be syntactically correct and executable",
            "2. Use appropriate table and column names from the schema",
            "3. Follow SQL best practices and conventions",
            "4. Consider the business context and domain knowledge",
            "5. Ensure the query logic matches the natural language question",
            ""
        ])
        
        if additional_instructions:
            prompt_parts.extend([
                "**Additional Instructions:**",
                additional_instructions,
                ""
            ])
        
        prompt_parts.extend([
            "**Output Format:**",
            "Provide only the SQL query without explanations or comments.",
            "",
            "```sql",
            "-- Your SQL query here",
            "```"
        ])
        
        full_prompt = "\n".join(prompt_parts)
        
        # 检查长度限制
        if len(full_prompt) > self.config.max_context_length:
            return self._truncate_prompt(full_prompt, context)
        
        return full_prompt
    
    def _truncate_prompt(self, prompt: str, context: Dict[str, List]) -> str:
        """截断过长的提示词"""
        # 简化实现：优先保留QA对和SQL示例
        essential_parts = [
            "# Text2SQL Generation Task",
            "# Database Schema", 
            "# Generation Instructions"
        ]
        
        # 重新构建简化版本
        return prompt[:self.config.max_context_length] + "\n\n[Content truncated due to length limit]"


class EnhancedRAGRetriever:
    """增强型RAG检索器，结合Vanna.ai的检索策略和高级功能"""
    
    def __init__(self, config: Optional[RetrievalConfig] = None):
        """Initialize enhanced retriever.
        
        Args:
            config: Retrieval configuration
        """
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.config = config or RetrievalConfig()
        
        self.quality_filter = QualityFilter()
        self.diversity_filter = DiversityFilter()
        self.context_builder = ContextBuilder(self.config)
        self.prompt_builder = PromptBuilder(self.config)
    
    def retrieve_context(self, query: str, db_id: str, 
                        strategy: Optional[RetrievalStrategy] = None,
                        custom_filters: Optional[Dict[str, Any]] = None) -> Dict[str, List]:
        """检索与查询相关的上下文信息
        
        Args:
            query: 用户查询
            db_id: 数据库标识符
            strategy: 检索策略
            custom_filters: 自定义过滤器
            
        Returns:
            Dict: 分类的上下文信息
        """
        # 使用指定策略或默认策略
        current_strategy = strategy or self.config.strategy
        
        # 生成查询向量
        query_embedding = self.embedding_service.generate_embedding(query)
        
        # 多类型检索
        results_by_type = {}
        data_types = ["ddl", "doc", "sql", "qa_pair", "domain"]
        
        for data_type in data_types:
            # 构建过滤器
            search_filter = {"data_type": data_type, "db_id": db_id}
            if custom_filters:
                search_filter.update(custom_filters)
            
            # 执行搜索
            raw_results = self.vector_store.search(
                vector=query_embedding,
                filter=search_filter,
                limit=self.config.max_examples_per_type * 2  # 获取更多结果用于过滤
            )
            
            # 转换为RetrievalResult对象
            retrieval_results = [
                RetrievalResult(
                    id=r.id,
                    content=r.metadata.get("content", ""),
                    score=r.score,
                    data_type=data_type,
                    metadata=r.metadata
                )
                for r in raw_results
            ]
            
            # 应用质量过滤
            if self.config.enable_quality_filter:
                retrieval_results = self.quality_filter.filter_by_similarity(
                    retrieval_results, self.config.similarity_threshold
                )
                retrieval_results = self.quality_filter.filter_by_content_quality(
                    retrieval_results
                )
            
            # 应用多样性过滤
            if self.config.enable_diversity_filter:
                retrieval_results = self.diversity_filter.ensure_diversity(
                    retrieval_results
                )
            
            # 按分数排序
            retrieval_results.sort(key=lambda x: x.score, reverse=True)
            
            results_by_type[data_type] = retrieval_results
        
        # 构建上下文
        return self.context_builder.build_context(results_by_type)
    
    def build_enhanced_prompt(self, query: str, context: Dict[str, List], 
                            schema_info: str, additional_instructions: str = "") -> str:
        """构建增强的提示词，结合检索到的上下文
        
        Args:
            query: 用户查询
            context: 检索到的上下文信息
            schema_info: 数据库模式信息
            additional_instructions: 额外指令
            
        Returns:
            str: 增强的提示词
        """
        return self.prompt_builder.build_enhanced_prompt(
            query, context, schema_info, additional_instructions
        )
    
    def get_retrieval_stats(self, query: str, db_id: str) -> Dict[str, Any]:
        """获取检索统计信息
        
        Args:
            query: 用户查询
            db_id: 数据库标识符
            
        Returns:
            Dict: 检索统计信息
        """
        context = self.retrieve_context(query, db_id)
        
        stats = {
            "query": query,
            "db_id": db_id,
            "strategy": self.config.strategy.value,
            "similarity_threshold": self.config.similarity_threshold,
            "retrieved_counts": {
                "ddl_statements": len(context.get("ddl_statements", [])),
                "documentation": len(context.get("documentation", [])),
                "sql_examples": len(context.get("sql_examples", [])),
                "qa_pairs": len(context.get("qa_pairs", [])),
                "domain_knowledge": len(context.get("domain_knowledge", []))
            },
            "total_retrieved": sum(len(v) if isinstance(v, list) else 0 for v in context.values()),
            "high_quality_qa_pairs": len([
                pair for pair in context.get("qa_pairs", [])
                if pair.get("score", 0) >= 0.8
            ])
        }
        
        return stats
    
    def update_config(self, **kwargs):
        """更新检索配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # 重新初始化依赖配置的组件
        self.context_builder = ContextBuilder(self.config)
        self.prompt_builder = PromptBuilder(self.config)

# Global enhanced RAG retriever instance
enhanced_rag_retriever = EnhancedRAGRetriever()