"""
Vector Store for optimized agent selection.
This module provides a vector store for agent embedding storage and similarity search.
"""
import logging
import numpy as np
from typing import Dict, List, Optional, Union, Any, Tuple

from backend.brain.optimized.agent_definition import AgentDefinition
from backend.brain.optimized.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        v1: First vector
        v2: Second vector
        
    Returns:
        Similarity score between 0 and 1
    """
    v1_array = np.array(v1)
    v2_array = np.array(v2)
    
    dot_product = np.dot(v1_array, v2_array)
    norm_v1 = np.linalg.norm(v1_array)
    norm_v2 = np.linalg.norm(v2_array)
    
    # Avoid division by zero
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
        
    similarity = dot_product / (norm_v1 * norm_v2)
    
    # Ensure value is between 0 and 1
    return max(0.0, min(1.0, similarity))


class AgentVectorStore:
    """
    Vector store for agent selection optimization.
    
    This class provides:
    1. Storage for agent embeddings
    2. Semantic search for finding similar agents
    3. Vector similarity calculations
    """
    
    def __init__(self, embedding_service: EmbeddingService):
        """
        Initialize the agent vector store.
        
        Args:
            embedding_service: Service for generating embeddings
        """
        self.embedding_service = embedding_service
        self.vector_db: Dict[str, List[float]] = {}  # agent_id -> embedding
        self.agent_data: Dict[str, AgentDefinition] = {}  # agent_id -> agent
        logger.info("Initialized AgentVectorStore")
        
    async def index_agent(self, agent: AgentDefinition) -> bool:
        """
        Index an agent in the vector store.
        
        Args:
            agent: Agent definition to index
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate the comprehensive text representation
            text_rep = agent.get_text_representation()
            
            # Generate embedding (cached by the embedding service)
            embedding = await self.embedding_service.get_embedding(text_rep)
            
            # Store in vector database
            self.vector_db[agent.id] = embedding
            self.agent_data[agent.id] = agent
            
            logger.info(f"Indexed agent '{agent.name}' (ID: {agent.id}) in vector store")
            return True
        except Exception as e:
            logger.error(f"Error indexing agent {agent.name}: {str(e)}")
            return False
        
    async def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the vector store.
        
        Args:
            agent_id: ID of the agent to remove
            
        Returns:
            True if agent was removed, False otherwise
        """
        if agent_id in self.vector_db:
            del self.vector_db[agent_id]
            agent_name = self.agent_data[agent_id].name if agent_id in self.agent_data else "Unknown"
            if agent_id in self.agent_data:
                del self.agent_data[agent_id]
            logger.info(f"Removed agent '{agent_name}' (ID: {agent_id}) from vector store")
            return True
        else:
            logger.warning(f"Agent ID {agent_id} not found in vector store")
            return False
        
    async def update_agent(self, agent: AgentDefinition) -> bool:
        """
        Update an existing agent in the vector store.
        
        Args:
            agent: Updated agent definition
            
        Returns:
            True if successful, False otherwise
        """
        # Just reindex the agent
        return await self.index_agent(agent)
        
    async def find_similar_agents(
        self,
        query: str,
        top_k: int = 3,
        threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Find agents that might handle the query.
        
        Args:
            query: User query to match
            top_k: Number of top results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of dictionaries with agent info and similarity scores
        """
        # If no agents, return empty list
        if not self.vector_db:
            logger.warning("No agents in vector store to search")
            return []
            
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.get_embedding(query)
            
            # Calculate similarities
            similarities = []
            for agent_id, agent_embedding in self.vector_db.items():
                similarity = cosine_similarity(query_embedding, agent_embedding)
                similarities.append((agent_id, similarity))
                
            # Sort by similarity score
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Return top k results above threshold
            return [
                {
                    "id": agent_id,
                    "similarity": score,
                    "agent": self.agent_data[agent_id]
                }
                for agent_id, score in similarities[:top_k]
                if score >= threshold
            ]
        except Exception as e:
            logger.error(f"Error finding similar agents: {str(e)}")
            return []
            
    async def keyword_prefilter(
        self,
        query: str
    ) -> List[Tuple[AgentDefinition, float]]:
        """
        Fast pre-filtering using keywords.
        
        This method uses simple keyword matching to quickly filter out agents that
        are unlikely to handle the query, avoiding unnecessary embedding calculations.
        
        Args:
            query: User query to match
            
        Returns:
            List of tuples with agent and confidence score
        """
        results = []
        query_lower = query.lower()
        
        for agent_id, agent in self.agent_data.items():
            matched = False
            confidence = 0.0
            
            # Check agent name
            if agent.name.lower() in query_lower:
                matched = True
                confidence = max(confidence, 0.8)
                
            # Check keywords from patterns
            for capability in agent.capabilities:
                if not hasattr(capability, 'patterns'):
                    continue
                    
                for pattern in capability.patterns:
                    if pattern.get("type") == "keyword":
                        keyword = pattern.get("value", "").lower()
                        if keyword and keyword in query_lower:
                            matched = True
                            boost = pattern.get("confidence_boost", 0.1)
                            confidence = max(confidence, 0.7 + boost)
                    elif pattern.get("type") == "regex":
                        # Simple regex check (could be enhanced)
                        import re
                        regex = pattern.get("value", "")
                        try:
                            if regex and re.search(regex, query, re.IGNORECASE):
                                matched = True
                                boost = pattern.get("confidence_boost", 0.1)
                                confidence = max(confidence, 0.7 + boost)
                        except Exception:
                            # Ignore regex errors
                            pass
            
            if matched:
                results.append((agent, confidence))
                
        # Sort by confidence
        results.sort(key=lambda x: x[1], reverse=True)
        return results