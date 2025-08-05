"""
Decomposer Agent for query decomposition and SQL generation.
Based on MAC-SQL strategy with Chain of Thought (CoT) approach.
"""
import re
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from agents.base_agent import BaseAgent
from utils.models import ChatMessage, AgentResponse
from services.enhanced_rag_retriever import EnhancedRAGRetriever, RetrievalStrategy, RetrievalConfig
from services.llm_service import llm_service
from utils.prompts import (
    get_decomposer_query_decomposition_prompt,
    get_decomposer_simple_sql_prompt,
    get_decomposer_cot_sql_prompt
)


class DatasetType(Enum):
    """支持的数据集类型"""
    BIRD = "bird"
    SPIDER = "spider"
    GENERIC = "generic"


@dataclass
class DecompositionConfig:
    """查询分解配置"""
    max_sub_questions: int = 5
    enable_cot_reasoning: bool = True
    enable_rag_enhancement: bool = True
    dataset_type: DatasetType = DatasetType.GENERIC
    temperature: float = 0.1
    max_tokens: int = 2000


class QueryDecomposer:
    """查询分解器，将复杂查询分解为子问题"""
    
    def __init__(self, config: DecompositionConfig):
        self.config = config
        import logging
        self.logger = logging.getLogger(f"{__name__}.QueryDecomposer")
    
    def decompose_query(self, query: str, schema_info: str, evidence: str = "") -> List[str]:
        """将复杂查询分解为子问题
        
        Args:
            query: 自然语言查询
            schema_info: 数据库模式信息
            evidence: 额外的证据信息
            
        Returns:
            List[str]: 子问题列表
        """
        # 分析查询复杂度
        complexity = self._analyze_query_complexity(query)
        
        if complexity["is_simple"]:
            # 简单查询不需要分解
            return [query]
        
        # 使用LLM进行查询分解
        try:
            # 获取格式化的提示词
            system_prompt, user_prompt = get_decomposer_query_decomposition_prompt(
                query=query,
                schema_info=schema_info,
                evidence=evidence,
                complexity_info=complexity
            )
            
            # 调用LLM服务
            llm_response = llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=self.config.temperature,
                max_tokens=1000
            )
            
            if llm_response.success:
                # 解析LLM响应中的JSON
                json_data = llm_service.extract_json_from_response(llm_response.content)
                
                if json_data and "sub_questions" in json_data:
                    sub_questions = json_data["sub_questions"]
                    # 限制子问题数量
                    return sub_questions[:self.config.max_sub_questions]
            
            # LLM调用失败，返回原始查询作为单一子问题
            self.logger.warning(f"LLM decomposition failed: {llm_response.error}, using simple fallback")
            
        except Exception as e:
            self.logger.warning(f"Error in LLM decomposition: {e}, using simple fallback")
        
        # 后备方案：返回原始查询作为单一子问题
        return [query]
    
    def _analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """分析查询复杂度"""
        query_lower = query.lower()
        
        complexity_indicators = {
            "has_aggregation": any(word in query_lower for word in ["count", "sum", "avg", "average", "max", "min", "total"]),
            "has_grouping": any(word in query_lower for word in ["group by", "each", "per", "by category", "by type"]),
            "has_filtering": any(word in query_lower for word in ["where", "filter", "only", "exclude", "include", "more than", "less than", "greater", "who"]),
            "has_sorting": any(word in query_lower for word in ["order", "sort", "highest", "lowest", "top", "bottom"]),
            "has_joining": any(word in query_lower for word in ["and", "with", "from", "in", "of"]),
            "has_comparison": any(word in query_lower for word in ["more than", "less than", "greater", "smaller", "above", "below", "between"]),
            "has_temporal": any(word in query_lower for word in ["year", "month", "day", "date", "time", "recent", "last", "first"]),
            "has_multiple_entities": len(re.findall(r'\b(?:table|user|customer|order|product|item|person|company|employee)\w*\b', query_lower)) > 1
        }
        
        complexity_score = sum(complexity_indicators.values())
        
        return {
            "score": complexity_score,
            "is_simple": complexity_score <= 2,
            "is_complex": complexity_score >= 4,
            "indicators": complexity_indicators
        }
    



class SQLGenerator:
    """SQL生成器，基于CoT方法生成SQL语句"""
    
    def __init__(self, config: DecompositionConfig):
        self.config = config
        import logging
        self.logger = logging.getLogger(f"{__name__}.SQLGenerator")
    
    def generate_sql_steps(self, sub_questions: List[str], schema_info: str, 
                          fk_info: str, context: Dict[str, List]) -> str:
        """基于子问题生成SQL语句
        
        Args:
            sub_questions: 子问题列表
            schema_info: 数据库模式信息
            fk_info: 外键关系信息
            context: RAG检索的上下文信息
            
        Returns:
            str: 生成的SQL语句
        """
        if len(sub_questions) == 1:
            # 简单查询直接生成
            return self._generate_simple_sql(sub_questions[0], schema_info, fk_info, context)
        
        # 复杂查询使用CoT方法
        return self._generate_cot_sql(sub_questions, schema_info, fk_info, context)
    
    def _generate_simple_sql(self, question: str, schema_info: str, 
                           fk_info: str, context: Dict[str, List]) -> str:
        """生成简单SQL查询"""
        try:
            # 获取格式化的提示词
            system_prompt, user_prompt = get_decomposer_simple_sql_prompt(
                query=question,
                schema_info=schema_info,
                fk_info=fk_info,
                context=context
            )
            
            # 调用LLM服务
            llm_response = llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            if llm_response.success:
                sql = llm_service.extract_sql_from_response(llm_response.content)
                if sql and len(sql.strip()) > 0:
                    return sql
            
            self.logger.warning(f"LLM SQL generation failed: {llm_response.error}, using simple fallback")
            
        except Exception as e:
            self.logger.warning(f"Error in LLM SQL generation: {e}, using simple fallback")
        
        # 后备方案：返回基础SQL
        return "SELECT * FROM table_name LIMIT 10;"
    
    def _generate_cot_sql(self, sub_questions: List[str], schema_info: str, 
                         fk_info: str, context: Dict[str, List]) -> str:
        """使用CoT方法生成复杂SQL查询"""
        try:
            # 重构原始查询
            original_query = " ".join(sub_questions)
            
            # 获取格式化的提示词
            system_prompt, user_prompt = get_decomposer_cot_sql_prompt(
                original_query=original_query,
                sub_questions=sub_questions,
                schema_info=schema_info,
                fk_info=fk_info,
                context=context
            )
            
            # 调用LLM服务
            llm_response = llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            if llm_response.success:
                sql = llm_service.extract_sql_from_response(llm_response.content)
                if sql and len(sql.strip()) > 0:
                    return sql
            
            self.logger.warning(f"LLM CoT SQL generation failed: {llm_response.error}, using simple fallback")
            
        except Exception as e:
            self.logger.warning(f"Error in LLM CoT SQL generation: {e}, using simple fallback")
        
        # 后备方案：返回基础SQL
        return "SELECT * FROM table_name LIMIT 10;"
    



class DecomposerAgent(BaseAgent):
    """Decomposer智能体，负责查询分解和SQL生成"""
    
    def __init__(self, agent_name: str = "Decomposer", dataset_name: str = "generic", 
                 rag_retriever: Optional[EnhancedRAGRetriever] = None, router=None):
        """初始化Decomposer智能体
        
        Args:
            agent_name: 智能体名称
            dataset_name: 数据集名称（bird、spider、generic）
            rag_retriever: RAG检索器
            router: 消息路由器
        """
        super().__init__(agent_name, router)
        
        # 根据数据集类型设置配置
        dataset_type = DatasetType.GENERIC
        if dataset_name.lower() == "bird":
            dataset_type = DatasetType.BIRD
        elif dataset_name.lower() == "spider":
            dataset_type = DatasetType.SPIDER
        
        self.config = DecompositionConfig(dataset_type=dataset_type)
        self.dataset_name = dataset_name
        
        # 初始化组件
        self.query_decomposer = QueryDecomposer(self.config)
        self.sql_generator = SQLGenerator(self.config)
        self.rag_retriever = rag_retriever
        
        # 性能统计
        self.decomposition_stats = {
            "total_queries": 0,
            "simple_queries": 0,
            "complex_queries": 0,
            "avg_sub_questions": 0.0,
            "rag_enhanced_queries": 0
        }
    
    def talk(self, message: ChatMessage) -> AgentResponse:
        """处理查询分解和SQL生成
        
        Args:
            message: 输入消息，包含查询和模式信息
            
        Returns:
            AgentResponse: 包含生成的SQL和分解信息
        """
        if not self._validate_message(message):
            return self._prepare_response(message, success=False, error="Invalid message")
        
        try:
            # 检查必要的输入信息
            if not message.desc_str:
                return self._prepare_response(
                    message, success=False, error="Missing database schema description"
                )
            
            # 步骤1: 查询分解
            sub_questions = self._decompose_query(message.query, message.desc_str, message.evidence)
            
            # 步骤2: RAG增强（如果可用）
            context = {}
            if self.config.enable_rag_enhancement and self.rag_retriever:
                context = self._retrieve_rag_context(message.query, message.db_id)
                self.decomposition_stats["rag_enhanced_queries"] += 1
            
            # 步骤3: SQL生成
            final_sql = self._generate_sql_steps(sub_questions, message.desc_str, message.fk_str, context)
            
            # 步骤4: 构建QA对字符串
            qa_pairs = self._build_qa_pairs_string(sub_questions, final_sql, context)
            
            # 更新消息
            message.final_sql = final_sql
            message.qa_pairs = qa_pairs
            message.send_to = "Refiner"  # 发送给Refiner进行验证
            
            # 更新统计信息
            self._update_decomposition_stats(sub_questions, context)
            
            self.logger.info(f"Query decomposed into {len(sub_questions)} sub-questions")
            self.logger.info(f"Generated SQL: {final_sql[:100]}...")
            
            return self._prepare_response(
                message,
                success=True,
                sub_questions_count=len(sub_questions),
                sub_questions=sub_questions,
                rag_enhanced=bool(context),
                sql_generated=True
            )
            
        except Exception as e:
            self.logger.error(f"Error in query decomposition: {e}")
            return self._prepare_response(message, success=False, error=str(e))
    
    def _decompose_query(self, query: str, schema_info: str, evidence: str = "") -> List[str]:
        """分解查询为子问题"""
        return self.query_decomposer.decompose_query(query, schema_info, evidence)
    
    def _retrieve_rag_context(self, query: str, db_id: str) -> Dict[str, List]:
        """检索RAG上下文信息"""
        if not self.rag_retriever:
            return {}
        
        try:
            # 根据数据集类型选择检索策略
            strategy = RetrievalStrategy.BALANCED
            if self.config.dataset_type == DatasetType.BIRD:
                strategy = RetrievalStrategy.CONTEXT_FOCUSED  # BIRD需要更多业务上下文
            elif self.config.dataset_type == DatasetType.SPIDER:
                strategy = RetrievalStrategy.SQL_FOCUSED  # Spider更注重SQL模式
            
            return self.rag_retriever.retrieve_context(query, db_id, strategy)
        except Exception as e:
            self.logger.warning(f"RAG context retrieval failed: {e}")
            return {}
    
    def _generate_sql_steps(self, sub_questions: List[str], schema_info: str, 
                          fk_info: str, context: Dict[str, List]) -> str:
        """生成SQL语句"""
        return self.sql_generator.generate_sql_steps(sub_questions, schema_info, fk_info, context)
    
    def _build_qa_pairs_string(self, sub_questions: List[str], final_sql: str, 
                             context: Dict[str, List]) -> str:
        """构建QA对字符串用于后续处理"""
        qa_parts = []
        
        # 添加当前查询的分解过程
        qa_parts.append("# Current Query Decomposition")
        for i, sub_q in enumerate(sub_questions, 1):
            qa_parts.append(f"Sub-question {i}: {sub_q}")
        
        qa_parts.append(f"Final SQL: {final_sql}")
        qa_parts.append("")
        
        # 添加相关的历史QA对
        if context.get("qa_pairs"):
            qa_parts.append("# Related Historical Examples")
            for i, pair in enumerate(context["qa_pairs"][:3], 1):
                qa_parts.append(f"Example {i}:")
                qa_parts.append(f"Q: {pair['question']}")
                qa_parts.append(f"A: {pair['sql']}")
                qa_parts.append("")
        
        return "\n".join(qa_parts)
    
    def _update_decomposition_stats(self, sub_questions: List[str], context: Dict[str, List]):
        """更新分解统计信息"""
        self.decomposition_stats["total_queries"] += 1
        
        if len(sub_questions) == 1:
            self.decomposition_stats["simple_queries"] += 1
        else:
            self.decomposition_stats["complex_queries"] += 1
        
        # 更新平均子问题数量
        total_sub_questions = (self.decomposition_stats["avg_sub_questions"] * 
                             (self.decomposition_stats["total_queries"] - 1) + len(sub_questions))
        self.decomposition_stats["avg_sub_questions"] = total_sub_questions / self.decomposition_stats["total_queries"]
    
    def get_decomposition_stats(self) -> Dict[str, Any]:
        """获取分解统计信息"""
        stats = self.decomposition_stats.copy()
        stats.update({
            "dataset_type": self.config.dataset_type.value,
            "rag_enhancement_enabled": self.config.enable_rag_enhancement,
            "cot_reasoning_enabled": self.config.enable_cot_reasoning,
            "rag_enhancement_rate": (
                stats["rag_enhanced_queries"] / stats["total_queries"] 
                if stats["total_queries"] > 0 else 0.0
            )
        })
        return stats
    
    def reset_decomposition_stats(self):
        """重置分解统计信息"""
        self.decomposition_stats = {
            "total_queries": 0,
            "simple_queries": 0,
            "complex_queries": 0,
            "avg_sub_questions": 0.0,
            "rag_enhanced_queries": 0
        }
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # 重新初始化组件
        self.query_decomposer = QueryDecomposer(self.config)
        self.sql_generator = SQLGenerator(self.config)
        
        self.logger.info(f"Configuration updated: {kwargs}")
    
    def set_rag_retriever(self, rag_retriever: EnhancedRAGRetriever):
        """设置RAG检索器"""
        self.rag_retriever = rag_retriever
        self.logger.info("RAG retriever updated")
    
    def get_supported_datasets(self) -> List[str]:
        """获取支持的数据集列表"""
        return [dataset.value for dataset in DatasetType]
    
    def switch_dataset(self, dataset_name: str):
        """切换数据集类型"""
        dataset_name_lower = dataset_name.lower()
        
        if dataset_name_lower == "bird":
            self.config.dataset_type = DatasetType.BIRD
        elif dataset_name_lower == "spider":
            self.config.dataset_type = DatasetType.SPIDER
        else:
            self.config.dataset_type = DatasetType.GENERIC
        
        self.dataset_name = dataset_name
        
        # 重新初始化组件
        self.query_decomposer = QueryDecomposer(self.config)
        self.sql_generator = SQLGenerator(self.config)
        
        self.logger.info(f"Switched to dataset: {dataset_name}")