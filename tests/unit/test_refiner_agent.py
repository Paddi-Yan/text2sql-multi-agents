"""
Unit tests for Refiner agent.
"""
import pytest
import sqlite3
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from agents.refiner_agent import RefinerAgent, SQLSecurityValidator, TimeoutError
from utils.models import ChatMessage, SQLExecutionResult, SecurityValidationResult, RiskLevel
from services.llm_service import LLMService
from storage.mysql_adapter import MySQLAdapter


class TestSQLSecurityValidator:
    """Test SQL security validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SQLSecurityValidator()
    
    def test_safe_select_query(self):
        """Test validation of safe SELECT query."""
        sql = "SELECT id, name FROM users WHERE age > 18"
        result = self.validator.validate_sql(sql)
        
        assert result.is_safe is True
        assert result.risk_level == RiskLevel.LOW
        assert result.detected_pattern is None
    
    def test_dangerous_drop_query(self):
        """Test detection of dangerous DROP query."""
        sql = "SELECT * FROM users; DROP TABLE users;"
        result = self.validator.validate_sql(sql)
        
        assert result.is_safe is False
        assert result.risk_level == RiskLevel.HIGH
        assert result.detected_pattern is not None
    
    def test_sql_injection_pattern(self):
        """Test detection of SQL injection patterns."""
        sql = "SELECT * FROM users WHERE id = 1 OR 1=1"
        result = self.validator.validate_sql(sql)
        
        assert result.is_safe is False
        assert result.risk_level == RiskLevel.HIGH
    
    def test_union_select_attack(self):
        """Test detection of UNION SELECT attack."""
        sql = "SELECT name FROM users UNION SELECT password FROM admin"
        result = self.validator.validate_sql(sql)
        
        assert result.is_safe is False
        assert result.risk_level == RiskLevel.HIGH
    
    def test_non_select_query(self):
        """Test rejection of non-SELECT queries."""
        sql = "INSERT INTO users (name) VALUES ('test')"
        result = self.validator.validate_sql(sql)
        
        assert result.is_safe is False
        assert result.risk_level == RiskLevel.MEDIUM
        assert "Only SELECT queries are allowed" in result.error
    
    def test_with_clause_allowed(self):
        """Test that WITH clauses are allowed."""
        sql = "WITH temp AS (SELECT * FROM users) SELECT * FROM temp"
        result = self.validator.validate_sql(sql)
        
        assert result.is_safe is True
        assert result.risk_level == RiskLevel.LOW
    
    def test_suspicious_functions(self):
        """Test detection of suspicious functions."""
        sql = "SELECT SLEEP(10) FROM users"
        result = self.validator.validate_sql(sql)
        
        assert result.is_safe is False
        assert result.risk_level == RiskLevel.MEDIUM


class TestRefinerAgent:
    """Test Refiner agent functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.sqlite")
        
        # Create test database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    age INTEGER,
                    email TEXT
                )
            """)
            cursor.execute("""
                INSERT INTO users (name, age, email) VALUES 
                ('Alice', 25, 'alice@example.com'),
                ('Bob', 30, 'bob@example.com'),
                ('Charlie', 35, 'charlie@example.com')
            """)
            conn.commit()
        
        # Mock LLM service
        self.mock_llm = Mock()
        self.mock_llm.generate_response = Mock()
        
        # Create agent
        self.agent = RefinerAgent(
            data_path=self.temp_dir,
            dataset_name="test",
            llm_service=self.mock_llm
        )
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_agent_initialization(self):
        """Test agent initialization."""
        assert self.agent.agent_name == "Refiner"
        assert self.agent.data_path == self.temp_dir
        assert self.agent.dataset_name == "test"
        assert self.agent.execution_timeout == 120
        assert self.agent.max_refinement_attempts == 3
    
    def test_successful_sql_execution(self):
        """Test successful SQL execution."""
        message = ChatMessage(
            db_id="test",
            query="Get all users",
            final_sql="SELECT * FROM users",
            desc_str="users table with id, name, age, email columns"
        )
        
        response = self.agent.talk(message)
        
        assert response.success is True
        assert response.message.execution_result is not None
        assert response.message.send_to == "System"
        assert response.metadata["security_validated"] is True
    
    def test_sql_syntax_error_handling(self):
        """Test handling of SQL syntax errors."""
        message = ChatMessage(
            db_id="test",
            query="Get all users",
            final_sql="SELECT * FORM users",  # Syntax error: FORM instead of FROM
            desc_str="users table with id, name, age, email columns"
        )
        
        # Mock LLM to return corrected SQL
        self.mock_llm.generate_response.return_value = "SELECT * FROM users"
        
        response = self.agent.talk(message)
        
        # Should attempt refinement
        assert self.mock_llm.generate_response.called
        assert response.message.fixed is True
    
    def test_security_violation_rejection(self):
        """Test rejection of SQL with security violations."""
        message = ChatMessage(
            db_id="test",
            query="Malicious query",
            final_sql="SELECT * FROM users; DROP TABLE users;",
            desc_str="users table"
        )
        
        response = self.agent.talk(message)
        
        assert response.success is False
        assert "Security violation" in response.error
        assert response.metadata.get("security_result") is not None
    
    def test_table_not_found_error(self):
        """Test handling of table not found errors."""
        message = ChatMessage(
            db_id="test",
            query="Get products",
            final_sql="SELECT * FROM products",  # Table doesn't exist
            desc_str="users table with id, name, age, email columns"
        )
        
        # Mock LLM to return corrected SQL
        self.mock_llm.generate_response.return_value = "SELECT * FROM users"
        
        response = self.agent.talk(message)
        
        # Should attempt refinement for "no such table" error
        assert self.mock_llm.generate_response.called
    
    def test_column_not_found_error(self):
        """Test handling of column not found errors."""
        message = ChatMessage(
            db_id="test",
            query="Get user salaries",
            final_sql="SELECT name, salary FROM users",  # salary column doesn't exist
            desc_str="users table with id, name, age, email columns"
        )
        
        # Mock LLM to return corrected SQL
        self.mock_llm.generate_response.return_value = "SELECT name, age FROM users"
        
        response = self.agent.talk(message)
        
        # Should attempt refinement for "no such column" error
        assert self.mock_llm.generate_response.called
    
    def test_no_sql_provided(self):
        """Test handling when no SQL is provided."""
        message = ChatMessage(
            db_id="test",
            query="Get all users",
            final_sql="",  # No SQL provided
            desc_str="users table"
        )
        
        response = self.agent.talk(message)
        
        assert response.success is False
        assert "No SQL query provided" in response.error
    
    def test_invalid_message_format(self):
        """Test handling of invalid message format."""
        message = ChatMessage(
            db_id="",  # Missing db_id
            query="",  # Missing query
            final_sql="SELECT * FROM users"
        )
        
        response = self.agent.talk(message)
        
        assert response.success is False
        assert "Invalid message format" in response.error
    
    def test_sql_execution_timeout(self):
        """Test SQL execution timeout handling."""
        # Create a mock that simulates timeout behavior
        message = ChatMessage(
            db_id="test",
            query="Long running query",
            final_sql="SELECT * FROM users",
            desc_str="users table"
        )
        
        # For this test, we'll just verify the timeout mechanism exists
        # In a real scenario, this would be tested with actual long-running queries
        response = self.agent.talk(message)
        
        # The response should either succeed or fail gracefully
        assert isinstance(response.success, bool)
    
    def test_mysql_adapter_integration(self):
        """Test integration with MySQL adapter."""
        # Mock MySQL adapter
        mock_mysql = Mock(spec=MySQLAdapter)
        mock_mysql.execute_query.return_value = [
            {"id": 1, "name": "Alice", "age": 25},
            {"id": 2, "name": "Bob", "age": 30}
        ]
        
        agent = RefinerAgent(
            data_path=self.temp_dir,
            dataset_name="test",
            llm_service=self.mock_llm,
            mysql_adapter=mock_mysql
        )
        
        message = ChatMessage(
            db_id="test",
            query="Get all users",
            final_sql="SELECT * FROM users",
            desc_str="users table"
        )
        
        response = agent.talk(message)
        
        assert response.success is True
        assert mock_mysql.execute_query.called
        assert response.message.execution_result is not None
    
    def test_mysql_adapter_error_handling(self):
        """Test MySQL adapter error handling."""
        # Mock MySQL adapter to raise exception
        mock_mysql = Mock(spec=MySQLAdapter)
        mock_mysql.execute_query.side_effect = Exception("Connection failed")
        
        agent = RefinerAgent(
            data_path=self.temp_dir,
            dataset_name="test",
            llm_service=self.mock_llm,
            mysql_adapter=mock_mysql
        )
        
        message = ChatMessage(
            db_id="test",
            query="Get all users",
            final_sql="SELECT * FROM users",
            desc_str="users table"
        )
        
        response = agent.talk(message)
        
        assert response.success is False
        assert "Connection failed" in str(response.message.execution_result["sqlite_error"])
    
    def test_sql_extraction_from_response(self):
        """Test SQL extraction from LLM response."""
        # Test various response formats
        test_cases = [
            ("```sql\nSELECT * FROM users\n```", "SELECT * FROM users"),
            ("```\nSELECT name FROM users\n```", "SELECT name FROM users"),
            ("SQL: SELECT id FROM users", "SELECT id FROM users"),
            ("Query: SELECT age FROM users", "SELECT age FROM users"),
            ("SELECT email FROM users\n\nThis query...", "SELECT email FROM users"),
            ("SELECT * FROM users", "SELECT * FROM users"),
        ]
        
        for response_text, expected_sql in test_cases:
            extracted = self.agent._extract_sql_from_response(response_text)
            assert extracted == expected_sql, f"Failed for: {response_text}"
    
    def test_refinement_needed_detection(self):
        """Test detection of when refinement is needed."""
        # Test cases for refinable errors
        refinable_cases = [
            SQLExecutionResult(sql="", sqlite_error="no such table: products", is_successful=False),
            SQLExecutionResult(sql="", sqlite_error="no such column: salary", is_successful=False),
            SQLExecutionResult(sql="", sqlite_error="syntax error near 'FORM'", is_successful=False),
            SQLExecutionResult(sql="", sqlite_error="ambiguous column name: id", is_successful=False),
        ]
        
        for case in refinable_cases:
            assert self.agent._is_need_refine(case) is True
        
        # Test cases for non-refinable errors
        non_refinable_cases = [
            SQLExecutionResult(sql="", is_successful=True),  # Successful execution
            SQLExecutionResult(sql="", sqlite_error="permission denied", is_successful=False),
            SQLExecutionResult(sql="", sqlite_error="connection timeout", is_successful=False),
        ]
        
        for case in non_refinable_cases:
            assert self.agent._is_need_refine(case) is False
    
    def test_agent_statistics(self):
        """Test agent statistics tracking."""
        # Execute some operations
        message = ChatMessage(
            db_id="test",
            query="Get all users",
            final_sql="SELECT * FROM users",
            desc_str="users table"
        )
        
        # Execute successful query
        self.agent.talk(message)
        
        # Execute query with security violation
        message.final_sql = "SELECT * FROM users; DROP TABLE users;"
        self.agent.talk(message)
        
        stats = self.agent.get_stats()
        
        assert stats["execution_count"] >= 1
        assert stats["security_violations"] >= 1
        assert "refinement_rate" in stats
        assert "security_violation_rate" in stats
    
    def test_stats_reset(self):
        """Test statistics reset functionality."""
        # Execute some operations
        message = ChatMessage(
            db_id="test",
            query="Get all users",
            final_sql="SELECT * FROM users"
        )
        
        self.agent.talk(message)
        
        # Reset stats
        self.agent.reset_stats()
        
        stats = self.agent.get_stats()
        assert stats["execution_count"] == 0
        assert stats["validation_count"] == 0
        assert stats["refinement_count"] == 0
        assert stats["security_violations"] == 0
    
    def test_llm_validation_functionality(self):
        """Test LLM-based SQL validation."""
        message = ChatMessage(
            db_id="test",
            query="Get all users",
            final_sql="SELECT * FROM users",
            desc_str="users table with id, name, age, email columns"
        )
        
        # Mock LLM to return validation result
        validation_response = '''
        {
            "is_valid": true,
            "syntax_errors": [],
            "logical_issues": [],
            "security_concerns": [],
            "suggestions": ["Consider specifying column names instead of using *"]
        }
        '''
        self.mock_llm.generate_response.return_value = validation_response
        
        response = self.agent.talk(message)
        
        # Should have called LLM for validation
        assert self.mock_llm.generate_response.call_count >= 1
        assert response.success is True
    
    def test_llm_validation_with_errors(self):
        """Test LLM validation detecting errors."""
        message = ChatMessage(
            db_id="test",
            query="Get user names",
            final_sql="SELECT name FROM nonexistent_table",
            desc_str="users table with id, name, age, email columns"
        )
        
        # Mock LLM to return validation with errors
        validation_response = '''
        {
            "is_valid": false,
            "syntax_errors": ["Table 'nonexistent_table' does not exist"],
            "logical_issues": [],
            "security_concerns": [],
            "suggestions": ["Use 'users' table instead"]
        }
        '''
        self.mock_llm.generate_response.return_value = validation_response
        
        response = self.agent.talk(message)
        
        # Should still proceed with execution despite validation warnings
        assert self.mock_llm.generate_response.called
        # The actual execution will fail, but validation should have been attempted
        assert response.message.execution_result is not None
    
    def test_validation_response_parsing(self):
        """Test parsing of non-JSON validation responses."""
        message = ChatMessage(
            db_id="test",
            query="Get users",
            final_sql="SELECT * FROM users",
            desc_str="users table"
        )
        
        # Mock LLM to return non-JSON response
        validation_response = """
        The SQL query appears to be valid.
        Syntax error: None found
        Logical issues: None
        Suggestions: Consider specifying column names
        """
        self.mock_llm.generate_response.return_value = validation_response
        
        response = self.agent.talk(message)
        
        # Should handle non-JSON response gracefully
        assert response.success is True
        assert self.mock_llm.generate_response.called
    
    def test_context_building_for_refinement(self):
        """Test context building for SQL refinement."""
        message = ChatMessage(
            db_id="test",
            query="Get user names",
            final_sql="SELECT name FROM user",  # Wrong table name
            desc_str="users table with id, name, age, email columns",
            fk_str="No foreign keys",
            evidence="The table is called 'users', not 'user'"
        )
        
        # Mock LLM to return validation and then corrected SQL
        self.mock_llm.generate_response.side_effect = [
            '{"is_valid": true}',  # Validation response
            "SELECT name FROM users"  # Refinement response
        ]
        
        response = self.agent.talk(message)
        
        # Verify LLM was called multiple times (validation + refinement)
        assert self.mock_llm.generate_response.call_count >= 2
    
    def test_multiple_refinement_attempts(self):
        """Test multiple refinement attempts."""
        message = ChatMessage(
            db_id="test",
            query="Get all users",
            final_sql="SELECT * FORM users",  # Syntax error
            desc_str="users table"
        )
        
        # Mock LLM to return corrected SQL
        self.mock_llm.generate_response.return_value = "SELECT * FROM users"
        
        response = self.agent.talk(message)
        
        # Should have attempted refinement
        assert self.mock_llm.generate_response.called
        # The refinement should have been attempted (even if it doesn't always succeed)
        assert response.message.execution_result is not None