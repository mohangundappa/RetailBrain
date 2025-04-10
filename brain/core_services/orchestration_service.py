"""
Orchestration service for Staples Brain.

This service handles the routing of requests to appropriate agents and
manages the execution flow of the overall system.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from brain.core_services.base_service import CoreService
from agents.base_agent import BaseAgent
from utils.memory import ConversationMemory
from utils.observability import record_agent_selection
from config.agent_constants import (
    INTENT_AGENT_MAPPING,
    DEFAULT_CONFIDENCE_THRESHOLD,
    HIGH_CONFIDENCE_THRESHOLD,
    CONTINUITY_BONUS
)

logger = logging.getLogger(__name__)

class OrchestrationService(CoreService):
    """
    Service for orchestrating agent selection and execution.
    
    This service routes requests to appropriate agents based on intent recognition
    and manages the conversation flow across multiple interactions.
    """
    
    def __init__(self, agents: Optional[List[BaseAgent]] = None):
        """
        Initialize the orchestration service.
        
        Args:
            agents: Optional list of agents to orchestrate
        """
        self.agents = agents or []
        self.agent_map = {}  # Map from agent_id to agent instance
        self.memories = {}  # Dictionary of session_id -> ConversationMemory
        self.agent_routing_history = {}  # Track routing history per session
        self.confidence_threshold = DEFAULT_CONFIDENCE_THRESHOLD
        self.fallback_threshold = DEFAULT_CONFIDENCE_THRESHOLD * 0.7  # 70% of default threshold 
        self.continuity_bonus = CONTINUITY_BONUS
        self.recency_window = 300  # Consider context from the last 5 minutes (in seconds)
        
        # Use intent to agent mapping from central constants
        self.intent_routing = INTENT_AGENT_MAPPING
        
        self.health_status = {"healthy": False, "last_check": None, "details": {}}
    
    def initialize(self) -> bool:
        """
        Initialize the orchestration service with required resources.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Register agents in the agent map
            for agent in self.agents:
                agent_id = agent.agent_id
                self.agent_map[agent_id] = agent
            
            logger.info(f"Orchestration service initialized with {len(self.agents)} agents")
            
            self.health_status["healthy"] = True
            self.health_status["last_check"] = datetime.now().isoformat()
            self.health_status["details"] = {
                "agent_count": len(self.agents),
                "registered_agents": list(self.agent_map.keys())
            }
            
            return True
            
        except Exception as e:
            error_message = f"Failed to initialize orchestration service: {str(e)}"
            logger.error(error_message)
            
            self.health_status["healthy"] = False
            self.health_status["last_check"] = datetime.now().isoformat()
            self.health_status["details"] = {"error": error_message}
            
            return False
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the orchestration service.
        
        Args:
            agent: Agent instance to register
        """
        agent_id = agent.agent_id
        if agent_id in self.agent_map:
            logger.warning(f"Agent with ID '{agent_id}' is already registered. Replacing.")
        
        self.agent_map[agent_id] = agent
        
        # Also add to the agents list if not already there
        if agent not in self.agents:
            self.agents.append(agent)
        
        logger.info(f"Registered agent: {agent_id}")
    
    def get_agent_by_id(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get an agent by its ID.
        
        Args:
            agent_id: Agent ID to retrieve
            
        Returns:
            Agent instance or None if not found
        """
        return self.agent_map.get(agent_id)
    
    def get_agent_by_intent(self, intent: str) -> Optional[BaseAgent]:
        """
        Get the appropriate agent for handling a specific intent.
        
        Args:
            intent: Intent to find agent for
            
        Returns:
            Agent instance or None if no matching agent
        """
        agent_id = self.intent_routing.get(intent)
        if not agent_id:
            logger.warning(f"No agent mapping found for intent: {intent}")
            return None
        
        agent = self.agent_map.get(agent_id)
        if not agent:
            logger.warning(f"No agent found for ID: {agent_id}")
            return None
        
        return agent
    
    def _get_memory(self, session_id: str) -> ConversationMemory:
        """
        Get or create a conversation memory for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Conversation memory instance
        """
        if session_id not in self.memories:
            self.memories[session_id] = ConversationMemory(session_id)
            self.agent_routing_history[session_id] = []
        
        return self.memories[session_id]
    
    async def route_request(self, 
                          session_id: str, 
                          user_input: str, 
                          intent_data: Dict[str, Any]) -> Tuple[BaseAgent, float]:
        """
        Route a request to the appropriate agent based on intent and context.
        
        Args:
            session_id: Session identifier
            user_input: User input text
            intent_data: Intent classification data
            
        Returns:
            Tuple of (selected agent, confidence score)
        """
        memory = self._get_memory(session_id)
        routing_history = self.agent_routing_history.get(session_id, [])
        
        intent = intent_data.get("intent", "none")
        base_confidence = intent_data.get("confidence", 0.0)
        
        # Get potential agent from intent
        agent = self.get_agent_by_intent(intent)
        
        # If no agent found for intent or confidence too low, use fallback
        if not agent or base_confidence < self.fallback_threshold:
            logger.info(f"No suitable agent found for intent '{intent}' with confidence {base_confidence}")
            return None, 0.0
        
        # Apply context-based adjustments to confidence
        adjusted_confidence = base_confidence
        
        # Check for conversation continuity - prefer the same agent if recent interactions
        if routing_history:
            recent_agent_id = routing_history[-1]
            recent_agent = self.get_agent_by_id(recent_agent_id)
            
            # Apply continuity bonus if this is the same agent and within time window
            last_routing_time = memory.get_working_memory("last_routing_time")
            if (recent_agent and recent_agent.agent_id == agent.agent_id and
                last_routing_time and 
                (datetime.now() - datetime.fromisoformat(last_routing_time)).total_seconds() < self.recency_window):
                
                adjusted_confidence += self.continuity_bonus
                logger.debug(f"Applied continuity bonus: +{self.continuity_bonus} to agent {agent.agent_id}")
        
        # Record the routing decision
        memory.update_working_memory("last_routing_time", datetime.now().isoformat())
        routing_history.append(agent.agent_id)
        self.agent_routing_history[session_id] = routing_history
        
        # Record agent selection for metrics
        record_agent_selection(agent.agent_id)
        
        return agent, adjusted_confidence
    
    async def process_with_agent(self, 
                               agent: BaseAgent, 
                               session_id: str, 
                               user_input: str, 
                               context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a request with a specific agent.
        
        Args:
            agent: Agent to process with
            session_id: Session identifier
            user_input: User input text
            context: Optional context data
            
        Returns:
            Agent response
        """
        memory = self._get_memory(session_id)
        
        # Add the user message to memory
        memory.add_message("user", user_input)
        
        # Process with agent
        response = await agent.process(user_input, memory, context or {})
        
        # Add the agent's response to memory
        if response and "response" in response:
            memory.add_message("assistant", response["response"])
        
        return response
    
    def clear_session(self, session_id: str) -> None:
        """
        Clear the session data for a specific session.
        
        Args:
            session_id: Session identifier to clear
        """
        if session_id in self.memories:
            del self.memories[session_id]
        
        if session_id in self.agent_routing_history:
            del self.agent_routing_history[session_id]
        
        logger.info(f"Cleared session data for {session_id}")
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the service.
        
        Returns:
            Dictionary containing service metadata
        """
        return {
            "name": "orchestration_service",
            "description": "Agent orchestration and routing service",
            "version": "1.0.0",
            "registered_agents": list(self.agent_map.keys()),
            "active_sessions": len(self.memories),
            "health_status": self.health_status
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the service.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            # Update health check time
            self.health_status["last_check"] = datetime.now().isoformat()
            
            # Check if agents are registered
            if not self.agent_map:
                self.health_status["healthy"] = False
                self.health_status["details"] = {"error": "No agents registered"}
                return self.health_status
            
            # Could perform deeper checks on each agent
            # For now, we just verify agents are registered
            agent_status = {}
            for agent_id, agent in self.agent_map.items():
                agent_status[agent_id] = {
                    "initialized": agent is not None,
                    "type": type(agent).__name__ if agent else "Unknown"
                }
            
            self.health_status["healthy"] = True
            self.health_status["details"] = {
                "agent_count": len(self.agent_map),
                "agents": agent_status,
                "active_sessions": len(self.memories)
            }
            
            return self.health_status
            
        except Exception as e:
            error_message = f"Health check failed: {str(e)}"
            logger.error(error_message)
            
            self.health_status["healthy"] = False
            self.health_status["details"] = {"error": error_message}
            
            return self.health_status