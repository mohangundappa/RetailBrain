"""
Staples Brain Orchestration Engine.

This module provides the central orchestration layer for the Staples Brain system,
coordinating interactions between specialized agents and managing conversation state.
It serves as the "brain" in the AI super-brain system architecture.

The Orchestration Engine is responsible for:
1. Initializing and managing agent registry
2. Routing user requests to appropriate agents
3. Maintaining conversation context and state
4. Providing telemetry and monitoring capabilities
"""

import logging
import os
import importlib
from typing import Dict, Any, List, Optional, Union, Tuple

from backend.config.config import Config
from backend.orchestration.router import AgentRouter
from backend.orchestration.factory import AgentFactory
from backend.orchestration.telemetry import TelemetryManager
from backend.orchestration.state.persistence import StatePersistenceManager

logger = logging.getLogger(__name__)

class StaplesBrain:
    """
    Central orchestration engine for the Staples Brain system.
    
    This class serves as the integration layer between API endpoints and specialized agents,
    providing intelligent routing, state management, and agent coordination capabilities.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Staples Brain with configuration.
        
        Args:
            config: Optional configuration object. If None, uses default configuration.
        """
        self.config = config or Config()
        logger.info("Initializing Staples Brain with config: %s", self.config)
        
        # Initialize components
        self.telemetry = TelemetryManager()
        self.factory = AgentFactory(config=self.config)
        self.router = AgentRouter(config=self.config)
        self.state_manager = StatePersistenceManager()
        
        # Agent registry
        self.agents = {}
        self.initialize_agents()
        
    def initialize_agents(self) -> None:
        """
        Initialize all available agents from the registry.
        
        This loads all registered agents and makes them available for use.
        """
        logger.info("Initializing agents...")
        # Load agent registry from database or configuration
        agent_list = self.factory.list_available_agents()
        logger.info("Found %d available agents", len(agent_list))
        
        # Register agents with router
        for agent_id in agent_list:
            self.router.register_agent(agent_id)
            
        logger.info("Agent initialization complete")
        
    async def process_request(self, 
                        input_text: str, 
                        session_id: Optional[str] = None,
                        context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user request and route it to the appropriate agent.
        
        Args:
            input_text: User input text
            session_id: Optional session identifier for maintaining context
            context: Optional additional context for the request
            
        Returns:
            Agent response with metadata
        """
        context = context or {}
        logger.info("Processing request: '%s', session_id=%s", input_text[:50], session_id)
        
        # Create session if needed
        if not session_id:
            session_id = self.state_manager.create_session()
            logger.info("Created new session: %s", session_id)
        
        # Track telemetry
        event_id = self.telemetry.record_event(
            session_id=session_id,
            event_type="request",
            data={"input": input_text, "context": context}
        )
        
        try:
            # Select appropriate agent
            agent_id = self.router.select_agent(input_text, context)
            logger.info("Selected agent: %s for request", agent_id)
            
            # Get or create agent instance
            agent = self.factory.get_agent(agent_id)
            
            # Load session state if available
            state = self.state_manager.get_session_state(session_id) or {}
            
            # Process request with agent
            response = await agent.process(
                input_text=input_text, 
                session_id=session_id,
                state=state,
                context=context
            )
            
            # Update session state
            if response.get("state"):
                self.state_manager.update_session_state(
                    session_id=session_id,
                    state=response["state"]
                )
            
            # Record response in telemetry
            self.telemetry.record_event(
                session_id=session_id,
                event_type="response",
                parent_id=event_id,
                data={"agent_id": agent_id, "response": response.get("response")}
            )
            
            return {
                "success": True,
                "response": response.get("response", ""),
                "agent": agent_id,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.exception("Error processing request: %s", str(e))
            self.telemetry.record_event(
                session_id=session_id,
                event_type="error",
                parent_id=event_id,
                data={"error": str(e)}
            )
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }
    
    def list_agents(self) -> List[str]:
        """
        Get a list of all available agents.
        
        Returns:
            List of agent identifiers
        """
        return self.factory.list_available_agents()
    
    def get_agent_details(self, agent_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent details
        """
        return self.factory.get_agent_details(agent_id)
        
    def get_agent_by_name(self, agent_name: str) -> Any:
        """
        Get agent by its display name.
        
        Args:
            agent_name: Agent display name
            
        Returns:
            Agent instance
        """
        # Find agent ID by name
        agent_details = self.factory.list_agent_details()
        for agent_id, details in agent_details.items():
            if details.get("name") == agent_name:
                return self.factory.get_agent(agent_id)
        return None
    
    def get_telemetry(self, session_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """
        Get telemetry data for system monitoring.
        
        Args:
            session_id: Optional session to filter by
            limit: Maximum number of events to return
            
        Returns:
            Telemetry data
        """
        if session_id:
            return self.telemetry.get_session_events(session_id, limit)
        else:
            return self.telemetry.get_recent_sessions(limit)

# Global instance for singleton access
_brain_instance = None

def initialize_staples_brain(config: Optional[Config] = None) -> StaplesBrain:
    """
    Initialize or get the Staples Brain instance.
    
    This function uses a singleton pattern to ensure only one instance
    of the StaplesBrain exists in the application.
    
    Args:
        config: Optional configuration object
        
    Returns:
        StaplesBrain instance
    """
    global _brain_instance
    if _brain_instance is None:
        logger.info("Initializing Staples Brain...")
        _brain_instance = StaplesBrain(config)
        logger.info("Staples Brain initialized")
    return _brain_instance