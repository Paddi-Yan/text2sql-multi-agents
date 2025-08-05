"""
Unit tests for LLM Service.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from services.llm_service import LLMService, LLMResponse, llm_service


class TestLLMResponse:
    """Test LLMResponse dataclass."""
    
    def test_llm_response_creation(self):
        """Test LLMResponse creation."""
        response = LLMResponse(
            content="Test content",
            success=True,
            error=None,
            usage={"tokens": 100},
            model="test-model"
        )
        
        assert response.content == "Test content"
        assert response.success is True
        assert response.error is None
        assert response.usage == {"tokens": 100}
        assert response.model == "test-model"
    
    def test_llm_response_error(self):
        """Test LLMResponse with error."""
        response = LLMResponse(
            content="",
            success=False,
            error="API error"
        )
        
        assert response.content == ""
        assert response.success is False
        assert response.error == "API error"


class TestLLMService:
    """Test LLMService class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.llm_service = LLMService(
            model_name="test-model",
            api_key="test-key",
            base_url="https://test.api.com"
        )
    
    @patch('services.llm_service.OpenAI')
    def test_initialization(self, mock_openai):
        """Test LLM service initialization."""
        service = LLMService(
            model_name="gpt-4",
            api_key="test-key",
            base_url="https://api.openai.com"
        )
        
        assert service.model_name == "gpt-4"
        assert service.api_key == "test-key"
        assert service.base_url == "https://api.openai.com"
        mock_openai.assert_called_once()
    
    @patch('services.llm_service.OpenAI')
    def test_initialization_with_env_vars(self, mock_openai):
        """Test initialization with environment variables."""
        with patch.dict('os.environ', {
            'OPENAI_MODEL_NAME': 'env-model',
            'OPENAI_API_KEY': 'env-key',
            'OPENAI_BASE_URL': 'https://env.api.com'
        }):
            service = LLMService()
            
            assert service.model_name == "env-model"
            assert service.api_key == "env-key"
            assert service.base_url == "https://env.api.com"
    
    def test_generate_completion_success(self):
        """Test successful completion generation."""
        # Mock OpenAI client response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.model_dump.return_value = {"total_tokens": 50}
        
        self.llm_service.client.chat.completions.create = Mock(return_value=mock_response)
        
        response = self.llm_service.generate_completion(
            prompt="Test prompt",
            temperature=0.1,
            max_tokens=100
        )
        
        assert response.success is True
        assert response.content == "Test response"
        assert response.usage == {"total_tokens": 50}
        assert response.model == "test-model"
    
    def test_generate_completion_failure(self):
        """Test completion generation failure."""
        self.llm_service.client.chat.completions.create = Mock(
            side_effect=Exception("API error")
        )
        
        response = self.llm_service.generate_completion("Test prompt")
        
        assert response.success is False
        assert response.content == ""
        assert response.error == "API error"
    
    def test_decompose_query_success(self):
        """Test successful query decomposition."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"sub_questions": ["Q1", "Q2"], "reasoning": "Test"}'
        mock_response.usage.model_dump.return_value = {"total_tokens": 100}
        
        self.llm_service.client.chat.completions.create = Mock(return_value=mock_response)
        
        response = self.llm_service.decompose_query(
            query="Complex query",
            schema_info="Schema info",
            evidence="Evidence"
        )
        
        assert response.success is True
        assert "sub_questions" in response.content
        assert "reasoning" in response.content
    
    def test_generate_sql_simple(self):
        """Test simple SQL generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "SELECT * FROM users;"
        mock_response.usage.model_dump.return_value = {"total_tokens": 50}
        
        self.llm_service.client.chat.completions.create = Mock(return_value=mock_response)
        
        response = self.llm_service.generate_sql(
            query="Show all users",
            sub_questions=["Show all users"],
            schema_info="# Table: users\n[id, name, email]",
            use_cot=False
        )
        
        assert response.success is True
        assert "SELECT" in response.content
    
    def test_generate_sql_cot(self):
        """Test CoT SQL generation."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name;"
        mock_response.usage.model_dump.return_value = {"total_tokens": 100}
        
        self.llm_service.client.chat.completions.create = Mock(return_value=mock_response)
        
        response = self.llm_service.generate_sql(
            query="Show user order counts",
            sub_questions=["Find users", "Count orders", "Join and group"],
            schema_info="# Table: users\n[id, name]\n# Table: orders\n[id, user_id]",
            use_cot=True
        )
        
        assert response.success is True
        assert "SELECT" in response.content
        assert "JOIN" in response.content
    
    def test_extract_json_from_response_valid(self):
        """Test JSON extraction from valid response."""
        response_content = 'Here is the JSON: {"key": "value", "number": 42}'
        
        result = self.llm_service.extract_json_from_response(response_content)
        
        assert result == {"key": "value", "number": 42}
    
    def test_extract_json_from_response_invalid(self):
        """Test JSON extraction from invalid response."""
        response_content = "This is not JSON content"
        
        result = self.llm_service.extract_json_from_response(response_content)
        
        assert result is None
    
    def test_extract_json_from_response_pure_json(self):
        """Test JSON extraction from pure JSON response."""
        response_content = '{"sub_questions": ["Q1", "Q2"], "reasoning": "Test"}'
        
        result = self.llm_service.extract_json_from_response(response_content)
        
        assert result == {"sub_questions": ["Q1", "Q2"], "reasoning": "Test"}
    
    def test_extract_sql_from_response_with_markdown(self):
        """Test SQL extraction with markdown formatting."""
        response_content = """```sql
SELECT * FROM users
WHERE age > 18;
```"""
        
        result = self.llm_service.extract_sql_from_response(response_content)
        
        assert result == "SELECT * FROM users WHERE age > 18;"
    
    def test_extract_sql_from_response_plain(self):
        """Test SQL extraction from plain response."""
        response_content = "SELECT name, email FROM customers ORDER BY name;"
        
        result = self.llm_service.extract_sql_from_response(response_content)
        
        assert result == "SELECT name, email FROM customers ORDER BY name;"
    
    def test_extract_sql_from_response_with_comments(self):
        """Test SQL extraction with comments."""
        response_content = """```sql
-- This query selects all users
SELECT * FROM users;
-- End of query
```"""
        
        result = self.llm_service.extract_sql_from_response(response_content)
        
        assert result == "SELECT * FROM users;"
        assert "--" not in result
    
    def test_extract_sql_from_response_multiline(self):
        """Test SQL extraction from multiline response."""
        response_content = """```sql
SELECT u.name, 
       COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.name
ORDER BY order_count DESC;
```"""
        
        result = self.llm_service.extract_sql_from_response(response_content)
        
        assert "SELECT" in result
        assert "FROM users u" in result
        assert "LEFT JOIN orders o" in result
        assert "GROUP BY u.name" in result


class TestGlobalLLMService:
    """Test global LLM service instance."""
    
    def test_global_service_exists(self):
        """Test that global service instance exists."""
        assert llm_service is not None
        assert isinstance(llm_service, LLMService)
    
    def test_global_service_methods(self):
        """Test that global service has required methods."""
        assert hasattr(llm_service, 'generate_completion')
        assert hasattr(llm_service, 'decompose_query')
        assert hasattr(llm_service, 'generate_sql')
        assert hasattr(llm_service, 'extract_json_from_response')
        assert hasattr(llm_service, 'extract_sql_from_response')


class TestLLMServiceIntegration:
    """Integration tests for LLM service."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.service = LLMService(model_name="test-model")
    
    def test_decompose_query_with_complexity(self):
        """Test query decomposition with complexity information."""
        complexity_info = {
            "score": 5,
            "indicators": {
                "has_aggregation": True,
                "has_filtering": True,
                "has_sorting": True
            }
        }
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"sub_questions": ["Filter data", "Aggregate results", "Sort output"], "reasoning": "Complex query needs step-by-step approach"}'
        mock_response.usage.model_dump.return_value = {"total_tokens": 150}
        
        self.service.client.chat.completions.create = Mock(return_value=mock_response)
        
        response = self.service.decompose_query(
            query="Show average sales by category, sorted by amount",
            schema_info="# Table: sales\n[id, category, amount]",
            evidence="Focus on last quarter",
            complexity_info=complexity_info
        )
        
        assert response.success is True
        assert "sub_questions" in response.content
        
        # Verify the prompt includes complexity information
        call_args = self.service.client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        user_message = next(msg for msg in messages if msg['role'] == 'user')
        
        assert "Complexity score: 5/8" in user_message['content']
        assert "Has Aggregation" in user_message['content']
        assert "Has Filtering" in user_message['content']
    
    def test_generate_sql_with_context(self):
        """Test SQL generation with RAG context."""
        context = {
            "sql_examples": [
                "SELECT category, AVG(amount) FROM sales GROUP BY category;",
                "SELECT * FROM products WHERE price > 100;"
            ],
            "qa_pairs": [
                {
                    "question": "What is the average sales by category?",
                    "sql": "SELECT category, AVG(amount) FROM sales GROUP BY category;",
                    "score": 0.9
                }
            ]
        }
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "SELECT category, AVG(amount) as avg_sales FROM sales GROUP BY category ORDER BY avg_sales DESC;"
        mock_response.usage.model_dump.return_value = {"total_tokens": 80}
        
        self.service.client.chat.completions.create = Mock(return_value=mock_response)
        
        response = self.service.generate_sql(
            query="Show average sales by category",
            sub_questions=["Show average sales by category"],
            schema_info="# Table: sales\n[id, category, amount]",
            context=context,
            use_cot=False
        )
        
        assert response.success is True
        assert "SELECT" in response.content
        
        # Verify the prompt includes context
        call_args = self.service.client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        user_message = next(msg for msg in messages if msg['role'] == 'user')
        
        assert "Similar SQL Examples" in user_message['content']
        assert "Similar Question-SQL Pairs" in user_message['content']


if __name__ == "__main__":
    pytest.main([__file__])