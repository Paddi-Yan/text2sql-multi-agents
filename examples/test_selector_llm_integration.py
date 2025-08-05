"""
Test Selector Agent LLM integration.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.selector_agent import SelectorAgent
from utils.models import ChatMessage
from utils.prompts import get_selector_schema_analysis_prompt, get_selector_pruning_prompt


def test_selector_schema_analysis():
    """Test LLM-based schema analysis."""
    print("=== Testing Selector Schema Analysis ===\n")
    
    # Test prompt generation
    system_prompt, user_prompt = get_selector_schema_analysis_prompt(
        db_id="test_db",
        schema_info="""# Table: customers
[
  (id, INTEGER, Customer unique identifier),
  (name, VARCHAR, Customer full name),
  (email, VARCHAR, Customer email address),
  (category, VARCHAR, Customer category)
]

# Table: orders
[
  (id, INTEGER, Order unique identifier),
  (customer_id, INTEGER, Reference to customer),
  (amount, DECIMAL, Order total amount),
  (order_date, DATE, Date order was placed)
]""",
        table_count=2,
        total_columns=8,
        avg_columns=4.0
    )
    
    print("System Prompt:")
    print(system_prompt[:200] + "...")
    print("\nUser Prompt:")
    print(user_prompt[:300] + "...")
    print()


def test_selector_schema_pruning():
    """Test LLM-based schema pruning."""
    print("=== Testing Selector Schema Pruning ===\n")
    
    # Test prompt generation
    system_prompt, user_prompt = get_selector_pruning_prompt(
        query="Show total sales by customer category",
        schema_info="""# Table: customers
[
  (id, INTEGER, Customer unique identifier),
  (name, VARCHAR, Customer full name),
  (email, VARCHAR, Customer email address),
  (category, VARCHAR, Customer category),
  (registration_date, DATE, Date customer registered),
  (phone, VARCHAR, Customer phone number),
  (address, VARCHAR, Customer address),
  (status, VARCHAR, Customer status)
]

# Table: orders
[
  (id, INTEGER, Order unique identifier),
  (customer_id, INTEGER, Reference to customer),
  (amount, DECIMAL, Order total amount),
  (order_date, DATE, Date order was placed),
  (status, VARCHAR, Order status),
  (shipping_address, VARCHAR, Shipping address),
  (notes, TEXT, Order notes)
]""",
        fk_info="customers.id = orders.customer_id",
        evidence="Focus on completed orders only"
    )
    
    print("System Prompt:")
    print(system_prompt[:200] + "...")
    print("\nUser Prompt:")
    print(user_prompt[:400] + "...")
    print()


def test_selector_agent_integration():
    """Test Selector Agent with LLM integration."""
    print("=== Testing Selector Agent Integration ===\n")
    
    agent = SelectorAgent(agent_name="LLMSelector")
    
    # Create test message
    message = ChatMessage(
        db_id="test_db",
        query="Find customers with high order values in the premium category",
        evidence="Premium customers have category = 'Premium' and high value means > $1000"
    )
    
    print(f"Input Query: {message.query}")
    print(f"Evidence: {message.evidence}")
    print("Processing with LLM-based Selector...")
    
    # Note: This would require actual database connection for full testing
    # For now, we'll just test the prompt generation
    
    # Test schema analysis prompt
    try:
        system_prompt, user_prompt = get_selector_schema_analysis_prompt(
            db_id=message.db_id,
            schema_info="Sample schema",
            table_count=5,
            total_columns=25,
            avg_columns=5.0
        )
        print(f"\n✅ Schema analysis prompt generated successfully")
        print(f"System prompt length: {len(system_prompt)} characters")
        print(f"User prompt length: {len(user_prompt)} characters")
    except Exception as e:
        print(f"❌ Schema analysis prompt generation failed: {e}")
    
    # Test schema pruning prompt
    try:
        system_prompt, user_prompt = get_selector_pruning_prompt(
            query=message.query,
            schema_info="Sample schema",
            fk_info="Sample FK info",
            evidence=message.evidence
        )
        print(f"\n✅ Schema pruning prompt generated successfully")
        print(f"System prompt length: {len(system_prompt)} characters")
        print(f"User prompt length: {len(user_prompt)} characters")
    except Exception as e:
        print(f"❌ Schema pruning prompt generation failed: {e}")


def test_prompt_parameter_validation():
    """Test prompt parameter validation."""
    print("\n=== Testing Prompt Parameter Validation ===\n")
    
    # Test missing parameters
    try:
        get_selector_schema_analysis_prompt(
            db_id="test_db",
            schema_info="schema",
            # Missing table_count, total_columns, avg_columns
        )
        print("❌ Should have failed with missing parameters")
    except Exception as e:
        print(f"✅ Correctly caught missing parameters: {type(e).__name__}")
    
    # Test valid parameters
    try:
        system_prompt, user_prompt = get_selector_schema_analysis_prompt(
            db_id="test_db",
            schema_info="schema",
            table_count=3,
            total_columns=15,
            avg_columns=5.0
        )
        print("✅ Valid parameters accepted")
    except Exception as e:
        print(f"❌ Valid parameters rejected: {e}")


def main():
    """Run all Selector LLM integration tests."""
    print("Selector Agent LLM Integration Tests")
    print("=" * 50)
    
    try:
        test_selector_schema_analysis()
        test_selector_schema_pruning()
        test_selector_agent_integration()
        test_prompt_parameter_validation()
        
        print("=" * 50)
        print("All Selector LLM integration tests completed!")
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()