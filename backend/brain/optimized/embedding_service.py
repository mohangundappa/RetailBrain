"""
Optimized Embedding Service for Staples Brain.
This service provides efficient embedding generation with caching.
"""
import hashlib
import logging
import os
from typing import Dict, List, Optional, Union

import openai
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Service for efficient generation and caching of embeddings.
    
    This service provides:
    1. In-memory caching of embeddings
    2. Consistent embedding generation
    3. Potential for future batching optimization
    """
    
    def __init__(self, model: str = "text-embedding-ada-002", cache_size: int = 1000):
        """
        Initialize the embedding service.
        
        Args:
            model: The embedding model to use
            cache_size: Maximum number of items to keep in the cache
        """
        self.model = model
        self.cache_size = cache_size
        self.cache: Dict[str, List[float]] = {}
        
        # Initialize OpenAI client
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not found in environment")
        
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info(f"Initialized EmbeddingService with model {model}")
    
    def _get_cache_key(self, text: str) -> str:
        """
        Generate a cache key for the text.
        
        Args:
            text: Text to generate key for
            
        Returns:
            str: Cache key
        """
        # Use MD5 for fast hashing (not for security)
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    async def get_embedding(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Get embedding for text with caching.
        
        Args:
            text: Text or list of texts to embed
            
        Returns:
            Embedding vector or list of vectors
        """
        # Handle list input
        if isinstance(text, list):
            # For lists, we'll handle each item separately for now
            # Future optimization: batch API calls
            results = []
            for item in text:
                result = await self.get_embedding(item)
                results.append(result)
            return results
        
        # Check cache for single text input
        cache_key = self._get_cache_key(text)
        if cache_key in self.cache:
            logger.debug(f"Cache hit for embedding: {text[:30]}...")
            return self.cache[cache_key]
        
        # Generate new embedding
        try:
            logger.debug(f"Generating embedding for: {text[:30]}...")
            response = await self.client.embeddings.create(
                model=self.model,
                input=text
            )
            embedding = response.data[0].embedding
            
            # Cache the result
            self.cache[cache_key] = embedding
            
            # Simple cache size management
            if len(self.cache) > self.cache_size:
                # Remove random key (first one) if cache is full
                self.cache.pop(next(iter(self.cache)))
            
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            # Return empty embedding in case of error
            return [0.0] * 1536  # Default dimension for text-embedding-ada-002