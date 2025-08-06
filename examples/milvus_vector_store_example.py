"""
Example usage of Milvus vector store for Text2SQL system.
"""
import os
import sys
import uuid
from typing import List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.vector_store import vector_store


def generate_real_embedding(text: str) -> List[float]:
    """Generate a real embedding using the embedding service."""
    from services.embedding_service import embedding_service
    return embedding_service.generate_embedding(text)


def main():
    """Demonstrate Milvus vector store usage."""
    print("=== Milvus Vector Store Example ===\n")
    
    # Use global vector store instance
    try:
        print("✓ Using global vector store instance\n")
    except Exception as e:
        print(f"✗ Failed to access vector store: {e}")
        return
    
    # Example 1: Store training data (DDL statements)
    print("1. Storing DDL training data...")
    ddl_examples = [
        {
            "content": "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100), email VARCHAR(255));",
            "data_type": "ddl",
            "db_id": "ecommerce_db",
            "table_names": ["users"]
        },
        {
            "content": "CREATE TABLE orders (id INT PRIMARY KEY, user_id INT, total DECIMAL(10,2), FOREIGN KEY (user_id) REFERENCES users(id));",
            "data_type": "ddl", 
            "db_id": "ecommerce_db",
            "table_names": ["orders", "users"]
        }
    ]
    
    for example in ddl_examples:
        vector_id = str(uuid.uuid4())
        embedding = generate_real_embedding(example["content"])
        vector_store.insert(vector_id, embedding, example)
        print(f"  ✓ Stored DDL: {example['content'][:50]}...")
    
    # Example 2: Store question-SQL pairs
    print("\n2. Storing question-SQL pairs...")
    qa_pairs = [
        {
            "question": "How many users are there?",
            "sql": "SELECT COUNT(*) FROM users;",
            "content": "Q: How many users are there?\nA: SELECT COUNT(*) FROM users;",
            "data_type": "qa_pair",
            "db_id": "ecommerce_db"
        },
        {
            "question": "What are the total sales for each user?",
            "sql": "SELECT u.name, SUM(o.total) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name;",
            "content": "Q: What are the total sales for each user?\nA: SELECT u.name, SUM(o.total) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name;",
            "data_type": "qa_pair",
            "db_id": "ecommerce_db"
        }
    ]
    
    # Batch insert for efficiency
    ids = [str(uuid.uuid4()) for _ in qa_pairs]
    vectors = [generate_real_embedding(pair["content"]) for pair in qa_pairs]
    vector_store.insert_batch(ids, vectors, qa_pairs)
    print(f"  ✓ Stored {len(qa_pairs)} question-SQL pairs")
    
    # Example 3: Search for similar content
    print("\n3. Searching for similar content...")
    query = "How many customers do we have?"
    query_embedding = generate_real_embedding(query)
    
    # Search for similar questions
    results = vector_store.search(
        query_embedding,
        filter={"data_type": "qa_pair"},
        limit=3
    )
    
    print(f"Query: '{query}'")
    print("Similar questions found:")
    for i, result in enumerate(results, 1):
        print(f"  {i}. Score: {result.score:.3f}")
        print(f"     Question: {result.metadata.get('question', 'N/A')}")
        print(f"     SQL: {result.metadata.get('sql', 'N/A')}")
        print()
    
    # Example 4: Search with different filters
    print("4. Searching DDL statements...")
    ddl_results = vector_store.search(
        generate_real_embedding("table users"),
        filter={"data_type": "ddl"},
        limit=2
    )
    
    print("DDL statements found:")
    for i, result in enumerate(ddl_results, 1):
        print(f"  {i}. Score: {result.score:.3f}")
        print(f"     Content: {result.metadata.get('content', 'N/A')[:100]}...")
        print()
    
    # Example 5: Collection statistics
    print("5. Collection statistics...")
    stats = vector_store.get_collection_stats()
    print(f"  Total entities: {stats.get('total_entities', 'N/A')}")
    print(f"  Collection name: {stats.get('collection_name', 'N/A')}")
    print(f"  Dimension: {stats.get('dimension', 'N/A')}")
    
    # Example 6: Cleanup (delete by filter)
    print("\n6. Cleanup example...")
    print("  Deleting test data...")
    vector_store.delete_by_filter({"db_id": "ecommerce_db"})
    
    final_stats = vector_store.get_collection_stats()
    print(f"  Entities after cleanup: {final_stats.get('total_entities', 'N/A')}")
    
    # Close connection
    vector_store.close()
    print("\n✓ Vector store connection closed")


if __name__ == "__main__":
    main()