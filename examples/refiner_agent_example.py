"""
Example usage of Refiner agent for SQL execution validation and error correction.

This example demonstrates:
1. Basic SQL validation and execution
2. Security validation and injection prevention
3. Error detection and SQL refinement
4. Integration with other agents
5. Performance monitoring and statistics
"""
import os
import sys
import sqlite3
import tempfile
from unittest.mock import Mock

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.refiner_agent import RefinerAgent, SQLSecurityValidator
from utils.models import ChatMessage, SQLExecutionResult
from services.llm_service import LLMService
from storage.mysql_adapter import MySQLAdapter


def create_test_database():
    """Create a test SQLite database for demonstration."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.sqlite")
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER,
                email TEXT,
                department_id INTEGER
            )
        """)
        
        # Create departments table
        cursor.execute("""
            CREATE TABLE departments (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                budget REAL
            )
        """)
        
        # Insert sample data
        cursor.execute("""
            INSERT INTO users (name, age, email, department_id) VALUES 
            ('Alice Johnson', 28, 'alice@company.com', 1),
            ('Bob Smith', 32, 'bob@company.com', 2),
            ('Charlie Brown', 25, 'charlie@company.com', 1),
            ('Diana Prince', 30, 'diana@company.com', 3),
            ('Eve Wilson', 27, 'eve@company.com', 2)
        """)
        
        cursor.execute("""
            INSERT INTO departments (name, budget) VALUES 
            ('Engineering', 500000.0),
            ('Marketing', 200000.0),
            ('Sales', 300000.0)
        """)
        
        conn.commit()
    
    return temp_dir, db_path


def demonstrate_security_validation():
    """Demonstrate SQL security validation."""
    print("=== SQL Security Validation Demo ===\n")
    
    validator = SQLSecurityValidator()
    
    test_queries = [
        ("Safe SELECT query", "SELECT name, age FROM users WHERE age > 25"),
        ("SQL Injection attempt", "SELECT * FROM users WHERE id = 1 OR 1=1"),
        ("DROP table attack", "SELECT * FROM users; DROP TABLE users;"),
        ("UNION SELECT attack", "SELECT name FROM users UNION SELECT password FROM admin"),
        ("Non-SELECT query", "INSERT INTO users (name) VALUES ('hacker')"),
        ("Suspicious function", "SELECT SLEEP(10) FROM users"),
        ("Safe WITH clause", "WITH young_users AS (SELECT * FROM users WHERE age < 30) SELECT * FROM young_users")
    ]
    
    for description, sql in test_queries:
        print(f"Testing: {description}")
        print(f"SQL: {sql}")
        
        result = validator.validate_sql(sql)
        
        print(f"Safe: {result.is_safe}")
        print(f"Risk Level: {result.risk_level.value}")
        if result.detected_pattern:
            print(f"Detected Pattern: {result.detected_pattern}")
        if result.error:
            print(f"Error: {result.error}")
        if result.recommendations:
            print(f"Recommendations: {', '.join(result.recommendations)}")
        
        print("-" * 50)


def demonstrate_sql_execution():
    """Demonstrate SQL execution and validation."""
    print("\n=== SQL Execution Demo ===\n")
    
    temp_dir, db_path = create_test_database()
    
    try:
        # Create mock LLM service
        mock_llm = Mock()
        mock_llm.generate_response = Mock()
        
        # Create Refiner agent
        refiner = RefinerAgent(
            data_path=temp_dir,
            dataset_name="demo"
        )
        
        print(f"Created Refiner agent: {refiner.agent_name}")
        print(f"Database path: {db_path}")
        print()
        
        # Test cases
        test_cases = [
            {
                "description": "Valid SQL query with LLM validation",
                "message": ChatMessage(
                    db_id="test",
                    query="Get all users with their ages",
                    final_sql="SELECT name, age FROM users",
                    desc_str="users table with columns: id, name, age, email, department_id"
                ),
                "expected_success": True,
                "llm_validation_response": '{"is_valid": true, "suggestions": ["Query looks good"]}'
            },
            {
                "description": "SQL with syntax error",
                "message": ChatMessage(
                    db_id="test",
                    query="Get all users",
                    final_sql="SELECT * FORM users",  # FORM instead of FROM
                    desc_str="users table with columns: id, name, age, email, department_id"
                ),
                "expected_success": False,
                "llm_response": "SELECT * FROM users"
            },
            {
                "description": "Query with non-existent table",
                "message": ChatMessage(
                    db_id="test",
                    query="Get all products",
                    final_sql="SELECT * FROM products",
                    desc_str="Available tables: users, departments"
                ),
                "expected_success": False,
                "llm_response": "SELECT * FROM users"
            },
            {
                "description": "Query with non-existent column",
                "message": ChatMessage(
                    db_id="test",
                    query="Get user salaries",
                    final_sql="SELECT name, salary FROM users",
                    desc_str="users table columns: id, name, age, email, department_id"
                ),
                "expected_success": False,
                "llm_response": "SELECT name, age FROM users"
            },
            {
                "description": "Security violation - SQL injection",
                "message": ChatMessage(
                    db_id="test",
                    query="Malicious query",
                    final_sql="SELECT * FROM users WHERE id = 1 OR 1=1",
                    desc_str="users table"
                ),
                "expected_success": False
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"{i}. {test_case['description']}")
            print(f"   Query: {test_case['message'].query}")
            print(f"   SQL: {test_case['message'].final_sql}")
            
            # Set up LLM mock responses
            if "llm_validation_response" in test_case and "llm_response" in test_case:
                # Both validation and refinement responses
                mock_llm.generate_response.side_effect = [
                    test_case["llm_validation_response"],
                    test_case["llm_response"]
                ]
            elif "llm_validation_response" in test_case:
                # Only validation response
                mock_llm.generate_response.return_value = test_case["llm_validation_response"]
            elif "llm_response" in test_case:
                # Only refinement response (validation will be called first)
                mock_llm.generate_response.side_effect = [
                    '{"is_valid": true}',  # Default validation response
                    test_case["llm_response"]
                ]
            
            # Process message
            response = refiner.talk(test_case["message"])
            
            print(f"   Success: {response.success}")
            if response.error:
                print(f"   Error: {response.error}")
            
            if response.message.execution_result:
                exec_result = response.message.execution_result
                print(f"   Execution Time: {exec_result.get('execution_time', 0):.3f}s")
                if exec_result.get('data'):
                    print(f"   Result Rows: {len(exec_result['data'])}")
            
            if response.message.fixed:
                print(f"   SQL was refined: {response.message.final_sql}")
            
            print(f"   Next Agent: {response.message.send_to}")
            print()
        
        # Show agent statistics
        print("=== Agent Statistics ===")
        stats = refiner.get_stats()
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"{key}: {value:.3f}")
            else:
                print(f"{key}: {value}")
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)


def demonstrate_agent_integration():
    """Demonstrate integration with other agents."""
    print("\n=== Agent Integration Demo ===\n")
    
    temp_dir, db_path = create_test_database()
    
    try:
        # Mock other agents
        class MockSelectorAgent:
            def __init__(self):
                self.agent_name = "Selector"
            
            def talk(self, message):
                print(f"  Selector: Analyzing schema for query: {message.query[:50]}...")
                message.desc_str = "users(id, name, age, email, department_id), departments(id, name, budget)"
                message.fk_str = "users.department_id -> departments.id"
                message.send_to = "Decomposer"
                return Mock(success=True, message=message)
        
        class MockDecomposerAgent:
            def __init__(self):
                self.agent_name = "Decomposer"
            
            def talk(self, message):
                print(f"  Decomposer: Generating SQL for: {message.query[:50]}...")
                message.final_sql = "SELECT u.name, d.name as department FROM users u JOIN departments d ON u.department_id = d.id"
                message.qa_pairs = f"Q: {message.query}\nA: {message.final_sql}"
                message.send_to = "Refiner"
                return Mock(success=True, message=message)
        
        # Create agents
        selector = MockSelectorAgent()
        decomposer = MockDecomposerAgent()
        
        refiner = RefinerAgent(
            data_path=temp_dir,
            dataset_name="integration_demo"
        )
        
        print("Created agent pipeline: Selector -> Decomposer -> Refiner")
        print()
        
        # Simulate multi-agent workflow
        message = ChatMessage(
            db_id="test",
            query="Show me all users with their department names",
            evidence="Need to join users and departments tables"
        )
        
        print("1. Initial message:")
        print(f"   Query: {message.query}")
        print(f"   Evidence: {message.evidence}")
        print()
        
        print("2. Processing through agent pipeline:")
        
        # Selector processing
        selector_response = selector.talk(message)
        print(f"   Schema info: {message.desc_str}")
        print(f"   FK info: {message.fk_str}")
        print()
        
        # Decomposer processing
        decomposer_response = decomposer.talk(message)
        print(f"   Generated SQL: {message.final_sql}")
        print()
        
        # Refiner processing
        print("  Refiner: Validating and executing SQL...")
        refiner_response = refiner.talk(message)
        
        print(f"   Validation Success: {refiner_response.success}")
        if refiner_response.message.execution_result:
            exec_result = refiner_response.message.execution_result
            print(f"   Execution Time: {exec_result.get('execution_time', 0):.3f}s")
            if exec_result.get('data'):
                print(f"   Result Rows: {len(exec_result['data'])}")
                print("   Sample Results:")
                for row in exec_result['data'][:3]:
                    print(f"     {row}")
        
        print(f"   Final Status: {message.send_to}")
        print()
        
        print("3. Workflow completed successfully!")
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)


def demonstrate_mysql_integration():
    """Demonstrate MySQL adapter integration."""
    print("\n=== MySQL Integration Demo ===\n")
    
    # Create mock MySQL adapter
    class MockMySQLAdapter:
        def __init__(self):
            self.query_count = 0
        
        def execute_query(self, query):
            self.query_count += 1
            print(f"  MySQL: Executing query #{self.query_count}")
            print(f"  SQL: {query}")
            
            # Simulate different responses based on query
            if "users" in query.lower():
                return [
                    {"id": 1, "name": "Alice", "age": 28, "email": "alice@company.com"},
                    {"id": 2, "name": "Bob", "age": 32, "email": "bob@company.com"},
                    {"id": 3, "name": "Charlie", "age": 25, "email": "charlie@company.com"}
                ]
            elif "departments" in query.lower():
                return [
                    {"id": 1, "name": "Engineering", "budget": 500000.0},
                    {"id": 2, "name": "Marketing", "budget": 200000.0}
                ]
            else:
                raise Exception("Table not found")
    
    mock_mysql = MockMySQLAdapter()
    mock_llm = Mock()
    mock_llm.generate_response = Mock()
    mock_llm.generate_response.return_value = '{"is_valid": true}'
    
    # Create Refiner with MySQL adapter
    refiner = RefinerAgent(
        data_path="/tmp",  # Not used with MySQL
        dataset_name="mysql_demo",
        mysql_adapter=mock_mysql
    )
    
    print("Created Refiner agent with MySQL adapter")
    print()
    
    # Test queries
    test_queries = [
        ("Get all users", "SELECT * FROM users"),
        ("Get departments", "SELECT name, budget FROM departments"),
        ("Invalid table", "SELECT * FROM products")
    ]
    
    for description, sql in test_queries:
        print(f"Testing: {description}")
        
        message = ChatMessage(
            db_id="production",
            query=description,
            final_sql=sql,
            desc_str="Production database schema"
        )
        
        response = refiner.talk(message)
        
        print(f"  Success: {response.success}")
        if response.message.execution_result:
            exec_result = response.message.execution_result
            if exec_result.get('data'):
                print(f"  Rows returned: {len(exec_result['data'])}")
            if exec_result.get('sqlite_error'):
                print(f"  Error: {exec_result['sqlite_error']}")
        
        print()


def main():
    """Run all demonstrations."""
    print("Refiner Agent Demonstration")
    print("=" * 50)
    
    try:
        demonstrate_security_validation()
        demonstrate_sql_execution()
        demonstrate_agent_integration()
        demonstrate_mysql_integration()
        
        print("\n" + "=" * 50)
        print("All demonstrations completed successfully!")
        
    except Exception as e:
        print(f"Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()