"""
Embedding Service for Staples Brain.

This service provides vector embedding functionality for text using OpenAI's embedding API.
It supports semantic similarity calculations for agent routing and content retrieval.
"""
import logging
import os
import hashlib
from typing import Dict, List, Any, Optional

from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class EmbeddingConfig(BaseModel):
    """Configuration for embedding service"""
    model: str = "text-embedding-ada-002"  # OpenAI embedding model
    dimensions: int = 1536  # Default dimensions for OpenAI Ada embeddings
    cache_embeddings: bool = True  # Whether to cache embeddings


class EmbeddingService:
    """
    Service for generating text embeddings and calculating semantic similarity.
    
    This service wraps OpenAI's embedding API to provide vector representations
    of text for semantic similarity calculations and retrieval.
    """
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        """
        Initialize the embedding service.
        
        Args:
            config: Optional configuration for the service
        """
        self.config = config or EmbeddingConfig()
        self.api_key = os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in environment. Embeddings will not work.")
        
        # Initialize the embedding model
        self.embeddings = OpenAIEmbeddings(
            model=self.config.model,
            openai_api_key=self.api_key
        )
        
        # Cache for embeddings
        self._embedding_cache: Dict[str, List[float]] = {}
        
        logger.info(f"Initialized EmbeddingService with model {self.config.model}")
    
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.api_key:
            logger.error("Cannot generate embeddings: OPENAI_API_KEY not set")
            return [[0.0] * self.config.dimensions] * len(texts)
        
        results = []
        cache_hits = 0
        
        for text in texts:
            # Use cache if enabled
            if self.config.cache_embeddings:
                cache_key = self._get_cache_key(text)
                cached_embedding = self._embedding_cache.get(cache_key)
                
                if cached_embedding:
                    results.append(cached_embedding)
                    cache_hits += 1
                    continue
            
            # Not in cache, compute new embedding
            try:
                embedding = await self.embeddings.aembed_query(text)
                results.append(embedding)
                
                # Store in cache if enabled
                if self.config.cache_embeddings:
                    cache_key = self._get_cache_key(text)
                    self._embedding_cache[cache_key] = embedding
            except Exception as e:
                logger.error(f"Error generating embedding: {str(e)}")
                # Return a zero vector as fallback
                results.append([0.0] * self.config.dimensions)
        
        if cache_hits > 0:
            logger.debug(f"Embedding cache hits: {cache_hits}/{len(texts)}")
            
        return results
        
    async def get_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        embeddings = await self.get_embeddings([text])
        return embeddings[0]
    
    def _get_cache_key(self, text: str) -> str:
        """Generate a cache key for a text string"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()