"""
Complete example demonstrating the integrated vector storage system.
"""
import os
import sys
import uuid
from typing import List, Dict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.vector_store import vector_store
from services.embedding_service import embedding_service
from services.training_service import training_service
from services.enhanced_rag_retriever import enhanced_rag_retriever, RetrievalConfig, RetrievalStrategy
from config.settings import config


def setup_environment():
    """Setup environment variables for the demo."""
    os.environ.setdefault("USE_MOCK_VECTOR_STORE", "false")
    os.environ.setdefault("MILVUS_COLLECTION", "demo_collection")


def demonstrate_training_workflow():
    """Demonstrate the complete training workflow."""
    print("=== Training Workflow Demonstration ===\n")
    
    # Use global service instances
    print("✓ Using global service instances")
    print(f"✓ Using embedding model: {embedding_service.model}")
    print(f"✓ Vector dimension: {embedding_service.dimension}")
    
    # 1. Train with DDL statements
    print("\n1. Training with DDL statements...")
    ddl_statements = [
        """CREATE TABLE customers (
            id INT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE orders (
            id INT PRIMARY KEY,
            customer_id INT,
            total_amount DECIMAL(10,2),
            order_date DATE,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );""",
        """CREATE TABLE products (
            id INT PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            price DECIMAL(10,2),
            category VARCHAR(50)
        );"""
    ]
    
    success = training_service.train_ddl(ddl_statements, "ecommerce_db")
    print(f"  DDL training: {'✓ Success' if success else '✗ Failed'}")
    
    # 2. Train with documentation
    print("\n2. Training with business documentation...")
    docs = [
        {
            "title": "Customer Management",
            "content": "Customers are the core entities in our e-commerce system. Each customer has a unique email and can place multiple orders.",
            "category": "business_rules"
        },
        {
            "title": "Order Processing",
            "content": "Orders contain products and are linked to customers. The total_amount represents the sum of all product prices in the order.",
            "category": "business_rules"
        }
    ]
    
    success = training_service.train_documentation(docs, "ecommerce_db")
    print(f"  Documentation training: {'✓ Success' if success else '✗ Failed'}")
    
    # 3. Train with SQL examples
    print("\n3. Training with SQL examples...")
    sql_examples = [
        "SELECT COUNT(*) FROM customers WHERE created_at >= '2024-01-01';",
        "SELECT c.name, COUNT(o.id) as order_count FROM customers c LEFT JOIN orders o ON c.id = o.customer_id GROUP BY c.id, c.name;",
        "SELECT p.category, AVG(p.price) as avg_price FROM products p GROUP BY p.category;"
    ]
    
    success = training_service.train_sql(sql_examples, "ecommerce_db")
    print(f"  SQL examples training: {'✓ Success' if success else '✗ Failed'}")
    
    # 4. Train with question-SQL pairs
    print("\n4. Training with question-SQL pairs...")
    qa_pairs = [
        {
            "question": "How many customers do we have?",
            "sql": "SELECT COUNT(*) FROM customers;"
        },
        {
            "question": "What is the total revenue from all orders?",
            "sql": "SELECT SUM(total_amount) FROM orders;"
        },
        {
            "question": "Which customers have placed more than 5 orders?",
            "sql": "SELECT c.name, COUNT(o.id) as order_count FROM customers c JOIN orders o ON c.id = o.customer_id GROUP BY c.id, c.name HAVING COUNT(o.id) > 5;"
        },
        {
            "question": "What are the top 3 most expensive products?",
            "sql": "SELECT name, price FROM products ORDER BY price DESC LIMIT 3;"
        }
    ]
    
    success = training_service.train_qa_pairs(qa_pairs, "ecommerce_db")
    print(f"  QA pairs training: {'✓ Success' if success else '✗ Failed'}")
    
    # 5. Train with domain knowledge
    print("\n5. Training with domain knowledge...")
    domain_knowledge = [
        {
            "content": "In e-commerce, customer lifetime value (CLV) is calculated as the average order value multiplied by the number of orders per customer.",
            "category": "metrics",
            "tags": ["clv", "metrics", "business"]
        },
        {
            "content": "Revenue analysis typically involves grouping by time periods (daily, monthly, yearly) and product categories.",
            "category": "analytics",
            "tags": ["revenue", "analytics", "reporting"]
        }
    ]
    
    success = training_service.train_domain_knowledge(domain_knowledge, "ecommerce_db")
    print(f"  Domain knowledge training: {'✓ Success' if success else '✗ Failed'}")
    
    return training_service


def demonstrate_retrieval_workflow():
    """Demonstrate the enhanced RAG retrieval workflow."""
    print("\n=== Enhanced RAG Retrieval Demonstration ===\n")
    
    # Use global service instances
    
    # Test different retrieval strategies
    strategies = [
        (RetrievalStrategy.BALANCED, "Balanced retrieval"),
        (RetrievalStrategy.QA_FOCUSED, "QA-focused retrieval"),
        (RetrievalStrategy.SQL_FOCUSED, "SQL-focused retrieval"),
        (RetrievalStrategy.CONTEXT_FOCUSED, "Context-focused retrieval")
    ]
    
    test_queries = [
        "How many new customers joined last month?",
        "What is the average order value by product category?",
        "Show me the top customers by total spending"
    ]
    
    for strategy, strategy_name in strategies:
        print(f"\n--- {strategy_name} ---")
        
        config = RetrievalConfig(
            strategy=strategy,
            similarity_threshold=0.6,
            max_examples_per_type=2
        )
        
        # Update global retriever config
        enhanced_rag_retriever.config = config
        enhanced_rag_retriever.context_builder = enhanced_rag_retriever.context_builder.__class__(config)
        enhanced_rag_retriever.prompt_builder = enhanced_rag_retriever.prompt_builder.__class__(config)
        
        for query in test_queries:
            print(f"\nQuery: '{query}'")
            
            # Retrieve context
            context = enhanced_rag_retriever.retrieve_context(query, "ecommerce_db")
            
            # Show retrieval stats
            stats = enhanced_rag_retriever.get_retrieval_stats(query, "ecommerce_db")
            print(f"  Retrieved: {stats['total_retrieved']} items")
            print(f"  - DDL: {stats['retrieved_counts']['ddl_statements']}")
            print(f"  - Docs: {stats['retrieved_counts']['documentation']}")
            print(f"  - SQL: {stats['retrieved_counts']['sql_examples']}")
            print(f"  - QA: {stats['retrieved_counts']['qa_pairs']}")
            print(f"  - Domain: {stats['retrieved_counts']['domain_knowledge']}")
            
            # Show high-quality QA pairs if any
            if stats['high_quality_qa_pairs'] > 0:
                print(f"  - High-quality QA pairs: {stats['high_quality_qa_pairs']}")
            
            # Build enhanced prompt (truncated for display)
            prompt = enhanced_rag_retriever.build_enhanced_prompt(
                query, context, "# Database Schema\n[Schema would be here]"
            )
            print(f"  Generated prompt length: {len(prompt)} characters")
            
            break  # Only show first query for each strategy


def demonstrate_vector_operations():
    """Demonstrate low-level vector operations."""
    print("\n=== Vector Operations Demonstration ===\n")
    
    # Use global service instances
    print("✓ Using global service instances")
    
    # 1. Single insert and search
    print("\n1. Single vector operations...")
    test_text = "SELECT COUNT(*) FROM users WHERE active = 1"
    test_embedding = embedding_service.generate_embedding(test_text)
    test_id = str(uuid.uuid4())
    
    metadata = {
        "data_type": "sql",
        "db_id": "test_db",
        "content": test_text,
        "sql": test_text
    }
    
    vector_store.insert(test_id, test_embedding, metadata)
    print("  ✓ Vector inserted")
    
    # Search for similar vectors
    results = vector_store.search(test_embedding, limit=1)
    print(f"  ✓ Found {len(results)} similar vectors")
    if results:
        print(f"    - ID: {results[0].id}")
        print(f"    - Score: {results[0].score:.3f}")
        print(f"    - Content: {results[0].metadata.get('content', 'N/A')[:50]}...")
    
    # 2. Batch operations
    print("\n2. Batch vector operations...")
    batch_texts = [
        "INSERT INTO products (name, price) VALUES ('Widget', 19.99)",
        "UPDATE customers SET email = 'new@email.com' WHERE id = 1",
        "DELETE FROM orders WHERE order_date < '2023-01-01'"
    ]
    
    batch_embeddings = embedding_service.generate_embeddings_batch(batch_texts)
    batch_ids = [str(uuid.uuid4()) for _ in batch_texts]
    batch_metadata = [
        {
            "data_type": "sql",
            "db_id": "test_db",
            "content": text,
            "sql": text,
            "operation": "INSERT" if "INSERT" in text else "UPDATE" if "UPDATE" in text else "DELETE"
        }
        for text in batch_texts
    ]
    
    vector_store.insert_batch(batch_ids, batch_embeddings, batch_metadata)
    print(f"  ✓ Inserted batch of {len(batch_texts)} vectors")
    
    # 3. Filtered search
    print("\n3. Filtered search operations...")
    search_results = vector_store.search(
        embedding_service.generate_embedding("modify data in database"),
        filter={"data_type": "sql"},
        limit=5
    )
    
    print(f"  ✓ Found {len(search_results)} SQL-related vectors")
    for i, result in enumerate(search_results, 1):
        operation = result.metadata.get('operation', 'UNKNOWN')
        print(f"    {i}. {operation} operation (score: {result.score:.3f})")
    
    # 4. Collection statistics
    print("\n4. Collection statistics...")
    stats = vector_store.get_collection_stats()
    print(f"  Total entities: {stats.get('total_entities', 'N/A')}")
    print(f"  Collection: {stats.get('collection_name', 'N/A')}")
    print(f"  Dimension: {stats.get('dimension', 'N/A')}")
    
    # 5. Cleanup
    print("\n5. Cleanup operations...")
    vector_store.delete_by_filter({"db_id": "test_db"})
    print("  ✓ Cleaned up test data")
    
    final_stats = vector_store.get_collection_stats()
    print(f"  Final entity count: {final_stats.get('total_entities', 'N/A')}")
    
    vector_store.close()
    print("  ✓ Vector store connection closed")


def main():
    """Run the complete demonstration."""
    print("🚀 Complete Vector Storage System Demonstration\n")
    
    # Setup environment
    setup_environment()
    
    try:
        # 1. Demonstrate training workflow
        training_service = demonstrate_training_workflow()
        
        # 2. Demonstrate retrieval workflow
        demonstrate_retrieval_workflow()
        
        # 3. Demonstrate vector operations
        demonstrate_vector_operations()
        
        print("\n✅ All demonstrations completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            vector_store.close()
        except:
            pass


if __name__ == "__main__":
    main()