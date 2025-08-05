"""
Example usage of Decomposer Agent for Text2SQL query decomposition and SQL generation.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.decomposer_agent import DecomposerAgent, DatasetType, DecompositionConfig
from agents.base_agent import MessageRouter
from utils.models import ChatMessage
from services.enhanced_rag_retriever import EnhancedRAGRetriever, RetrievalConfig
from unittest.mock import Mock


def create_mock_rag_retriever():
    """Create a mock RAG retriever for demonstration."""
    mock_retriever = Mock(spec=EnhancedRAGRetriever)
    
    # Mock context data
    mock_context = {
        "ddl_statements": [
            "CREATE TABLE customers (id INT PRIMARY KEY, name VARCHAR(100), email VARCHAR(100), category VARCHAR(50));",
            "CREATE TABLE orders (id INT PRIMARY KEY, customer_id INT, amount DECIMAL(10,2), order_date DATE);"
        ],
        "documentation": [
            "Customer categories include: Premium, Standard, Basic",
            "Orders are recorded with timestamps and amounts in USD"
        ],
        "sql_examples": [
            "SELECT AVG(amount) FROM orders GROUP BY customer_id;",
            "SELECT c.category, COUNT(*) FROM customers c GROUP BY c.category;"
        ],
        "qa_pairs": [
            {
                "question": "What is the average order amount?",
                "sql": "SELECT AVG(amount) FROM orders;",
                "score": 0.95
            },
            {
                "question": "How many customers are in each category?",
                "sql": "SELECT category, COUNT(*) FROM customers GROUP BY category;",
                "score": 0.88
            }
        ],
        "domain_knowledge": [
            "Business operates in retail sector with focus on customer segmentation",
            "Order amounts typically range from $10 to $1000"
        ]
    }
    
    mock_retriever.retrieve_context.return_value = mock_context
    return mock_retriever


def demonstrate_basic_usage():
    """Demonstrate basic Decomposer agent usage."""
    print("=== Basic Decomposer Agent Usage ===\n")
    
    # Create agent
    agent = DecomposerAgent(agent_name="DemoDecomposer", dataset_name="generic")
    
    # Create test message
    message = ChatMessage(
        db_id="retail_db",
        query="Show me the total sales amount for each product category",
        desc_str="""# Table: products
[
  (id, INTEGER, Product unique identifier),
  (name, VARCHAR, Product name),
  (category, VARCHAR, Product category),
  (price, DECIMAL, Product price)
]

# Table: sales
[
  (id, INTEGER, Sale unique identifier),
  (product_id, INTEGER, Reference to product),
  (quantity, INTEGER, Quantity sold),
  (sale_date, DATE, Date of sale)
]""",
        fk_str="products.id = sales.product_id",
        evidence="Focus on sales data from the current year"
    )
    
    # Process message
    print(f"Input Query: {message.query}")
    print(f"Database: {message.db_id}")
    print("\nProcessing...")
    
    response = agent.talk(message)
    
    # Display results
    print(f"\nSuccess: {response.success}")
    if response.success:
        print(f"Generated SQL: {message.final_sql}")
        print(f"Next Agent: {message.send_to}")
        print(f"Sub-questions Count: {response.metadata.get('sub_questions_count', 0)}")
        print(f"RAG Enhanced: {response.metadata.get('rag_enhanced', False)}")
        
        if message.qa_pairs:
            print(f"\nQA Pairs Preview:")
            print(message.qa_pairs[:200] + "..." if len(message.qa_pairs) > 200 else message.qa_pairs)
    else:
        print(f"Error: {response.error}")
    
    # Show statistics
    stats = agent.get_decomposition_stats()
    print(f"\nAgent Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def demonstrate_rag_enhanced_usage():
    """Demonstrate RAG-enhanced Decomposer agent usage."""
    print("\n\n=== RAG-Enhanced Decomposer Agent Usage ===\n")
    
    # Create mock RAG retriever
    mock_rag_retriever = create_mock_rag_retriever()
    
    # Create agent with RAG enhancement
    agent = DecomposerAgent(
        agent_name="RAGDecomposer",
        dataset_name="bird",  # Use BIRD dataset for context-focused retrieval
        rag_retriever=mock_rag_retriever
    )
    
    # Create complex test message
    message = ChatMessage(
        db_id="ecommerce_db",
        query="What is the average order value for premium customers compared to standard customers in the last quarter?",
        desc_str="""# Table: customers
[
  (id, INTEGER, Customer unique identifier),
  (name, VARCHAR, Customer full name),
  (email, VARCHAR, Customer email address),
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
        evidence="Premium customers have category = 'Premium', standard customers have category = 'Standard'. Last quarter refers to the most recent 3-month period."
    )
    
    # Process message
    print(f"Input Query: {message.query}")
    print(f"Database: {message.db_id}")
    print(f"Dataset Type: {agent.config.dataset_type.value}")
    print("\nProcessing with RAG enhancement...")
    
    response = agent.talk(message)
    
    # Display results
    print(f"\nSuccess: {response.success}")
    if response.success:
        print(f"Generated SQL: {message.final_sql}")
        print(f"Sub-questions: {response.metadata.get('sub_questions', [])}")
        print(f"RAG Enhanced: {response.metadata.get('rag_enhanced', False)}")
        
        # Show that RAG retriever was called
        print(f"\nRAG Retriever Called: {mock_rag_retriever.retrieve_context.called}")
        if mock_rag_retriever.retrieve_context.called:
            call_args = mock_rag_retriever.retrieve_context.call_args
            print(f"RAG Query: {call_args[0][0]}")
            print(f"RAG DB ID: {call_args[0][1]}")
            print(f"RAG Strategy: {call_args[0][2]}")
    else:
        print(f"Error: {response.error}")


def demonstrate_dataset_switching():
    """Demonstrate switching between different dataset types."""
    print("\n\n=== Dataset Switching Demonstration ===\n")
    
    agent = DecomposerAgent()
    
    # Show supported datasets
    datasets = agent.get_supported_datasets()
    print(f"Supported datasets: {datasets}")
    
    # Test each dataset type
    test_query = "Find the top 5 customers by total order amount"
    schema_info = "# Table: customers\n[id, name]\n# Table: orders\n[id, customer_id, amount]"
    
    for dataset in datasets:
        print(f"\n--- Testing {dataset.upper()} dataset ---")
        
        # Switch dataset
        agent.switch_dataset(dataset)
        print(f"Current dataset: {agent.dataset_name}")
        print(f"Dataset type: {agent.config.dataset_type.value}")
        
        # Create message
        message = ChatMessage(
            db_id="test_db",
            query=test_query,
            desc_str=schema_info,
            fk_str="customers.id = orders.customer_id",
            evidence=""
        )
        
        # Process
        response = agent.talk(message)
        print(f"Processing success: {response.success}")
        if response.success:
            print(f"Generated SQL preview: {message.final_sql[:100]}...")


def demonstrate_configuration_updates():
    """Demonstrate configuration updates."""
    print("\n\n=== Configuration Updates Demonstration ===\n")
    
    agent = DecomposerAgent()
    
    # Show initial configuration
    print("Initial Configuration:")
    print(f"  Max sub-questions: {agent.config.max_sub_questions}")
    print(f"  CoT reasoning enabled: {agent.config.enable_cot_reasoning}")
    print(f"  RAG enhancement enabled: {agent.config.enable_rag_enhancement}")
    print(f"  Temperature: {agent.config.temperature}")
    
    # Update configuration
    print("\nUpdating configuration...")
    agent.update_config(
        max_sub_questions=3,
        enable_cot_reasoning=False,
        temperature=0.2
    )
    
    # Show updated configuration
    print("Updated Configuration:")
    print(f"  Max sub-questions: {agent.config.max_sub_questions}")
    print(f"  CoT reasoning enabled: {agent.config.enable_cot_reasoning}")
    print(f"  RAG enhancement enabled: {agent.config.enable_rag_enhancement}")
    print(f"  Temperature: {agent.config.temperature}")
    
    # Test with updated config
    message = ChatMessage(
        db_id="test_db",
        query="Show sales data with multiple aggregations and filters",
        desc_str="# Table: sales\n[id, amount, date, region, product_id]",
        fk_str="",
        evidence=""
    )
    
    response = agent.talk(message)
    print(f"\nProcessing with updated config - Success: {response.success}")
    if response.success:
        sub_questions_count = response.metadata.get('sub_questions_count', 0)
        print(f"Sub-questions generated: {sub_questions_count} (max allowed: {agent.config.max_sub_questions})")


def demonstrate_statistics_tracking():
    """Demonstrate statistics tracking."""
    print("\n\n=== Statistics Tracking Demonstration ===\n")
    
    agent = DecomposerAgent()
    
    # Process multiple queries
    test_queries = [
        ("Simple query", "List all products"),
        ("Medium query", "Show total sales by category"),
        ("Complex query", "Calculate monthly growth rate for each product category with year-over-year comparison"),
        ("Another simple", "Count customers"),
        ("Another complex", "Find customers with above-average order frequency and their preferred product categories")
    ]
    
    schema_info = """# Table: products
[id, name, category, price]
# Table: sales
[id, product_id, amount, date]
# Table: customers
[id, name, email]"""
    
    print("Processing multiple queries to track statistics...")
    
    for query_type, query in test_queries:
        message = ChatMessage(
            db_id="stats_test_db",
            query=query,
            desc_str=schema_info,
            fk_str="",
            evidence=""
        )
        
        response = agent.talk(message)
        print(f"  {query_type}: {'✓' if response.success else '✗'}")
    
    # Show final statistics
    stats = agent.get_decomposition_stats()
    print(f"\nFinal Statistics:")
    print(f"  Total queries processed: {stats['total_queries']}")
    print(f"  Simple queries: {stats['simple_queries']}")
    print(f"  Complex queries: {stats['complex_queries']}")
    print(f"  Average sub-questions per query: {stats['avg_sub_questions']:.2f}")
    print(f"  RAG enhancement rate: {stats['rag_enhancement_rate']:.2%}")
    print(f"  Dataset type: {stats['dataset_type']}")
    
    # Reset statistics
    print("\nResetting statistics...")
    agent.reset_decomposition_stats()
    
    reset_stats = agent.get_decomposition_stats()
    print(f"After reset - Total queries: {reset_stats['total_queries']}")


def demonstrate_message_routing():
    """Demonstrate message routing with other agents."""
    print("\n\n=== Message Routing Demonstration ===\n")
    
    # Create message router
    router = MessageRouter()
    
    # Create agent with router
    agent = DecomposerAgent(router=router)
    
    # Create mock Refiner agent for demonstration
    class MockRefinerAgent:
        def __init__(self):
            self.agent_name = "Refiner"
        
        def talk(self, message):
            print(f"  Refiner received message with SQL: {message.final_sql[:50]}...")
            return Mock(success=True)
    
    # Register mock refiner
    mock_refiner = MockRefinerAgent()
    router.register_agent(mock_refiner)
    
    # Process message
    message = ChatMessage(
        db_id="routing_test_db",
        query="Show customer order summary",
        desc_str="# Table: customers\n[id, name]\n# Table: orders\n[id, customer_id, amount]",
        fk_str="customers.id = orders.customer_id",
        evidence=""
    )
    
    print("Processing message with routing...")
    response = agent.process_message(message)  # Use process_message for routing
    
    print(f"Decomposer processing: {'✓' if response.success else '✗'}")
    print(f"Message routed to: {message.send_to}")
    
    # Show routing history
    history = router.get_routing_history()
    print(f"\nRouting History ({len(history)} events):")
    for event in history:
        print(f"  {event['from']} → {event['to']}: {event['query'][:50]}...")


def main():
    """Run all demonstrations."""
    print("Decomposer Agent Examples")
    print("=" * 50)
    
    try:
        demonstrate_basic_usage()
        demonstrate_rag_enhanced_usage()
        demonstrate_dataset_switching()
        demonstrate_configuration_updates()
        demonstrate_statistics_tracking()
        demonstrate_message_routing()
        
        print("\n" + "=" * 50)
        print("All demonstrations completed successfully!")
        
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()