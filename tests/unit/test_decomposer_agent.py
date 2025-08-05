"""
Unit tests for Decomposer Agent.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List

from agents.decomposer_agent import (
    DecomposerAgent, QueryDecomposer, SQLGenerator, 
    DatasetType, DecompositionConfig
)
from utils.models import ChatMessage, AgentResponse
from services.enhanced_rag_retriever import EnhancedRAGRetriever, RetrievalStrategy
from services.llm_service import LLMResponse


class TestQueryDecomposer:
    """Test QueryDecomposer class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = DecompositionConfig()
        self.decomposer = QueryDecomposer(self.config)
    
    def test_analyze_query_complexity_simple(self):
        """Test complexity analysis for simple queries."""
        simple_query = "Show all users"
        complexity = self.decomposer._analyze_query_complexity(simple_query)
        
        assert complexity["is_simple"] is True
        assert complexity["is_complex"] is False
        assert complexity["score"] <= 2
    
    def test_analyze_query_complexity_complex(self):
        """Test complexity analysis for complex queries."""
        complex_query = "Show the average order amount for each customer who placed more than 5 orders last year, sorted by total amount"
        complexity = self.decomposer._analyze_query_complexity(complex_query)
        
        assert complexity["is_complex"] is True
        assert complexity["score"] >= 4
        assert complexity["indicators"]["has_aggregation"] is True
        assert complexity["indicators"]["has_filtering"] is True
        assert complexity["indicators"]["has_sorting"] is True
    
    def test_decompose_simple_query(self):
        """Test decomposition of simple queries."""
        simple_query = "List all products"
        schema_info = "# Table: products\n[id, name, price]"
        
        sub_questions = self.decomposer.decompose_query(simple_query, schema_info)
        
        assert len(sub_questions) == 1
        assert sub_questions[0] == simple_query
    
    @patch('agents.decomposer_agent.llm_service')
    def test_decompose_complex_query(self, mock_llm_service):
        """Test decomposition of complex queries."""
        # Mock LLM response
        mock_llm_service.decompose_query.return_value = LLMResponse(
            content='{"sub_questions": ["Find products", "Calculate sales", "Group by category"], "reasoning": "Test"}',
            success=True
        )
        mock_llm_service.extract_json_from_response.return_value = {
            "sub_questions": ["Find products", "Calculate sales", "Group by category"]
        }
        
        complex_query = "Show the total sales amount for each product category in 2023"
        schema_info = "# Table: products\n[id, name, category, price]\n# Table: orders\n[id, product_id, quantity, date]"
        
        sub_questions = self.decomposer.decompose_query(complex_query, schema_info)
        
        assert len(sub_questions) == 3
        assert "Find products" in sub_questions
        assert "Calculate sales" in sub_questions
        assert "Group by category" in sub_questions
    
    @patch('utils.prompts.llm_service')
    def test_llm_decompose_aggregation(self, mock_llm_service):
        """Test LLM-based decomposition for aggregation queries."""
        # Mock LLM response
        mock_llm_service.generate_completion.return_value = LLMResponse(
            content='{"sub_questions": ["Find products", "Calculate average price"], "reasoning": "Test"}',
            success=True
        )
        mock_llm_service.extract_json_from_response.return_value = {
            "sub_questions": ["Find products", "Calculate average price"]
        }
        
        query = "Calculate the average price of products"
        schema_info = "# Table: products\n[id, name, price]"
        
        sub_questions = self.decomposer.decompose_query(query, schema_info)
        
        assert len(sub_questions) == 2
        assert "Find products" in sub_questions
        assert "Calculate average price" in sub_questions
    
    @patch('agents.decomposer_agent.llm_service')
    def test_llm_decompose_filtering(self, mock_llm_service):
        """Test LLM-based decomposition for filtering queries."""
        # Mock LLM response
        mock_llm_service.generate_completion.return_value = LLMResponse(
            content='{"sub_questions": ["Show products", "Apply price filter"], "reasoning": "Test"}',
            success=True
        )
        mock_llm_service.extract_json_from_response.return_value = {
            "sub_questions": ["Show products", "Apply price filter"]
        }
        
        query = "Show products where price is greater than 100"
        schema_info = "# Table: products\n[id, name, price]"
        
        sub_questions = self.decomposer.decompose_query(query, schema_info)
        
        assert len(sub_questions) == 2
        assert "Show products" in sub_questions
        assert "Apply price filter" in sub_questions


class TestSQLGenerator:
    """Test SQLGenerator class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = DecompositionConfig()
        self.generator = SQLGenerator(self.config)
    
    @patch('agents.decomposer_agent.llm_service')
    def test_generate_simple_sql(self, mock_llm_service):
        """Test simple SQL generation."""
        # Mock LLM response
        mock_llm_service.generate_completion.return_value = LLMResponse(
            content="SELECT * FROM users;",
            success=True
        )
        mock_llm_service.extract_sql_from_response.return_value = "SELECT * FROM users;"
        
        question = "Show all users"
        schema_info = "# Table: users\n[id, name, email]"
        fk_info = ""
        context = {}
        
        sql = self.generator._generate_simple_sql(question, schema_info, fk_info, context)
        
        assert sql == "SELECT * FROM users;"
        mock_llm_service.generate_completion.assert_called_once()
    
    @patch('agents.decomposer_agent.llm_service')
    def test_generate_cot_sql(self, mock_llm_service):
        """Test CoT SQL generation."""
        # Mock LLM response
        mock_llm_service.generate_completion.return_value = LLMResponse(
            content="SELECT p.name, SUM(s.amount) FROM products p JOIN sales s ON p.id = s.product_id GROUP BY p.name ORDER BY SUM(s.amount) DESC;",
            success=True
        )
        mock_llm_service.extract_sql_from_response.return_value = "SELECT p.name, SUM(s.amount) FROM products p JOIN sales s ON p.id = s.product_id GROUP BY p.name ORDER BY SUM(s.amount) DESC;"
        
        sub_questions = [
            "Find all products",
            "Calculate total sales for each product",
            "Sort by sales amount"
        ]
        schema_info = "# Table: products\n[id, name, price]\n# Table: sales\n[id, product_id, amount]"
        fk_info = "products.id = sales.product_id"
        context = {}
        
        sql = self.generator._generate_cot_sql(sub_questions, schema_info, fk_info, context)
        
        assert "SELECT" in sql
        assert "JOIN" in sql
        assert "GROUP BY" in sql
        assert "ORDER BY" in sql
        mock_llm_service.generate_completion.assert_called_once()
    
    @patch('agents.decomposer_agent.llm_service')
    def test_fallback_sql_generation_count(self, mock_llm_service):
        """Test fallback SQL generation for count queries."""
        # Mock LLM failure
        mock_llm_service.generate_completion.return_value = LLMResponse(
            content="",
            success=False,
            error="API error"
        )
        
        question = "How many users are there?"
        schema_info = "# Table: users\n[id, name, email]"
        fk_info = ""
        context = {}
        
        sql = self.generator._generate_simple_sql(question, schema_info, fk_info, context)
        
        # Should return fallback SQL
        assert "SELECT" in sql.upper()
        assert sql == "SELECT * FROM table_name LIMIT 10;"
    
    @patch('agents.decomposer_agent.llm_service')
    def test_fallback_sql_generation_average(self, mock_llm_service):
        """Test fallback SQL generation for average queries."""
        # Mock LLM failure
        mock_llm_service.generate_completion.return_value = LLMResponse(
            content="",
            success=False,
            error="API error"
        )
        
        question = "What is the average price?"
        schema_info = "# Table: products\n[id, name, price]"
        fk_info = ""
        context = {}
        
        sql = self.generator._generate_simple_sql(question, schema_info, fk_info, context)
        
        # Should return fallback SQL
        assert "SELECT" in sql.upper()
        assert sql == "SELECT * FROM table_name LIMIT 10;"
    
    @patch('agents.decomposer_agent.llm_service')
    def test_fallback_cot_sql_generation(self, mock_llm_service):
        """Test fallback CoT SQL generation."""
        # Mock LLM failure
        mock_llm_service.generate_completion.return_value = LLMResponse(
            content="",
            success=False,
            error="API error"
        )
        
        sub_questions = ["Find users", "Get their orders", "Calculate totals"]
        schema_info = "# Table: users\n[id, name]\n# Table: orders\n[id, user_id, amount]"
        fk_info = ""
        context = {}
        
        sql = self.generator._generate_cot_sql(sub_questions, schema_info, fk_info, context)
        
        # Should return fallback SQL
        assert "SELECT" in sql.upper()
        assert sql == "SELECT * FROM table_name LIMIT 10;"


class TestDecomposerAgent:
    """Test DecomposerAgent class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_rag_retriever = Mock(spec=EnhancedRAGRetriever)
        self.agent = DecomposerAgent(
            agent_name="TestDecomposer",
            dataset_name="generic",
            rag_retriever=self.mock_rag_retriever
        )
    
    def test_initialization(self):
        """Test agent initialization."""
        assert self.agent.agent_name == "TestDecomposer"
        assert self.agent.dataset_name == "generic"
        assert self.agent.config.dataset_type == DatasetType.GENERIC
        assert self.agent.rag_retriever is not None
    
    def test_initialization_bird_dataset(self):
        """Test agent initialization with BIRD dataset."""
        agent = DecomposerAgent(dataset_name="bird")
        
        assert agent.config.dataset_type == DatasetType.BIRD
        assert agent.dataset_name == "bird"
    
    def test_initialization_spider_dataset(self):
        """Test agent initialization with Spider dataset."""
        agent = DecomposerAgent(dataset_name="spider")
        
        assert agent.config.dataset_type == DatasetType.SPIDER
        assert agent.dataset_name == "spider"
    
    def test_talk_success(self):
        """Test successful message processing."""
        # Setup mock RAG retriever
        self.mock_rag_retriever.retrieve_context.return_value = {
            "sql_examples": ["SELECT * FROM users;"],
            "qa_pairs": [{"question": "Show users", "sql": "SELECT * FROM users;", "score": 0.9}]
        }
        
        # Create test message
        message = ChatMessage(
            db_id="test_db",
            query="Show all active users",
            desc_str="# Table: users\n[id, name, email, status]",
            fk_str="",
            evidence="Users with status = 'active'"
        )
        
        # Process message
        response = self.agent.talk(message)
        
        # Verify response
        assert response.success is True
        assert message.final_sql is not None
        assert len(message.final_sql) > 0
        assert message.qa_pairs is not None
        assert message.send_to == "Refiner"
        
        # Verify RAG retriever was called
        self.mock_rag_retriever.retrieve_context.assert_called_once()
    
    def test_talk_missing_schema(self):
        """Test message processing with missing schema."""
        message = ChatMessage(
            db_id="test_db",
            query="Show all users",
            desc_str="",  # Missing schema
            fk_str="",
            evidence=""
        )
        
        response = self.agent.talk(message)
        
        assert response.success is False
        assert "Missing database schema description" in response.error
    
    def test_talk_invalid_message(self):
        """Test message processing with invalid message."""
        message = ChatMessage(
            db_id="",  # Missing db_id
            query="Show all users",
            desc_str="# Table: users\n[id, name]",
            fk_str="",
            evidence=""
        )
        
        response = self.agent.talk(message)
        
        assert response.success is False
        assert "Invalid message" in response.error
    
    def test_talk_without_rag(self):
        """Test message processing without RAG retriever."""
        agent = DecomposerAgent(rag_retriever=None)
        
        message = ChatMessage(
            db_id="test_db",
            query="Show all users",
            desc_str="# Table: users\n[id, name, email]",
            fk_str="",
            evidence=""
        )
        
        response = agent.talk(message)
        
        assert response.success is True
        assert message.final_sql is not None
        assert message.qa_pairs is not None
    
    def test_retrieve_rag_context_balanced_strategy(self):
        """Test RAG context retrieval with balanced strategy."""
        self.mock_rag_retriever.retrieve_context.return_value = {"sql_examples": []}
        
        context = self.agent._retrieve_rag_context("test query", "test_db")
        
        self.mock_rag_retriever.retrieve_context.assert_called_once_with(
            "test query", "test_db", RetrievalStrategy.BALANCED
        )
    
    def test_retrieve_rag_context_bird_strategy(self):
        """Test RAG context retrieval with BIRD dataset strategy."""
        agent = DecomposerAgent(dataset_name="bird", rag_retriever=self.mock_rag_retriever)
        self.mock_rag_retriever.retrieve_context.return_value = {"documentation": []}
        
        context = agent._retrieve_rag_context("test query", "test_db")
        
        self.mock_rag_retriever.retrieve_context.assert_called_once_with(
            "test query", "test_db", RetrievalStrategy.CONTEXT_FOCUSED
        )
    
    def test_retrieve_rag_context_spider_strategy(self):
        """Test RAG context retrieval with Spider dataset strategy."""
        agent = DecomposerAgent(dataset_name="spider", rag_retriever=self.mock_rag_retriever)
        self.mock_rag_retriever.retrieve_context.return_value = {"sql_examples": []}
        
        context = agent._retrieve_rag_context("test query", "test_db")
        
        self.mock_rag_retriever.retrieve_context.assert_called_once_with(
            "test query", "test_db", RetrievalStrategy.SQL_FOCUSED
        )
    
    def test_retrieve_rag_context_failure(self):
        """Test RAG context retrieval failure handling."""
        self.mock_rag_retriever.retrieve_context.side_effect = Exception("RAG error")
        
        context = self.agent._retrieve_rag_context("test query", "test_db")
        
        assert context == {}
    
    def test_build_qa_pairs_string(self):
        """Test QA pairs string building."""
        sub_questions = ["Find users", "Filter active users"]
        final_sql = "SELECT * FROM users WHERE status = 'active';"
        context = {
            "qa_pairs": [
                {"question": "Show users", "sql": "SELECT * FROM users;", "score": 0.9}
            ]
        }
        
        qa_string = self.agent._build_qa_pairs_string(sub_questions, final_sql, context)
        
        assert "Current Query Decomposition" in qa_string
        assert "Find users" in qa_string
        assert "Filter active users" in qa_string
        assert final_sql in qa_string
        assert "Related Historical Examples" in qa_string
        assert "Show users" in qa_string
    
    def test_update_decomposition_stats(self):
        """Test decomposition statistics update."""
        initial_stats = self.agent.get_decomposition_stats()
        assert initial_stats["total_queries"] == 0
        
        # Update with simple query
        self.agent._update_decomposition_stats(["single question"], {})
        stats = self.agent.get_decomposition_stats()
        
        assert stats["total_queries"] == 1
        assert stats["simple_queries"] == 1
        assert stats["complex_queries"] == 0
        assert stats["avg_sub_questions"] == 1.0
        
        # Update with complex query
        self.agent._update_decomposition_stats(["q1", "q2", "q3"], {})
        stats = self.agent.get_decomposition_stats()
        
        assert stats["total_queries"] == 2
        assert stats["simple_queries"] == 1
        assert stats["complex_queries"] == 1
        assert stats["avg_sub_questions"] == 2.0
    
    def test_get_decomposition_stats(self):
        """Test getting decomposition statistics."""
        stats = self.agent.get_decomposition_stats()
        
        assert "total_queries" in stats
        assert "simple_queries" in stats
        assert "complex_queries" in stats
        assert "avg_sub_questions" in stats
        assert "rag_enhanced_queries" in stats
        assert "dataset_type" in stats
        assert "rag_enhancement_enabled" in stats
        assert "cot_reasoning_enabled" in stats
        assert "rag_enhancement_rate" in stats
        
        assert stats["dataset_type"] == "generic"
        assert stats["rag_enhancement_enabled"] is True
        assert stats["cot_reasoning_enabled"] is True
    
    def test_reset_decomposition_stats(self):
        """Test resetting decomposition statistics."""
        # Add some stats
        self.agent._update_decomposition_stats(["q1", "q2"], {})
        assert self.agent.get_decomposition_stats()["total_queries"] == 1
        
        # Reset stats
        self.agent.reset_decomposition_stats()
        stats = self.agent.get_decomposition_stats()
        
        assert stats["total_queries"] == 0
        assert stats["simple_queries"] == 0
        assert stats["complex_queries"] == 0
        assert stats["avg_sub_questions"] == 0.0
        assert stats["rag_enhanced_queries"] == 0
    
    def test_update_config(self):
        """Test configuration update."""
        original_max_sub = self.agent.config.max_sub_questions
        
        self.agent.update_config(max_sub_questions=10, enable_cot_reasoning=False)
        
        assert self.agent.config.max_sub_questions == 10
        assert self.agent.config.enable_cot_reasoning is False
        assert self.agent.config.max_sub_questions != original_max_sub
    
    def test_set_rag_retriever(self):
        """Test setting RAG retriever."""
        new_retriever = Mock(spec=EnhancedRAGRetriever)
        
        self.agent.set_rag_retriever(new_retriever)
        
        assert self.agent.rag_retriever is new_retriever
    
    def test_get_supported_datasets(self):
        """Test getting supported datasets."""
        datasets = self.agent.get_supported_datasets()
        
        assert "bird" in datasets
        assert "spider" in datasets
        assert "generic" in datasets
        assert len(datasets) == 3
    
    def test_switch_dataset_bird(self):
        """Test switching to BIRD dataset."""
        self.agent.switch_dataset("bird")
        
        assert self.agent.config.dataset_type == DatasetType.BIRD
        assert self.agent.dataset_name == "bird"
    
    def test_switch_dataset_spider(self):
        """Test switching to Spider dataset."""
        self.agent.switch_dataset("spider")
        
        assert self.agent.config.dataset_type == DatasetType.SPIDER
        assert self.agent.dataset_name == "spider"
    
    def test_switch_dataset_generic(self):
        """Test switching to generic dataset."""
        self.agent.switch_dataset("unknown")
        
        assert self.agent.config.dataset_type == DatasetType.GENERIC
        assert self.agent.dataset_name == "unknown"
    
    def test_switch_dataset_case_insensitive(self):
        """Test dataset switching is case insensitive."""
        self.agent.switch_dataset("BIRD")
        assert self.agent.config.dataset_type == DatasetType.BIRD
        
        self.agent.switch_dataset("Spider")
        assert self.agent.config.dataset_type == DatasetType.SPIDER


class TestDecomposerAgentIntegration:
    """Integration tests for DecomposerAgent."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.agent = DecomposerAgent()
    
    def test_end_to_end_simple_query(self):
        """Test end-to-end processing of simple query."""
        message = ChatMessage(
            db_id="test_db",
            query="List all products",
            desc_str="# Table: products\n[id, name, price, category]",
            fk_str="",
            evidence=""
        )
        
        response = self.agent.talk(message)
        
        assert response.success is True
        assert message.final_sql is not None
        assert "SELECT" in message.final_sql.upper()
        assert message.send_to == "Refiner"
        assert response.metadata["sub_questions_count"] >= 1
    
    def test_end_to_end_complex_query(self):
        """Test end-to-end processing of complex query."""
        message = ChatMessage(
            db_id="test_db",
            query="Show the average order amount for each customer category, sorted by amount",
            desc_str="""# Table: customers
[id, name, email, category]
# Table: orders
[id, customer_id, amount, date]""",
            fk_str="customers.id = orders.customer_id",
            evidence="Focus on active customers only"
        )
        
        response = self.agent.talk(message)
        
        assert response.success is True
        assert message.final_sql is not None
        assert "SELECT" in message.final_sql.upper()
        assert message.qa_pairs is not None
        assert "Current Query Decomposition" in message.qa_pairs
        assert response.metadata["sub_questions_count"] >= 1
    
    def test_performance_stats_tracking(self):
        """Test performance statistics tracking."""
        # Process simple query
        simple_message = ChatMessage(
            db_id="test_db",
            query="Show users",
            desc_str="# Table: users\n[id, name]",
            fk_str="",
            evidence=""
        )
        
        self.agent.talk(simple_message)
        
        # Process complex query
        complex_message = ChatMessage(
            db_id="test_db",
            query="Calculate average sales by region and month",
            desc_str="# Table: sales\n[id, amount, region, date]",
            fk_str="",
            evidence=""
        )
        
        self.agent.talk(complex_message)
        
        # Check stats
        stats = self.agent.get_decomposition_stats()
        assert stats["total_queries"] == 2
        assert stats["simple_queries"] >= 1
        assert stats["avg_sub_questions"] > 0


if __name__ == "__main__":
    pytest.main([__file__])