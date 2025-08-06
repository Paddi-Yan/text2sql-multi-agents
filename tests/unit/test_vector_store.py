"""
Unit tests for vector store implementation.
"""
import pytest
import uuid
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from storage.vector_store import VectorStore, SearchResult


class TestVectorStore:
    """Test cases for VectorStore."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock Milvus for testing
        with patch('storage.vector_store.connections'), \
             patch('storage.vector_store.Collection'), \
             patch('storage.vector_store.utility'):
            self.store = VectorStore()
        
        self.test_vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        self.test_metadata = {
            "data_type": "qa_pair",
            "db_id": "test_db",
            "content": "Test content",
            "question": "What is the test?",
            "sql": "SELECT * FROM test;"
        }
    
    @patch('storage.vector_store.connections')
    @patch('storage.vector_store.Collection')
    @patch('storage.vector_store.utility')
    def test_initialization(self, mock_utility, mock_collection, mock_connections):
        """Test VectorStore initialization."""
        mock_utility.has_collection.return_value = False
        mock_collection_instance = Mock()
        mock_collection.return_value = mock_collection_instance
        
        store = VectorStore()
        
        # Verify connection was attempted
        mock_connections.connect.assert_called_once()
        
        # Verify collection creation was attempted
        mock_collection.assert_called()
        mock_collection_instance.create_index.assert_called_once()
        mock_collection_instance.load.assert_called_once()
    
    def test_insert(self):
        """Test vector insertion."""
        test_id = str(uuid.uuid4())
        
        # Mock the collection insert method
        self.store.collection.insert = Mock()
        self.store.collection.flush = Mock()
        
        # Test insertion
        self.store.insert(test_id, self.test_vector, self.test_metadata)
        
        # Verify insert was called
        self.store.collection.insert.assert_called_once()
        self.store.collection.flush.assert_called_once()
    
    def test_batch_insert(self):
        """Test batch insertion."""
        ids = [f"batch_{i}" for i in range(3)]
        vectors = [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ]
        metadatas = [
            {"data_type": "test", "content": f"content_{i}"}
            for i in range(3)
        ]
        
        # Mock the collection methods
        self.store.collection.insert = Mock()
        self.store.collection.flush = Mock()
        
        # Test batch insertion
        self.store.insert_batch(ids, vectors, metadatas)
        
        # Verify insert was called
        self.store.collection.insert.assert_called_once()
        self.store.collection.flush.assert_called_once()
    
    def test_search(self):
        """Test vector search."""
        # Mock search results
        mock_hit = Mock()
        mock_hit.entity.get.side_effect = lambda key, default="": {
            "id": "test_id",
            "data_type": "qa_pair",
            "db_id": "test_db",
            "content": "test content",
            "question": "test question",
            "sql": "SELECT * FROM test;"
        }.get(key, default)
        mock_hit.score = 0.95
        
        mock_hits = [mock_hit]
        mock_results = [mock_hits]
        
        self.store.collection.search = Mock(return_value=mock_results)
        
        # Test search
        results = self.store.search(self.test_vector, limit=1)
        
        # Verify search was called
        self.store.collection.search.assert_called_once()
        
        # Verify results
        assert len(results) == 1
        assert results[0].id == "test_id"
        assert results[0].score == 0.95
        assert results[0].metadata["data_type"] == "qa_pair"
    
    def test_search_with_filter(self):
        """Test search with filter."""
        # Mock search results
        mock_hit = Mock()
        mock_hit.entity.get.side_effect = lambda key, default="": {
            "id": "test_id",
            "data_type": "sql",
            "db_id": "test_db",
            "content": "test content",
            "question": "",
            "sql": "SELECT * FROM test;"
        }.get(key, default)
        mock_hit.score = 0.85
        
        mock_hits = [mock_hit]
        mock_results = [mock_hits]
        
        self.store.collection.search = Mock(return_value=mock_results)
        
        # Test search with filter
        results = self.store.search(
            self.test_vector,
            filter={"data_type": "sql", "db_id": "test_db"},
            limit=5
        )
        
        # Verify search was called with filter expression
        call_args = self.store.collection.search.call_args
        assert 'expr' in call_args.kwargs
        assert 'data_type == "sql"' in call_args.kwargs['expr']
        assert 'db_id == "test_db"' in call_args.kwargs['expr']
        
        # Verify results
        assert len(results) == 1
        assert results[0].metadata["data_type"] == "sql"
    
    def test_delete(self):
        """Test vector deletion."""
        test_id = "test_id"
        
        # Mock the collection methods
        self.store.collection.delete = Mock()
        self.store.collection.flush = Mock()
        
        # Test deletion
        self.store.delete(test_id)
        
        # Verify delete was called with correct expression
        self.store.collection.delete.assert_called_once_with(f'id == "{test_id}"')
        self.store.collection.flush.assert_called_once()
    
    def test_delete_by_filter(self):
        """Test deletion by filter."""
        filter_dict = {"data_type": "test", "db_id": "test_db"}
        
        # Mock the collection methods
        self.store.collection.delete = Mock()
        self.store.collection.flush = Mock()
        
        # Test deletion by filter
        self.store.delete_by_filter(filter_dict)
        
        # Verify delete was called with correct expression
        call_args = self.store.collection.delete.call_args[0][0]
        assert 'data_type == "test"' in call_args
        assert 'db_id == "test_db"' in call_args
        self.store.collection.flush.assert_called_once()
    
    def test_get_collection_stats(self):
        """Test collection statistics."""
        # Mock collection stats
        self.store.collection.num_entities = 100
        
        # Test stats
        stats = self.store.get_collection_stats()
        
        # Verify stats
        assert stats["total_entities"] == 100
        assert "collection_name" in stats
        assert "dimension" in stats
    
    def test_create_index(self):
        """Test index creation."""
        # Mock the collection method
        self.store.collection.create_index = Mock()
        
        # Test index creation
        self.store.create_index(
            field_name="vector",
            index_type="IVF_FLAT",
            metric_type="COSINE"
        )
        
        # Verify create_index was called
        self.store.collection.create_index.assert_called_once()
        call_args = self.store.collection.create_index.call_args
        assert call_args.kwargs["field_name"] == "vector"
    
    def test_close(self):
        """Test connection closing."""
        # Mock the collection and connections
        self.store.collection.release = Mock()
        
        with patch('storage.vector_store.connections') as mock_connections:
            # Test close
            self.store.close()
            
            # Verify release and disconnect were called
            self.store.collection.release.assert_called_once()
            mock_connections.disconnect.assert_called_once_with("default")


@pytest.mark.integration
class TestVectorStoreIntegration:
    """Integration tests for VectorStore (requires running Milvus)."""
    
    @pytest.fixture
    def vector_store(self):
        """Create a test vector store."""
        try:
            store = VectorStore(
                host="localhost",
                port="19530",
                collection_name="test_collection",
                dimension=3
            )
            yield store
            # Cleanup
            store.close()
        except Exception:
            pytest.skip("Milvus not available for integration tests")
    
    def test_milvus_insert_and_search(self, vector_store):
        """Test Milvus insert and search functionality."""
        test_id = str(uuid.uuid4())
        test_vector = [0.1, 0.2, 0.3]
        test_metadata = {
            "data_type": "test",
            "db_id": "test_db",
            "content": "Test content"
        }
        
        # Insert vector
        vector_store.insert(test_id, test_vector, test_metadata)
        
        # Search for similar vectors
        results = vector_store.search(test_vector, limit=1)
        
        assert len(results) >= 1
        # Note: Exact match might not be first due to indexing
        found = any(r.id == test_id for r in results)
        assert found
    
    def test_milvus_batch_operations(self, vector_store):
        """Test Milvus batch operations."""
        ids = [f"batch_{i}" for i in range(3)]
        vectors = [[0.1 * i, 0.2 * i, 0.3 * i] for i in range(1, 4)]
        metadatas = [
            {"data_type": "batch_test", "content": f"content_{i}"}
            for i in range(3)
        ]
        
        # Batch insert
        vector_store.insert_batch(ids, vectors, metadatas)
        
        # Search to verify insertion
        results = vector_store.search([0.1, 0.2, 0.3], limit=5)
        batch_results = [r for r in results if r.metadata.get("data_type") == "batch_test"]
        assert len(batch_results) >= 1
    
    def test_milvus_filter_search(self, vector_store):
        """Test Milvus search with filters."""
        # Insert vectors with different db_ids
        for i in range(2):
            test_id = f"filter_test_{i}"
            test_vector = [0.1, 0.2, 0.3]
            metadata = {
                "data_type": "filter_test",
                "db_id": f"db_{i}",
                "content": f"content_{i}"
            }
            vector_store.insert(test_id, test_vector, metadata)
        
        # Search with filter
        results = vector_store.search(
            [0.1, 0.2, 0.3],
            filter={"db_id": "db_0"},
            limit=5
        )
        
        # All results should match the filter
        for result in results:
            if result.metadata.get("data_type") == "filter_test":
                assert result.metadata.get("db_id") == "db_0"


if __name__ == "__main__":
    pytest.main([__file__])