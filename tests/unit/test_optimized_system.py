"""
Test the optimized vector storage system.
"""
import os
import sys

# Add project root to path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.embedding_service import EmbeddingService
from storage.vector_store import VectorStore
from config.settings import config

def test_embedding_service():
    """Test the embedding service."""
    print("=== Testing Embedding Service ===")
    
    try:
        embedding_service = EmbeddingService()
        
        # Test health check
        health = embedding_service.health_check()
        print(f"Health check: {health['status']}")
        print(f"Model: {health.get('model', 'N/A')}")
        print(f"Base URL: {health.get('base_url', 'N/A')}")
        print(f"Dimension: {health.get('dimension', 'N/A')}")
        
        # Test embedding generation
        test_text = "SELECT COUNT(*) FROM users"
        embedding = embedding_service.generate_embedding(test_text)
        print(f"Generated embedding dimension: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
        
        # Test batch embedding generation
        test_texts = [
            "SELECT * FROM products",
            "INSERT INTO orders VALUES (1, 100)",
            "UPDATE customers SET status = 'active'"
        ]
        batch_embeddings = embedding_service.generate_embeddings_batch(test_texts)
        print(f"Batch embeddings count: {len(batch_embeddings)}")
        print(f"Each embedding dimension: {len(batch_embeddings[0])}")
        
        return embedding_service
        
    except Exception as e:
        print(f"Error testing embedding service: {e}")
        return None

def test_vector_store():
    """Test the vector store."""
    print("\n=== Testing Vector Store ===")
    
    try:
        vector_store = VectorStore()
        print("✓ Vector store initialized successfully")
        
        # Test collection stats
        stats = vector_store.get_collection_stats()
        print(f"Collection stats: {stats}")
        
        return vector_store
        
    except Exception as e:
        print(f"Error connecting to Milvus: {e}")
        print("Please ensure Milvus is running: docker-compose up -d milvus-standalone")
        return None

def test_configuration():
    """Test the configuration system."""
    print("\n=== Testing Configuration ===")
    
    print(f"Embedding model: {config.embedding_config.model}")
    print(f"Embedding dimension: {config.embedding_config.dimension}")
    print(f"Base URL: {config.embedding_config.base_url}")
    print(f"Milvus host: {config.vector_store_config.host}")
    print(f"Milvus port: {config.vector_store_config.port}")
    print(f"Collection name: {config.vector_store_config.collection_name}")

def test_integration():
    """Test integration between embedding service and vector store."""
    print("\n=== Testing Integration ===")
    
    try:
        # Initialize services
        embedding_service = EmbeddingService()
        vector_store = VectorStore()
        
        # Test data
        test_data = [
            {
                "text": "SELECT COUNT(*) FROM users WHERE active = 1",
                "metadata": {
                    "data_type": "sql",
                    "db_id": "test_db",
                    "content": "SELECT COUNT(*) FROM users WHERE active = 1",
                    "sql": "SELECT COUNT(*) FROM users WHERE active = 1"
                }
            },
            {
                "text": "How many active users are there?",
                "metadata": {
                    "data_type": "qa_pair",
                    "db_id": "test_db",
                    "content": "Q: How many active users are there?\nA: SELECT COUNT(*) FROM users WHERE active = 1",
                    "question": "How many active users are there?",
                    "sql": "SELECT COUNT(*) FROM users WHERE active = 1"
                }
            }
        ]
        
        # Insert test data
        import uuid
        for i, item in enumerate(test_data):
            vector_id = str(uuid.uuid4())
            embedding = embedding_service.generate_embedding(item["text"])
            vector_store.insert(vector_id, embedding, item["metadata"])
            print(f"✓ Inserted item {i+1}: {item['text'][:50]}...")
        
        # Test search
        query = "Count active users"
        query_embedding = embedding_service.generate_embedding(query)
        results = vector_store.search(query_embedding, limit=5)
        
        print(f"\nSearch results for '{query}':")
        for i, result in enumerate(results, 1):
            print(f"  {i}. Score: {result.score:.3f}")
            print(f"     Type: {result.metadata.get('data_type', 'N/A')}")
            print(f"     Content: {result.metadata.get('content', 'N/A')[:80]}...")
            print()
        
        # Test filtered search
        sql_results = vector_store.search(
            query_embedding,
            filter={"data_type": "sql"},
            limit=3
        )
        print(f"Filtered search (SQL only): {len(sql_results)} results")
        
        # Cleanup test data
        vector_store.delete_by_filter({"db_id": "test_db"})
        print("✓ Cleaned up test data")
        
        return True
        
    except Exception as e:
        print(f"Integration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Optimized Vector Storage System\n")
    
    # Test configuration
    test_configuration()
    
    # Test embedding service
    embedding_service = test_embedding_service()
    
    # Test vector store
    vector_store = test_vector_store()
    
    # Test integration if both services work
    integration_success = False
    if embedding_service and vector_store:
        integration_success = test_integration()
    
    # Results summary
    print("\n" + "="*50)
    print("RESULTS SUMMARY")
    print("="*50)
    
    if embedding_service:
        print("✅ Embedding service: WORKING")
    else:
        print("❌ Embedding service: FAILED")
    
    if vector_store:
        print("✅ Vector store: WORKING")
        vector_store.close()
    else:
        print("❌ Vector store: FAILED")
    
    if integration_success:
        print("✅ Integration test: PASSED")
    else:
        print("❌ Integration test: FAILED")
    
    if embedding_service and vector_store and integration_success:
        print("\n🎉 All systems are working correctly!")
    else:
        print("\n⚠️  Some systems need attention.")

if __name__ == "__main__":
    main()