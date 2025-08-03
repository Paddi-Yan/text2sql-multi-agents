"""
Unit tests for data models.
"""
import pytest
from datetime import datetime
from utils.models import (
    ChatMessage, DatabaseInfo, SQLExecutionResult, 
    MemoryRecord, RetryPolicy, SystemMetrics
)


class TestChatMessage:
    """Test ChatMessage data model."""
    
    def test_chat_message_creation(self):
        """Test ChatMessage can be created with required fields."""
        message = ChatMessage(
            db_id="test_db",
            query="SELECT * FROM users"
        )
        
        assert message.db_id == "test_db"
        assert message.query == "SELECT * FROM users"
        assert message.evidence == ""
        assert message.send_to == "System"
        assert message.pruned is False
    
    def test_chat_message_with_optional_fields(self):
        """Test ChatMessage with optional fields."""
        message = ChatMessage(
            db_id="test_db",
            query="SELECT * FROM users",
            evidence="User table contains customer data",
            final_sql="SELECT id, name FROM users",
            send_to="Refiner"
        )
        
        assert message.evidence == "User table contains customer data"
        assert message.final_sql == "SELECT id, name FROM users"
        assert message.send_to == "Refiner"


class TestSQLExecutionResult:
    """Test SQLExecutionResult data model."""
    
    def test_sql_execution_result_success(self):
        """Test successful SQL execution result."""
        result = SQLExecutionResult(
            sql="SELECT COUNT(*) FROM users",
            data=[(10,)],
            execution_time=0.05,
            is_successful=True
        )
        
        assert result.sql == "SELECT COUNT(*) FROM users"
        assert result.data == [(10,)]
        assert result.execution_time == 0.05
        assert result.is_successful is True
        assert result.sqlite_error == ""
    
    def test_sql_execution_result_error(self):
        """Test failed SQL execution result."""
        result = SQLExecutionResult(
            sql="SELECT * FROM nonexistent_table",
            sqlite_error="no such table: nonexistent_table",
            exception_class="OperationalError",
            is_successful=False
        )
        
        assert result.is_successful is False
        assert "nonexistent_table" in result.sqlite_error
        assert result.exception_class == "OperationalError"


class TestRetryPolicy:
    """Test RetryPolicy data model."""
    
    def test_retry_policy_defaults(self):
        """Test retry policy default values."""
        policy = RetryPolicy()
        
        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.exponential_base == 2.0
        assert policy.jitter is True
    
    def test_calculate_delay(self):
        """Test delay calculation."""
        policy = RetryPolicy(jitter=False)
        
        assert policy.calculate_delay(0) == 1.0
        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(2) == 4.0
        assert policy.calculate_delay(10) == 60.0  # max_delay cap


class TestSystemMetrics:
    """Test SystemMetrics data model."""
    
    def test_system_metrics_defaults(self):
        """Test system metrics default values."""
        metrics = SystemMetrics()
        
        assert metrics.query_count == 0
        assert metrics.successful_queries == 0
        assert metrics.failed_queries == 0
        assert metrics.success_rate == 0.0
        assert metrics.error_rate == 0.0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = SystemMetrics(
            query_count=100,
            successful_queries=85,
            failed_queries=15
        )
        
        assert metrics.success_rate == 0.85
        assert metrics.error_rate == 0.15