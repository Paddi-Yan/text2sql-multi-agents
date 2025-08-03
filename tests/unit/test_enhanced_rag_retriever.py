"""
Unit tests for Enhanced RAG Retriever.
"""
import pytest
from unittest.mock import Mock, MagicMock
from typing import List, Dict, Any

from services.enhanced_rag_retriever import (
    EnhancedRAGRetriever, RetrievalConfig, RetrievalStrategy,
    QualityFilter, DiversityFilter, ContextBuilder, PromptBuilder,
    RetrievalResult
)
from storage.vector_store import SearchResult


class TestQualityFilter:
    """Test QualityFilter functionality."""
    
    def test_filter_by_similarity(self):
        """Test similarity-based filtering."""
        results = [
            RetrievalResult("1", "content1", 0.9, "sql", {}),
            RetrievalResult("2", "content2", 0.6, "sql", {}),
            RetrievalResult("3", "content3", 0.8, "sql", {})
        ]
        
        filtered = QualityFilter.filter_by_similarity(results, threshold=0.7)
        
        assert len(filtered) == 2
        assert filtered[0].score == 0.9
        assert filtered[1].score == 0.8
    
    def test_filter_by_content_quality(self):
        """Test content quality filtering."""
        results = [
            RetrievalResult("1", "SELECT * FROM users", 0.9, "sql", {}),
            RetrievalResult("2", "x", 0.8, "sql", {}),  # Too short
            RetrievalResult("3", "A" * 3000, 0.8, "sql", {}),  # Too long
            RetrievalResult("4", "Valid documentation content", 0.8, "doc", {})
        ]
        
        filtered = QualityFilter.filter_by_content_quality(results)
        
        assert len(filtered) == 2
        assert filtered[0].content == "SELECT * FROM users"
        assert filtered[1].content == "Valid documentation content"
    
    def test_has_sql_errors(self):
        """Test SQL error detection."""
        assert QualityFilter._has_sql_errors("syntax error in query")
        assert QualityFilter._has_sql_errors("invalid syntax")
        assert not QualityFilter._has_sql_errors("SELECT * FROM users")


class TestDiversityFilter:
    """Test DiversityFilter functionality."""
    
    def test_ensure_diversity(self):
        """Test diversity filtering."""
        results = [
            RetrievalResult("1", "SELECT * FROM users", 0.9, "sql", {}),
            RetrievalResult("2", "SELECT * FROM users WHERE id = 1", 0.8, "sql", {}),  # Similar
            RetrievalResult("3", "SELECT COUNT(*) FROM orders", 0.7, "sql", {}),  # Different
        ]
        
        diverse = DiversityFilter.ensure_diversity(results, max_similar=2)
        
        # Should keep diverse results
        assert len(diverse) >= 2
        contents = [r.content for r in diverse]
        assert "SELECT COUNT(*) FROM orders" in contents
    
    def test_are_similar(self):
        """Test similarity detection."""
        result1 = RetrievalResult("1", "SELECT * FROM users", 0.9, "sql", {})
        result2 = RetrievalResult("2", "SELECT * FROM users WHERE id = 1", 0.8, "sql", {})
        result3 = RetrievalResult("3", "SELECT COUNT(*) FROM orders", 0.7, "sql", {})
        
        # These should be considered similar (Jaccard similarity = 0.5)
        assert DiversityFilter._are_similar(result1, result2)
        # These should not be similar
        assert not DiversityFilter._are_similar(result1, result3)


class TestContextBuilder:
    """Test ContextBuilder functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = RetrievalConfig()
        self.builder = ContextBuilder(self.config)
    
    def test_build_context_balanced(self):
        """Test balanced context building."""
        results_by_type = {
            "ddl": [
                RetrievalResult("1", "CREATE TABLE users (id INT)", 0.9, "ddl", {"content": "CREATE TABLE users (id INT)"})
            ],
            "qa_pair": [
                RetrievalResult("2", "Q: How many users? A: SELECT COUNT(*)", 0.8, "qa_pair", {
                    "question": "How many users?",
                    "sql": "SELECT COUNT(*) FROM users"
                })
            ]
        }
        
        context = self.builder.build_context(results_by_type)
        
        assert "ddl_statements" in context
        assert "qa_pairs" in context
        assert len(context["ddl_statements"]) == 1
        assert len(context["qa_pairs"]) == 1
        assert context["qa_pairs"][0]["question"] == "How many users?"
    
    def test_get_type_limits_qa_focused(self):
        """Test QA-focused type limits."""
        self.config.strategy = RetrievalStrategy.QA_FOCUSED
        self.config.max_examples_per_type = 3
        
        limits = self.builder._get_type_limits()
        
        assert limits["qa_pair"] == 6  # 2x base limit
        assert limits["ddl"] == 1      # reduced
        assert limits["sql"] == 3      # base limit


class TestPromptBuilder:
    """Test PromptBuilder functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = RetrievalConfig()
        self.builder = PromptBuilder(self.config)
    
    def test_build_enhanced_prompt(self):
        """Test enhanced prompt building."""
        query = "Show all users"
        context = {
            "ddl_statements": ["CREATE TABLE users (id INT, name VARCHAR(100))"],
            "qa_pairs": [
                {
                    "question": "How many users?",
                    "sql": "SELECT COUNT(*) FROM users",
                    "score": 0.9
                }
            ],
            "sql_examples": ["SELECT * FROM users WHERE active = 1"],
            "documentation": ["Users table contains customer information"],
            "domain_knowledge": ["Active users are those who logged in recently"]
        }
        schema_info = "Table: users (id, name, active)"
        
        prompt = self.builder.build_enhanced_prompt(query, context, schema_info)
        
        assert "Text2SQL Generation Task" in prompt
        assert query in prompt
        assert schema_info in prompt
        assert "CREATE TABLE users" in prompt
        assert "How many users?" in prompt
        assert "SELECT * FROM users WHERE active = 1" in prompt
        assert "Users table contains customer information" in prompt
        assert "Active users are those who logged in recently" in prompt
        assert "Generation Instructions" in prompt
    
    def test_build_enhanced_prompt_with_additional_instructions(self):
        """Test prompt building with additional instructions."""
        query = "Show all users"
        context = {"ddl_statements": [], "qa_pairs": [], "sql_examples": [], "documentation": [], "domain_knowledge": []}
        schema_info = "Table: users (id, name)"
        additional_instructions = "Use LIMIT 10 for performance"
        
        prompt = self.builder.build_enhanced_prompt(query, context, schema_info, additional_instructions)
        
        assert "Additional Instructions:" in prompt
        assert "Use LIMIT 10 for performance" in prompt
    
    def test_truncate_prompt(self):
        """Test prompt truncation."""
        self.config.max_context_length = 100
        
        long_prompt = "A" * 200
        context = {}
        
        truncated = self.builder._truncate_prompt(long_prompt, context)
        
        assert len(truncated) <= 150  # Should be truncated with message
        assert "Content truncated" in truncated


class TestEnhancedRAGRetriever:
    """Test EnhancedRAGRetriever functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_vector_store = Mock()
        self.mock_embedding_service = Mock()
        self.mock_embedding_service.generate_embedding.return_value = [0.1, 0.2, 0.3]
        
        self.config = RetrievalConfig(
            similarity_threshold=0.7,
            max_examples_per_type=3,
            enable_quality_filter=True,
            enable_diversity_filter=True
        )
        
        self.retriever = EnhancedRAGRetriever(
            vector_store=self.mock_vector_store,
            embedding_service=self.mock_embedding_service,
            config=self.config
        )
    
    def test_retrieve_context_with_quality_filter(self):
        """Test context retrieval with quality filtering."""
        # Mock search results
        mock_results = [
            SearchResult(
                id="1",
                score=0.9,
                metadata={
                    "content": "SELECT * FROM users",
                    "data_type": "sql",
                    "sql": "SELECT * FROM users"
                }
            ),
            SearchResult(
                id="2", 
                score=0.5,  # Below threshold
                metadata={
                    "content": "SELECT * FROM orders",
                    "data_type": "sql",
                    "sql": "SELECT * FROM orders"
                }
            )
        ]
        
        self.mock_vector_store.search.return_value = mock_results
        
        context = self.retriever.retrieve_context("Show all users", "test_db")
        
        # Should filter out low-score results
        assert len(context["sql_examples"]) == 1
        assert context["sql_examples"][0] == "SELECT * FROM users"
    
    def test_retrieve_context_with_custom_strategy(self):
        """Test context retrieval with custom strategy."""
        mock_results = [
            SearchResult(
                id="1",
                score=0.9,
                metadata={
                    "content": "Q: How many users? A: SELECT COUNT(*)",
                    "data_type": "qa_pair",
                    "question": "How many users?",
                    "sql": "SELECT COUNT(*) FROM users"
                }
            )
        ]
        
        self.mock_vector_store.search.return_value = mock_results
        
        context = self.retriever.retrieve_context(
            "Show all users", 
            "test_db",
            strategy=RetrievalStrategy.QA_FOCUSED
        )
        
        assert "qa_pairs" in context
        # QA_FOCUSED strategy should prioritize QA pairs
        self.mock_vector_store.search.assert_called()
    
    def test_build_enhanced_prompt(self):
        """Test enhanced prompt building."""
        context = {
            "ddl_statements": ["CREATE TABLE users (id INT)"],
            "qa_pairs": [{"question": "How many users?", "sql": "SELECT COUNT(*)", "score": 0.9}],
            "sql_examples": ["SELECT * FROM users"],
            "documentation": ["Users table info"],
            "domain_knowledge": ["Business rules"]
        }
        
        prompt = self.retriever.build_enhanced_prompt(
            "Show all users",
            context,
            "Table: users (id, name)",
            "Use proper formatting"
        )
        
        assert "Text2SQL Generation Task" in prompt
        assert "Show all users" in prompt
        assert "CREATE TABLE users" in prompt
        assert "How many users?" in prompt
        assert "Use proper formatting" in prompt
    
    def test_get_retrieval_stats(self):
        """Test retrieval statistics."""
        mock_results = [
            SearchResult(
                id="1",
                score=0.9,
                metadata={
                    "content": "Q: How many users? A: SELECT COUNT(*)",
                    "data_type": "qa_pair",
                    "question": "How many users?",
                    "sql": "SELECT COUNT(*) FROM users"
                }
            )
        ]
        
        self.mock_vector_store.search.return_value = mock_results
        
        stats = self.retriever.get_retrieval_stats("Show all users", "test_db")
        
        assert stats["query"] == "Show all users"
        assert stats["db_id"] == "test_db"
        assert "retrieved_counts" in stats
        assert "total_retrieved" in stats
        assert "high_quality_qa_pairs" in stats
    
    def test_update_config(self):
        """Test configuration updates."""
        original_threshold = self.retriever.config.similarity_threshold
        
        self.retriever.update_config(similarity_threshold=0.8)
        
        assert self.retriever.config.similarity_threshold == 0.8
        assert self.retriever.config.similarity_threshold != original_threshold
    
    def test_retrieve_context_with_custom_filters(self):
        """Test context retrieval with custom filters."""
        mock_results = []
        self.mock_vector_store.search.return_value = mock_results
        
        custom_filters = {"category": "business"}
        
        self.retriever.retrieve_context(
            "Show all users",
            "test_db", 
            custom_filters=custom_filters
        )
        
        # Verify custom filters were applied
        calls = self.mock_vector_store.search.call_args_list
        for call in calls:
            filter_arg = call[1]["filter"]
            assert "category" in filter_arg
            assert filter_arg["category"] == "business"
    
    def test_retrieve_context_without_quality_filter(self):
        """Test context retrieval without quality filtering."""
        self.config.enable_quality_filter = False
        
        mock_results = [
            SearchResult(
                id="1",
                score=0.3,  # Very low score
                metadata={
                    "content": "SELECT * FROM users",
                    "data_type": "sql",
                    "sql": "SELECT * FROM users"
                }
            )
        ]
        
        self.mock_vector_store.search.return_value = mock_results
        
        context = self.retriever.retrieve_context("Show all users", "test_db")
        
        # Should include low-score results when quality filter is disabled
        assert len(context["sql_examples"]) == 1
    
    def test_retrieve_context_without_diversity_filter(self):
        """Test context retrieval without diversity filtering."""
        self.config.enable_diversity_filter = False
        
        mock_results = [
            SearchResult(
                id="1",
                score=0.9,
                metadata={
                    "content": "SELECT * FROM users",
                    "data_type": "sql",
                    "sql": "SELECT * FROM users"
                }
            ),
            SearchResult(
                id="2",
                score=0.8,
                metadata={
                    "content": "SELECT * FROM users WHERE id = 1",  # Similar content
                    "data_type": "sql", 
                    "sql": "SELECT * FROM users WHERE id = 1"
                }
            )
        ]
        
        self.mock_vector_store.search.return_value = mock_results
        
        context = self.retriever.retrieve_context("Show all users", "test_db")
        
        # Should include similar results when diversity filter is disabled
        assert len(context["sql_examples"]) == 2