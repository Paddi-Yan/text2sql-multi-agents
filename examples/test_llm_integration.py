"""
Test LLM integration with Decomposer Agent.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.decomposer_agent import DecomposerAgent
from utils.models import ChatMessage
from services.llm_service import llm_service


def test_llm_service():
    """Test basic LLM service functionality."""
    print("=== Testing LLM Service ===\n")
    
    # Test simple completion
    response = llm_service.generate_completion(
        prompt="What is 2+2?",
        temperature=0.1,
        max_tokens=100
    )
    
    print(f"LLM Service Test:")
    print(f"Success: {response.success}")
    print(f"Content: {response.content}")
    print(f"Model: {response.model}")
    if response.error:
        print(f"Error: {response.error}")
    print()


def test_query_decomposition():
    """Test query decomposition with LLM."""
    print("=== Testing Query Decomposition ===\n")
    
    query = "Show the average order amount for each customer category, sorted by total amount"
    schema_info = """# Table: customers
[
  (id, INTEGER, Customer unique identifier),
  (name, VARCHAR, Customer full name),
  (category, VARCHAR, Customer category: Premium, Standard, Basic)
]

# Table: orders
[
  (id, INTEGER, Order unique identifier),
  (customer_id, INTEGER, Reference to customer),
  (amount, DECIMAL, Order total amount),
  (order_date, DATE, Date order was placed)
]"""
    
    response = llm_service.decompose_query(
        query=query,
        schema_info=schema_info,
        evidence="Focus on active customers only"
    )
    
    print(f"Query Decomposition Test:")
    print(f"Original Query: {query}")
    print(f"Success: {response.success}")
    print(f"Response: {response.content}")
    
    if response.success:
        json_data = llm_service.extract_json_from_response(response.content)
        if json_data:
            print(f"Sub-questions: {json_data.get('sub_questions', [])}")
            print(f"Reasoning: {json_data.get('reasoning', 'N/A')}")
    
    if response.error:
        print(f"Error: {response.error}")
    print()


def test_sql_generation():
    """Test SQL generation with LLM."""
    print("=== Testing SQL Generation ===\n")
    
    query = "Show all customers with their total order amounts"
    schema_info = """# Table: customers
[
  (id, INTEGER, Customer unique identifier),
  (name, VARCHAR, Customer full name),
  (email, VARCHAR, Customer email address)
]

# Table: orders
[
  (id, INTEGER, Order unique identifier),
  (customer_id, INTEGER, Reference to customer),
  (amount, DECIMAL, Order total amount)
]"""
    
    fk_info = "customers.id = orders.customer_id"
    
    response = llm_service.generate_sql(
        query=query,
        sub_questions=[query],
        schema_info=schema_info,
        fk_info=fk_info,
        use_cot=False
    )
    
    print(f"SQL Generation Test:")
    print(f"Query: {query}")
    print(f"Success: {response.success}")
    
    if response.success:
        sql = llm_service.extract_sql_from_response(response.content)
        print(f"Generated SQL: {sql}")
    
    if response.error:
        print(f"Error: {response.error}")
    print()


def test_decomposer_agent_with_llm():
    """Test Decomposer Agent with LLM integration."""
    print("=== Testing Decomposer Agent with LLM ===\n")
    
    agent = DecomposerAgent(agent_name="LLMDecomposer", dataset_name="generic")
    
    message = ChatMessage(
        db_id="test_db",
        query="Find the top 5 customers by total order value in the last year",
        desc_str="""# Table: customers
[
  (id, INTEGER, Customer unique identifier),
  (name, VARCHAR, Customer full name),
  (email, VARCHAR, Customer email address),
  (registration_date, DATE, Date customer registered)
]

# Table: orders
[
  (id, INTEGER, Order unique identifier),
  (customer_id, INTEGER, Reference to customer),
  (amount, DECIMAL, Order total amount),
  (order_date, DATE, Date order was placed),
  (status, VARCHAR, Order status)
]""",
        fk_str="customers.id = orders.customer_id",
        evidence="Consider only completed orders (status = 'completed')"
    )
    
    print(f"Input Query: {message.query}")
    print("Processing with LLM...")
    
    response = agent.talk(message)
    
    print(f"\nDecomposer Agent Test:")
    print(f"Success: {response.success}")
    
    if response.success:
        print(f"Generated SQL: {message.final_sql}")
        print(f"Next Agent: {message.send_to}")
        print(f"Sub-questions Count: {response.metadata.get('sub_questions_count', 0)}")
        
        if message.qa_pairs:
            print(f"\nQA Pairs Preview:")
            print(message.qa_pairs[:300] + "..." if len(message.qa_pairs) > 300 else message.qa_pairs)
    else:
        print(f"Error: {response.error}")
    
    # Show statistics
    stats = agent.get_decomposition_stats()
    print(f"\nAgent Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def test_complex_query_with_cot():
    """Test complex query with Chain of Thought."""
    print("\n=== Testing Complex Query with CoT ===\n")
    
    agent = DecomposerAgent(agent_name="CoTDecomposer", dataset_name="bird")
    
    message = ChatMessage(
        db_id="ecommerce_db",
        query="What is the monthly growth rate of premium customer orders compared to the previous year?",
        desc_str="""# Table: customers
[
  (id, INTEGER, Customer unique identifier),
  (name, VARCHAR, Customer full name),
  (category, VARCHAR, Customer category: Premium, Standard, Basic),
  (registration_date, DATE, Date customer registered)
]

# Table: orders
[
  (id, INTEGER, Order unique identifier),
  (customer_id, INTEGER, Reference to customer),
  (amount, DECIMAL, Order total amount),
  (order_date, DATE, Date order was placed),
  (status, VARCHAR, Order status)
]""",
        fk_str="customers.id = orders.customer_id",
        evidence="Premium customers have category = 'Premium'. Compare current year with previous year monthly data."
    )
    
    print(f"Complex Query: {message.query}")
    print("Processing with CoT approach...")
    
    response = agent.talk(message)
    
    print(f"\nComplex Query Test:")
    print(f"Success: {response.success}")
    
    if response.success:
        print(f"Generated SQL: {message.final_sql}")
        print(f"Sub-questions: {response.metadata.get('sub_questions', [])}")
        print(f"Used CoT: {len(response.metadata.get('sub_questions', [])) > 1}")
    else:
        print(f"Error: {response.error}")


def main():
    """Run all LLM integration tests."""
    print("LLM Integration Tests")
    print("=" * 50)
    
    try:
        test_llm_service()
        test_query_decomposition()
        test_sql_generation()
        test_decomposer_agent_with_llm()
        test_complex_query_with_cot()
        
        print("=" * 50)
        print("All LLM integration tests completed!")
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()