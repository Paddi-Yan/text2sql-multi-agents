"""
Vector store implementation for training data storage and retrieval.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import uuid


@dataclass
class SearchResult:
    """Search result from vector store."""
    id: str
    score: float
    metadata: Dict[str, Any]


class MockVectorStore:
    """Mock vector store for development and testing."""
    
    def __init__(self):
        self.data = {}  # id -> (vector, metadata)
    
    def insert(self, id: str, vector: List[float], metadata: Dict[str, Any]):
        """Insert vector with metadata."""
        self.data[id] = (vector, metadata)
    
    def search(self, vector: List[float], filter: Optional[Dict[str, Any]] = None, 
               limit: int = 5) -> List[SearchResult]:
        """Search for similar vectors."""
        results = []
        
        for doc_id, (stored_vector, stored_metadata) in self.data.items():
            # Apply filter if provided
            if filter:
                match = True
                for key, value in filter.items():
                    if key not in stored_metadata or stored_metadata[key] != value:
                        match = False
                        break
                if not match:
                    continue
            
            # Calculate similarity (simplified cosine similarity)
            similarity = self._calculate_similarity(vector, stored_vector)
            results.append(SearchResult(
                id=doc_id,
                score=similarity,
                metadata=stored_metadata
            ))
        
        # Sort by similarity and return top results
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]
    
    def delete(self, id: str):
        """Delete vector by id."""
        if id in self.data:
            del self.data[id]
    
    def _calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


class VectorStore:
    """Production vector store interface (to be implemented with Milvus)."""
    
    def __init__(self, config):
        """Initialize vector store with configuration."""
        # For now, use mock implementation
        self._store = MockVectorStore()
    
    def insert(self, id: str, vector: List[float], metadata: Dict[str, Any]):
        """Insert vector with metadata."""
        return self._store.insert(id, vector, metadata)
    
    def search(self, vector: List[float], filter: Optional[Dict[str, Any]] = None, 
               limit: int = 5) -> List[SearchResult]:
        """Search for similar vectors."""
        return self._store.search(vector, filter, limit)
    
    def delete(self, id: str):
        """Delete vector by id."""
        return self._store.delete(id)