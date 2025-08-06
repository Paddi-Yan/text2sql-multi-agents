"""
Vector store implementation for training data storage and retrieval.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging
from pymilvus import (
    connections, 
    Collection, 
    CollectionSchema, 
    FieldSchema, 
    DataType,
    utility
)

from config.settings import config

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result from vector store."""
    id: str
    score: float
    metadata: Dict[str, Any]


class VectorStore:
    """Milvus-based vector store for production use."""
    
    def __init__(self, host: str = None, port: str = None, 
                 collection_name: str = None, dimension: int = None):
        """
        Initialize Milvus vector store.
        
        Args:
            host: Milvus server host (optional, will use config if not provided)
            port: Milvus server port (optional, will use config if not provided)
            collection_name: Name of the collection to use (optional, will use config if not provided)
            dimension: Vector dimension (optional, will use config if not provided)
        """
        self.host = host or config.vector_store_config.host
        self.port = port or config.vector_store_config.port
        self.collection_name = collection_name or config.vector_store_config.collection_name
        self.dimension = dimension or config.vector_store_config.dimension
        self.collection = None
        self._connect()
        self._create_collection()
    
    def _connect(self):
        """Connect to Milvus server."""
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise
    
    def _create_collection(self):
        """Create collection if it doesn't exist."""
        try:
            if utility.has_collection(self.collection_name):
                self.collection = Collection(self.collection_name)
                logger.info(f"Using existing collection: {self.collection_name}")
            else:
                # Define collection schema
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
                    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
                    FieldSchema(name="data_type", dtype=DataType.VARCHAR, max_length=50),
                    FieldSchema(name="db_id", dtype=DataType.VARCHAR, max_length=100),
                    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=10000),
                    FieldSchema(name="question", dtype=DataType.VARCHAR, max_length=5000),
                    FieldSchema(name="sql", dtype=DataType.VARCHAR, max_length=5000),
                    FieldSchema(name="metadata_json", dtype=DataType.VARCHAR, max_length=5000),
                ]
                
                schema = CollectionSchema(
                    fields=fields,
                    description="Text2SQL vector storage"
                )
                
                self.collection = Collection(
                    name=self.collection_name,
                    schema=schema
                )
                
                # Create index for vector field using config
                index_params = {
                    "metric_type": config.vector_store_config.metric_type,
                    "index_type": config.vector_store_config.index_type,
                    "params": {"nlist": config.vector_store_config.nlist}
                }
                self.collection.create_index(
                    field_name="vector",
                    index_params=index_params
                )
                
                logger.info(f"Created new collection: {self.collection_name}")
            
            # Load collection into memory
            self.collection.load()
            
        except Exception as e:
            logger.error(f"Failed to create/load collection: {e}")
            raise
    
    def insert(self, id: str, vector: List[float], metadata: Dict[str, Any]):
        """
        Insert vector with metadata.
        
        Args:
            id: Unique identifier for the vector
            vector: Vector embeddings
            metadata: Associated metadata
        """
        try:
            # Prepare data for insertion - ensure all string fields are not None
            data = [
                [id],  # id
                [vector],  # vector
                [metadata.get("data_type", "") or ""],  # data_type
                [metadata.get("db_id", "") or ""],  # db_id
                [metadata.get("content", "") or ""],  # content
                [metadata.get("question", "") or ""],  # question
                [metadata.get("sql", "") or ""],  # sql
                [str(metadata)],  # metadata_json (serialized)
            ]
            
            self.collection.insert(data)
            self.collection.flush()
            
            logger.debug(f"Inserted vector with id: {id}")
            
        except Exception as e:
            logger.error(f"Failed to insert vector {id}: {e}")
            raise
    
    def insert_batch(self, ids: List[str], vectors: List[List[float]], 
                     metadatas: List[Dict[str, Any]]):
        """
        Insert multiple vectors in batch.
        
        Args:
            ids: List of unique identifiers
            vectors: List of vector embeddings
            metadatas: List of associated metadata
        """
        try:
            if len(ids) != len(vectors) or len(ids) != len(metadatas):
                raise ValueError("Length of ids, vectors, and metadatas must be equal")
            
            # Prepare batch data - ensure all string fields are not None
            data = [
                ids,  # id
                vectors,  # vector
                [meta.get("data_type", "") or "" for meta in metadatas],  # data_type
                [meta.get("db_id", "") or "" for meta in metadatas],  # db_id
                [meta.get("content", "") or "" for meta in metadatas],  # content
                [meta.get("question", "") or "" for meta in metadatas],  # question
                [meta.get("sql", "") or "" for meta in metadatas],  # sql
                [str(meta) for meta in metadatas],  # metadata_json
            ]
            
            self.collection.insert(data)
            self.collection.flush()
            
            logger.info(f"Inserted batch of {len(ids)} vectors")
            
        except Exception as e:
            logger.error(f"Failed to insert batch: {e}")
            raise
    
    def search(self, vector: List[float], filter: Optional[Dict[str, Any]] = None, 
               limit: int = 5) -> List[SearchResult]:
        """
        Search for similar vectors.
        
        Args:
            vector: Query vector
            filter: Optional filter conditions
            limit: Maximum number of results to return
            
        Returns:
            List of search results
        """
        try:
            # Build filter expression
            filter_expr = None
            if filter:
                conditions = []
                for key, value in filter.items():
                    if key in ["data_type", "db_id"]:
                        conditions.append(f'{key} == "{value}"')
                
                if conditions:
                    filter_expr = " and ".join(conditions)
            
            # Search parameters using config
            search_params = {
                "metric_type": config.vector_store_config.metric_type,
                "params": {"nprobe": 10}
            }
            
            # Perform search
            results = self.collection.search(
                data=[vector],
                anns_field="vector",
                param=search_params,
                limit=limit,
                expr=filter_expr,
                output_fields=["id", "data_type", "db_id", "content", "question", "sql", "metadata_json"]
            )
            
            # Convert results to SearchResult objects
            search_results = []
            for hits in results:
                for hit in hits:
                    # Reconstruct metadata from stored fields
                    metadata = {
                        "data_type": hit.entity.get("data_type", ""),
                        "db_id": hit.entity.get("db_id", ""),
                        "content": hit.entity.get("content", ""),
                        "question": hit.entity.get("question", ""),
                        "sql": hit.entity.get("sql", ""),
                    }
                    
                    search_results.append(SearchResult(
                        id=hit.entity.get("id"),
                        score=hit.score,
                        metadata=metadata
                    ))
            
            logger.debug(f"Found {len(search_results)} similar vectors")
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            raise
    
    def delete(self, id: str):
        """
        Delete vector by id.
        
        Args:
            id: Unique identifier of the vector to delete
        """
        try:
            expr = f'id == "{id}"'
            self.collection.delete(expr)
            self.collection.flush()
            
            logger.debug(f"Deleted vector with id: {id}")
            
        except Exception as e:
            logger.error(f"Failed to delete vector {id}: {e}")
            raise
    
    def delete_by_filter(self, filter: Dict[str, Any]):
        """
        Delete vectors by filter conditions.
        
        Args:
            filter: Filter conditions
        """
        try:
            conditions = []
            for key, value in filter.items():
                if key in ["data_type", "db_id"]:
                    conditions.append(f'{key} == "{value}"')
            
            if conditions:
                expr = " and ".join(conditions)
                self.collection.delete(expr)
                self.collection.flush()
                
                logger.info(f"Deleted vectors with filter: {filter}")
            
        except Exception as e:
            logger.error(f"Failed to delete vectors with filter {filter}: {e}")
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            stats = self.collection.num_entities
            return {
                "total_entities": stats,
                "collection_name": self.collection_name,
                "dimension": self.dimension
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}
    
    def create_index(self, field_name: str = "vector", index_type: str = None, 
                     metric_type: str = None, params: Optional[Dict] = None):
        """
        Create or update index for better search performance.
        
        Args:
            field_name: Field to create index on
            index_type: Type of index (optional, will use config if not provided)
            metric_type: Distance metric (optional, will use config if not provided)
            params: Additional index parameters (optional, will use config if not provided)
        """
        try:
            if index_type is None:
                index_type = config.vector_store_config.index_type
            if metric_type is None:
                metric_type = config.vector_store_config.metric_type
            if params is None:
                params = {"nlist": config.vector_store_config.nlist}
            
            index_params = {
                "metric_type": metric_type,
                "index_type": index_type,
                "params": params
            }
            
            self.collection.create_index(
                field_name=field_name,
                index_params=index_params
            )
            
            logger.info(f"Created index on {field_name} with type {index_type}")
            
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise
    
    def close(self):
        """Close connection to Milvus."""
        try:
            if self.collection:
                self.collection.release()
            connections.disconnect("default")
            logger.info("Disconnected from Milvus")
        except Exception as e:
            logger.error(f"Error closing Milvus connection: {e}")


# Global vector store instance
vector_store = VectorStore()