"""
Unit tests for VannaTrainingService.
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from services.training_service import VannaTrainingService, EnhancedRAGRetriever
from utils.models import TrainingDataType


class TestVannaTrainingService:
    """Test VannaTrainingService functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_vector_store = Mock()
        self.mock_embedding_service = Mock()
        self.mock_embedding_service.generate_embedding.return_value = [0.1, 0.2, 0.3]
        
        self.training_service = VannaTrainingService(
            vector_store=self.mock_vector_store,
            embedding_service=self.mock_embedding_service
        )
    
    def test_train_ddl_success(self):
        """Test successful DDL training."""
        ddl_statements = [
            "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))",
            "CREATE TABLE orders (id INT PRIMARY KEY, user_id INT)"
        ]
        db_id = "test_db"
        
        result = self.training_service.train_ddl(ddl_statements, db_id)
        
        assert result is True
        assert self.mock_vector_store.insert.call_count == 2
        assert self.mock_embedding_service.generate_embedding.call_count == 2
    
    def test_train_documentation_success(self):
        """Test successful documentation training."""
        docs = [
            {"title": "User Guide", "content": "Users table contains customer information"},
            {"title": "Order Guide", "content": "Orders table contains purchase records"}
        ]
        db_id = "test_db"
        
        result = self.training_service.train_documentation(docs, db_id)
        
        assert result is True
        assert self.mock_vector_store.insert.call_count == 2
    
    def test_train_sql_success(self):
        """Test successful SQL training."""
        sql_queries = [
            "SELECT * FROM users WHERE age > 18",
            "SELECT COUNT(*) FROM orders WHERE status = 'completed'"
        ]
        db_id = "test_db"
        
        result = self.training_service.train_sql(sql_queries, db_id)
        
        assert result is True
        assert self.mock_vector_store.insert.call_count == 2
    
    def test_train_qa_pairs_success(self):
        """Test successful QA pairs training."""
        qa_pairs = [
            {"question": "How many users are there?", "sql": "SELECT COUNT(*) FROM users"},
            {"question": "Show all active orders", "sql": "SELECT * FROM orders WHERE status = 'active'"}
        ]
        db_id = "test_db"
        
        result = self.training_service.train_qa_pairs(qa_pairs, db_id)
        
        assert result is True
        assert self.mock_vector_store.insert.call_count == 2
    
    def test_train_domain_knowledge_success(self):
        """Test successful domain knowledge training."""
        knowledge_items = [
            {"content": "Active users are those who logged in within 30 days", "category": "business_rules"},
            {"content": "Order status can be: pending, processing, completed, cancelled", "category": "data_definitions"}
        ]
        db_id = "test_db"
        
        result = self.training_service.train_domain_knowledge(knowledge_items, db_id)
        
        assert result is True
        assert self.mock_vector_store.insert.call_count == 2
    
    def test_auto_train_from_successful_query(self):
        """Test automatic training from successful queries."""
        question = "Show all users"
        sql = "SELECT * FROM users"
        db_id = "test_db"
        
        result = self.training_service.auto_train_from_successful_query(question, sql, db_id)
        
        assert result is True
        assert self.mock_vector_store.insert.call_count == 1
    
    def test_get_training_stats(self):
        """Test getting training statistics."""
        stats = self.training_service.get_training_stats("test_db")
        
        assert "total_training_examples" in stats
        assert "by_type" in stats
        assert "db_id" in stats
    
    def test_extract_table_names_from_ddl(self):
        """Test table name extraction from DDL."""
        ddl = "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))"
        table_names = self.training_service._extract_table_names(ddl)
        
        assert "users" in table_names
    
    def test_extract_table_names_from_sql(self):
        """Test table name extraction from SQL."""
        sql = "SELECT u.name FROM users u JOIN orders o ON u.id = o.user_id"
        table_names = self.training_service._extract_table_names_from_sql(sql)
        
        assert "users" in table_names
        assert "orders" in table_names


class TestEnhancedRAGRetriever:
    """Test EnhancedRAGRetriever functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_vector_store = Mock()
        self.mock_embedding_service = Mock()
        self.mock_embedding_service.generate_embedding.return_value = [0.1, 0.2, 0.3]
        
        self.retriever = EnhancedRAGRetriever(
            vector_store=self.mock_vector_store,
            embedding_service=self.mock_embedding_service
        )
    
    def test_retrieve_context(self):
        """Test context retrieval."""
        # Mock search results
        mock_result = Mock()
        mock_result.metadata = {
            "content": "test content",
            "sql": "SELECT * FROM test",
            "question": "test question"
        }
        self.mock_vector_store.search.return_value = [mock_result]
        
        query = "Show all users"
        db_id = "test_db"
        
        context = self.retriever.retrieve_context(query, db_id)
        
        assert "ddl_statements" in context
        assert "documentation" in context
        assert "sql_examples" in context
        assert "qa_pairs" in context
        assert "domain_knowledge" in context
        
        # Should call search for each data type
        assert self.mock_vector_store.search.call_count == 5
    
    def test_build_enhanced_prompt(self):
        """Test enhanced prompt building."""
        query = "Show all users"
        context = {
            "ddl_statements": ["CREATE TABLE users (id INT, name VARCHAR(100))"],
            "documentation": ["Users table contains customer information"],
            "sql_examples": ["SELECT * FROM users"],
            "qa_pairs": [{"question": "How many users?", "sql": "SELECT COUNT(*) FROM users"}],
            "domain_knowledge": ["Active users logged in within 30 days"]
        }
        schema_info = "Table: users (id, name)"
        
        prompt = self.retriever.build_enhanced_prompt(query, context, schema_info)
        
        assert "Text2SQL Task" in prompt
        assert query in prompt
        assert schema_info in prompt
        assert "CREATE TABLE users" in prompt
        assert "Similar SQL Examples" in prompt
        assert "Similar Question-SQL Pairs" in prompt
        assert "Domain Knowledge" in prompt