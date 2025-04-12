"""
Optimized router for agent selection.
This module provides an optimized router that efficiently selects the best agent for a user query.
"""
import logging
import re
from typing import Dict, List, Optional, Tuple, Any, Union

from backend.brain.optimized.agent_definition import AgentDefinition
from backend.brain.optimized.embedding_service import EmbeddingService
from backend.brain.optimized.vector_store import AgentVectorStore

logger = logging.getLogger(__name__)


class OptimizedAgentRouter:
    """
    Router that efficiently selects the best agent for a query.
    
    This router:
    1. Uses a multi-stage selection process
    2. Applies fast pre-filtering before expensive operations
    3. Makes minimal embedding API calls
    4. Supports conversation context for continuity
    """
    
    def __init__(
        self,
        agent_vector_store: AgentVectorStore,
        embedding_service: EmbeddingService,
        memory_service: Optional[Any] = None
    ):
        """
        Initialize the optimized agent router.
        
        Args:
            agent_vector_store: Vector store for agent embeddings
            embedding_service: Service for generating embeddings
            memory_service: Optional service for conversation memory
        """
        self.agent_vector_store = agent_vector_store
        self.embedding_service = embedding_service
        self.memory_service = memory_service
        logger.info("Initialized OptimizedAgentRouter")
        
    async def route(
        self,
        query: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[AgentDefinition], float, Dict[str, Any]]:
        """
        Route a query to the best agent.
        
        Args:
            query: User query to route
            session_id: Optional session ID for context
            context: Optional additional context
            
        Returns:
            Tuple of (selected agent, confidence, context)
        """
        if not query:
            logger.warning("Empty query provided to router")
            return None, 0.0, context or {}
            
        # Initialize context if not provided
        context = context or {}
        used_context = dict(context)
        
        # Check for conversation continuity if session provided
        if session_id and self.memory_service:
            continuity_result = await self._check_continuity(query, session_id, context)
            if continuity_result:
                agent, confidence, continuity_context = continuity_result
                logger.info(f"Using continuity: Selected '{agent.name}' with confidence {confidence:.2f}")
                used_context.update(continuity_context)
                return agent, confidence, used_context
                
        # Fast pre-filtering using keywords (derived from agent patterns)
        # This avoids unnecessary embedding API calls
        prefiltered_agents = await self.agent_vector_store.keyword_prefilter(query)
        if prefiltered_agents:
            # If we have exactly one high-confidence match, use it directly
            if len(prefiltered_agents) == 1 and prefiltered_agents[0][1] > 0.8:
                agent, confidence = prefiltered_agents[0]
                logger.info(f"Keyword match: Selected '{agent.name}' with confidence {confidence:.2f}")
                used_context["selection_method"] = "keyword_match"
                return agent, confidence, used_context
            
            # If we have multiple potential matches but one is clearly higher confidence
            elif len(prefiltered_agents) > 1 and prefiltered_agents[0][1] > 0.9 and prefiltered_agents[0][1] - prefiltered_agents[1][1] > 0.3:
                agent, confidence = prefiltered_agents[0]
                logger.info(f"High-confidence keyword match: Selected '{agent.name}' with confidence {confidence:.2f}")
                used_context["selection_method"] = "high_confidence_keyword"
                return agent, confidence, used_context
                
            # Otherwise, use the prefiltered agents as candidates for semantic search
            logger.info(f"Prefiltered to {len(prefiltered_agents)} agents, using semantic search")
            used_context["prefilter_candidates"] = len(prefiltered_agents)
            
            # Extract just the agent IDs for semantic search
            prefiltered_ids = [agent.id for agent, _ in prefiltered_agents]
            
            # Proceed with semantic search limited to prefiltered agents
            similar_results = await self._semantic_search(query, limit_to_ids=prefiltered_ids)
        else:
            # No candidates from prefiltering, use full semantic search
            logger.info("No keyword matches, using full semantic search")
            similar_results = await self._semantic_search(query)
        
        # Process semantic search results
        if similar_results:
            best_match = similar_results[0]
            agent = best_match["agent"]
            similarity = best_match["similarity"]
            logger.info(f"Semantic match: Selected '{agent.name}' with similarity {similarity:.2f}")
            used_context["selection_method"] = "semantic_match"
            return agent, similarity, used_context
        
        # If no agent found, return None
        logger.warning("No suitable agent found for query")
        return None, 0.0, used_context
    
    async def _semantic_search(
        self,
        query: str,
        limit_to_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search for similar agents.
        
        Args:
            query: User query
            limit_to_ids: Optional list of agent IDs to search within
            
        Returns:
            List of match results
        """
        # If we have a limited list of IDs, filter the vector store
        if limit_to_ids is not None and limit_to_ids:
            # Use a temporary in-memory filtered copy
            filtered_store = AgentVectorStore(self.embedding_service)
            for agent_id in limit_to_ids:
                if agent_id in self.agent_vector_store.agent_data:
                    await filtered_store.index_agent(self.agent_vector_store.agent_data[agent_id])
            
            # Search in the filtered store
            return await filtered_store.find_similar_agents(query, top_k=3, threshold=0.5)
        else:
            # Search in the full store
            return await self.agent_vector_store.find_similar_agents(query, top_k=3, threshold=0.5)
            
    async def _check_continuity(
        self,
        query: str,
        session_id: str,
        context: Dict[str, Any]
    ) -> Optional[Tuple[AgentDefinition, float, Dict[str, Any]]]:
        """
        Check for conversation continuity.
        
        Args:
            query: User query
            session_id: Session ID
            context: Current context
            
        Returns:
            Tuple of (agent, confidence, context) if continuity detected, None otherwise
        """
        if not self.memory_service:
            return None
            
        try:
            # Get conversation context from memory service
            conversation = await self.memory_service.get_conversation(session_id)
            if not conversation:
                return None
                
            # Check if we have a last agent
            last_agent_id = conversation.get("last_agent_id")
            if not last_agent_id or last_agent_id not in self.agent_vector_store.agent_data:
                return None
                
            # Get the agent
            agent = self.agent_vector_store.agent_data[last_agent_id]
            
            # Check if the query seems related to the current topic
            current_topic = conversation.get("current_topic", "")
            if current_topic and self._is_same_topic(query, current_topic):
                # Apply continuity bonus
                continuity_confidence = 0.75  # High confidence for continuing conversation
                continuity_context = {"continuity_from": last_agent_id, "current_topic": current_topic}
                return agent, continuity_confidence, continuity_context
        except Exception as e:
            logger.error(f"Error checking continuity: {str(e)}")
            
        return None
    
    def _is_same_topic(self, query: str, current_topic: str) -> bool:
        """
        Check if the new query is likely on the same topic.
        
        Args:
            query: User query
            current_topic: Current conversation topic
            
        Returns:
            True if likely the same topic, False otherwise
        """
        # Simple topic matching based on common keywords
        query_words = set(re.findall(r'\b\w+\b', query.lower()))
        topic_words = set(re.findall(r'\b\w+\b', current_topic.lower()))
        
        # Remove common stop words
        stop_words = {"the", "and", "to", "a", "of", "for", "in", "is", "it", "that", "with", "my"}
        query_words = query_words - stop_words
        topic_words = topic_words - stop_words
        
        if not query_words or not topic_words:
            return False
            
        # Calculate word overlap
        common_words = query_words.intersection(topic_words)
        overlap_ratio = len(common_words) / min(len(query_words), len(topic_words))
        
        # Check for continuity markers
        continuity_markers = {"also", "additionally", "furthermore", "moreover", "and", "what about", "how about"}
        has_markers = any(marker in query.lower() for marker in continuity_markers)
        
        return overlap_ratio >= 0.3 or has_markers
    
    async def route_and_prepare(
        self,
        query: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[AgentDefinition], float, Dict[str, Any]]:
        """
        Route a query and prepare context for the agent.
        
        Args:
            query: User query
            session_id: Optional session ID
            context: Optional additional context
            
        Returns:
            Tuple of (agent, confidence, prepared_context)
        """
        # Route to best agent
        agent, confidence, route_context = await self.route(query, session_id, context)
        
        if not agent:
            return None, 0.0, route_context
            
        # Extract entities for the selected agent
        entities = await self._extract_entities(query, agent)
        
        # Prepare context
        prepared_context = {
            **route_context,
            "extracted_entities": entities,
            "confidence": confidence,
            "session_id": session_id
        }
        
        return agent, confidence, prepared_context
    
    async def _extract_entities(
        self,
        query: str,
        agent: AgentDefinition
    ) -> Dict[str, Any]:
        """
        Extract entities from the query for the selected agent.
        
        Args:
            query: User query
            agent: Selected agent
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        
        # For each entity definition in the agent
        for entity_def in agent.entity_definitions:
            # Extract entity based on type
            if entity_def.entity_type == "email":
                # Use regex to find emails
                matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', query)
                if matches:
                    entities[entity_def.name] = matches[0]
            elif entity_def.validation_regex:
                # Use custom regex if provided
                try:
                    matches = re.findall(entity_def.validation_regex, query)
                    if matches:
                        entities[entity_def.name] = matches[0]
                except Exception as e:
                    logger.error(f"Error in regex extraction: {str(e)}")
            # Add more entity extraction methods as needed
        
        return entities