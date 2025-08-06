"""
Embedding service for generating vector embeddings.
"""
import time
import uuid
from typing import List, Dict, Any, Optional
import logging

from utils.models import EmbeddingRequest, EmbeddingResponse
from config.settings import config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """OpenAI embedding service for production use."""
    
    def __init__(self):
        """Initialize embedding service.
        
        Args:
            api_key: OpenAI API key (optional, will use config if not provided)
            base_url: OpenAI API base URL (optional, will use config if not provided)
            model: Embedding model name (optional, will use config if not provided)
        """
        self.api_key = config.embedding_config.api_key
        self.base_url = config.embedding_config.base_url
        self.model = config.embedding_config.model
        self.dimension = config.embedding_config.dimension
        self.max_retries = config.embedding_config.max_retries
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Please set OPENAI_API_KEY environment variable.")
        
        try:
            import openai
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            self.client = openai.OpenAI(**client_kwargs)
            logger.info(f"Initialized OpenAI client with model: {self.model}, base_url: {self.base_url}")
        except ImportError:
            raise ImportError("OpenAI library not installed. Please install with: pip install openai")
    
    def generate_embedding(self, text: str, **kwargs) -> List[float]:
        """Generate embedding for a single text."""
        start_time = time.time()
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
                **kwargs
            )
            processing_time = time.time() - start_time
            
            logger.debug(f"Generated embedding for text (length: {len(text)}) in {processing_time:.3f}s")
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        start_time = time.time()
        
        try:
            # Process in batches to avoid API limits
            batch_size = config.embedding_config.batch_size
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    **kwargs
                )
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
            
            processing_time = time.time() - start_time
            logger.info(f"Generated {len(all_embeddings)} embeddings in {processing_time:.3f}s")
            return all_embeddings
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise
    
    def create_embedding_request(self, text: str, user_id: Optional[str] = None, 
                               metadata: Optional[Dict[str, Any]] = None) -> EmbeddingRequest:
        """Create an embedding request object."""
        return EmbeddingRequest(
            text=text,
            model=self.model,
            user_id=user_id,
            metadata=metadata or {}
        )
    
    def process_embedding_request(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Process an embedding request and return response."""
        start_time = time.time()
        request_id = str(uuid.uuid4())
        
        try:
            embedding = self.generate_embedding(request.text)
            processing_time = time.time() - start_time
            
            return EmbeddingResponse(
                embedding=embedding,
                model=request.model,
                usage={"total_tokens": len(request.text.split())},  # Approximate
                request_id=request_id,
                processing_time=processing_time
            )
        except Exception as e:
            logger.error(f"Failed to process embedding request {request_id}: {e}")
            raise
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get information about the current embedding service."""
        return {
            "model": self.model,
            "dimension": self.dimension,
            "max_tokens": 8192,
            "base_url": self.base_url,
            "service_type": "OpenAIEmbeddingService",
            "config": {
                "batch_size": config.embedding_config.batch_size,
                "max_retries": config.embedding_config.max_retries,
                "dimension": config.embedding_config.dimension
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the embedding service."""
        try:
            # Test with a simple text
            test_text = "Health check test"
            embedding = self.generate_embedding(test_text)
            
            return {
                "status": "healthy",
                "service_type": "OpenAIEmbeddingService",
                "model": self.model,
                "dimension": len(embedding),
                "base_url": self.base_url,
                "test_successful": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "test_successful": False
            }


# Global embedding service instance
embedding_service = EmbeddingService()