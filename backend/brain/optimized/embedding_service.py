"""
Embedding service for efficient agent selection.
This module provides a service for generating and caching embeddings.
"""
import logging
import time
from typing import Dict, List, Optional, Any, Union, Tuple

import numpy as np
from openai import OpenAI
from openai.types.embeddings import Embedding

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating and caching embeddings.
    
    This service:
    1. Generates embeddings using the OpenAI API
    2. Caches embeddings to minimize API calls
    3. Manages cache eviction and persistence
    """
    
    def __init__(self, model: str = "text-embedding-3-small"):
        """
        Initialize the embedding service.
        
        Args:
            model: OpenAI embedding model to use
        """
        # Initialize the OpenAI client
        self.client = OpenAI()
        self.model = model
        
        # Cache for embeddings
        self.cache: Dict[str, Tuple[List[float], float]] = {}
        self.api_calls = 0
        self.cache_hits = 0
        
        logger.info(f"Initialized EmbeddingService with model {model}")
        
    async def get_embedding(self, text: str) -> List[float]:
        """
        Get an embedding for the given text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        if not text:
            logger.warning("Empty text provided for embedding")
            # Return a zero vector
            return [0.0] * 1536  # Default embedding dimension
            
        # Check cache first
        cache_key = self._get_cache_key(text)
        if cache_key in self.cache:
            self.cache_hits += 1
            embedding, _ = self.cache[cache_key]
            logger.debug(f"Cache hit for text: {text[:50]}... (hits: {self.cache_hits})")
            return embedding
            
        # Generate embedding
        try:
            start_time = time.time()
            response = self.client.embeddings.create(
                model=self.model,
                input=[text],
                dimensions=1536
            )
            embedding = response.data[0].embedding
            self.api_calls += 1
            
            # Cache the result
            self.cache[cache_key] = (embedding, time.time())
            
            logger.info(f"Generated embedding in {time.time() - start_time:.2f}s (API calls: {self.api_calls})")
            
            # Prune cache if needed
            if len(self.cache) > 1000:
                self._prune_cache()
                
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            # Return a random vector as fallback
            return self._generate_random_embedding()
            
    def _get_cache_key(self, text: str) -> str:
        """
        Generate a cache key for the given text.
        
        Args:
            text: Text to generate key for
            
        Returns:
            Cache key
        """
        # Simple hashing for now - could use more sophisticated approach if needed
        return f"{self.model}_{hash(text)}"
        
    def _prune_cache(self, max_size: int = 500):
        """
        Prune the cache to the specified size.
        
        Args:
            max_size: Maximum number of entries to keep
        """
        if len(self.cache) <= max_size:
            return
            
        # Sort by timestamp (oldest first)
        sorted_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k][1])
        
        # Remove oldest entries
        to_remove = sorted_keys[:len(self.cache) - max_size]
        for key in to_remove:
            del self.cache[key]
            
        logger.info(f"Pruned embedding cache from {len(self.cache) + len(to_remove)} to {len(self.cache)} entries")
        
    def _generate_random_embedding(self, dimension: int = 1536) -> List[float]:
        """
        Generate a random embedding as a fallback.
        
        Args:
            dimension: Embedding dimension
            
        Returns:
            Random embedding vector
        """
        # Generate random vector and normalize it
        vector = np.random.randn(dimension).astype(np.float32)
        vector = vector / np.linalg.norm(vector)
        
        logger.warning("Using fallback random embedding")
        return vector.tolist()
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the embedding service.
        
        Returns:
            Dictionary of statistics
        """
        cache_hit_rate = 0.0
        if self.api_calls + self.cache_hits > 0:
            cache_hit_rate = self.cache_hits / (self.api_calls + self.cache_hits)
            
        return {
            "api_calls": self.api_calls,
            "cache_hits": self.cache_hits,
            "cache_size": len(self.cache),
            "cache_hit_rate": cache_hit_rate,
            "model": self.model
        }