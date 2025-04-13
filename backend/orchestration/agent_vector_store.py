"""
Agent vector store for efficient agent selection and retrieval.
This module provides a specialized vector store for indexing, searching, and retrieving intelligent agents
using embedding-based semantic similarity and keyword matching.
"""
import logging
import numpy as np
import re
from typing import Dict, List, Optional, Any, Union, Tuple

from backend.orchestration.agent_definition import AgentDefinition
from backend.orchestration.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class AgentVectorStore:
    """
    Vector store for agent embeddings.
    
    This store:
    1. Manages agent embeddings
    2. Provides efficient search functionality
    3. Supports keyword-based filtering before embeddings
    """
    
    def __init__(self, embedding_service: EmbeddingService):
        """
        Initialize the agent vector store.
        
        Args:
            embedding_service: Embedding service for generating embeddings
        """
        self.embedding_service = embedding_service
        
        # Store agent definitions by ID
        self.agent_data: Dict[str, AgentDefinition] = {}
        
        # Store embeddings by agent ID
        self.agent_embeddings: Dict[str, List[float]] = {}
        
        logger.info("Initialized AgentVectorStore")
        
    def clear(self) -> None:
        """
        Clear all agents and embeddings from the vector store.
        This is useful when reloading agents from the database.
        """
        agent_count = len(self.agent_data)
        self.agent_data.clear()
        self.agent_embeddings.clear()
        logger.info(f"Cleared {agent_count} agents from vector store")
        
    async def index_agent(self, agent: AgentDefinition) -> bool:
        """
        Index an agent in the vector store.
        
        Args:
            agent: Agent to index
            
        Returns:
            True if successful
        """
        if not agent or not agent.id:
            logger.warning("Attempted to index invalid agent")
            return False
            
        try:
            # Get embedding text
            embedding_text = agent.get_embedding_text()
            
            # Generate embedding
            embedding = await self.embedding_service.get_embedding(embedding_text)
            
            # Store agent and embedding
            self.agent_data[agent.id] = agent
            self.agent_embeddings[agent.id] = embedding
            
            logger.info(f"Indexed agent: {agent.name} (ID: {agent.id})")
            logger.info(f"Agent data store now contains {len(self.agent_data)} agents")
            logger.info(f"Agent IDs in store: {list(self.agent_data.keys())}")
            return True
        except Exception as e:
            logger.error(f"Error indexing agent {agent.name}: {str(e)}")
            return False
            
    async def find_similar_agents(
        self,
        query: str,
        top_k: int = 3,
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Find agents that are semantically similar to the query.
        
        Args:
            query: Query to find similar agents for
            top_k: Maximum number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of similar agents with similarity scores
        """
        if not query:
            logger.warning("Empty query provided to find_similar_agents")
            return []
            
        if not self.agent_embeddings:
            logger.warning("No agents indexed in the vector store")
            return []
            
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.get_embedding(query)
            
            # Calculate similarities
            similarities = []
            for agent_id, agent_embedding in self.agent_embeddings.items():
                similarity = self._cosine_similarity(query_embedding, agent_embedding)
                similarities.append((agent_id, similarity))
                
            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Filter by threshold and take top_k
            results = []
            for agent_id, similarity in similarities[:top_k]:
                if similarity >= threshold:
                    agent = self.agent_data[agent_id]
                    results.append({
                        "agent": agent,
                        "similarity": similarity
                    })
                    
            logger.info(f"Found {len(results)} similar agents for query: {query[:50]}...")
            return results
        except Exception as e:
            logger.error(f"Error finding similar agents: {str(e)}")
            return []
            
    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            v1: First vector
            v2: Second vector
            
        Returns:
            Cosine similarity
        """
        # Convert to numpy arrays for efficient calculation
        a = np.array(v1)
        b = np.array(v2)
        
        # Calculate dot product and norms
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        # Calculate cosine similarity
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)
        
    async def keyword_prefilter(
        self,
        query: str,
        threshold: float = 0.3
    ) -> List[Tuple[AgentDefinition, float]]:
        """
        Prefilter agents by keyword matching before embedding.
        
        Args:
            query: User query
            threshold: Minimum confidence threshold
            
        Returns:
            List of (agent, confidence) tuples
        """
        if not query:
            return []
            
        results = []
        
        for agent_id, agent in self.agent_data.items():
            # Initialize confidence to 0
            max_confidence = 0.0
            
            # Check each capability for pattern matches
            for capability in agent.capabilities:
                if hasattr(capability, 'matches'):
                    confidence = capability.matches(query)
                    max_confidence = max(max_confidence, confidence)
                    
            # If we have a high enough confidence, include in results
            if max_confidence >= threshold:
                results.append((agent, max_confidence))
                
        # Sort by confidence (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Keyword prefilter found {len(results)} agents for: {query[:50]}...")
        return results