"""
Orchestration Engine for Intelligent Agent System.

This module provides the central orchestration layer for the system,
coordinating interactions between specialized agents and managing conversation state.
It serves as the core intelligence coordination layer in the system architecture.

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
from backend.orchestration.router import OptimizedAgentRouter as AgentRouter
from backend.orchestration.factory import OptimizedAgentFactory as AgentFactory
from backend.orchestration.telemetry import TelemetryManager
from backend.orchestration.state.persistence import StatePersistenceManager

logger = logging.getLogger(__name__)

class OrchestrationEngine:
    """
    Central orchestration engine for the intelligent agent system.
    
    This class serves as the integration layer between API endpoints and specialized agents,
    providing intelligent routing, state management, and agent coordination capabilities.
    """
    
    def __init__(self, config: Optional[Config] = None, db_session=None):
        """
        Initialize the Orchestration Engine with configuration.
        
        Args:
            config: Optional configuration object. If None, uses default configuration.
            db_session: Database session
        """
        self.config = config or Config()
        logger.info("Initializing Orchestration Engine with config: %s", self.config)
        
        # Initialize components
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from backend.database.db import get_db
        from backend.api_gateway import get_sanitized_db_url
        
        if db_session is None:
            # Create a database session if none is provided
            db_url = get_sanitized_db_url()
            engine = create_async_engine(db_url)
            db_session = AsyncSession(engine)
        
        # Initialize services
        from backend.orchestration.embedding_service import EmbeddingService
        from backend.orchestration.vector_store import AgentVectorStore
        from backend.orchestration.telemetry import TelemetryManager
        
        embedding_service = EmbeddingService()
        agent_vector_store = AgentVectorStore(embedding_service)
        
        self.telemetry = TelemetryManager()
        self.factory = AgentFactory(db_session=db_session)
        self.router = AgentRouter(agent_vector_store=agent_vector_store, embedding_service=embedding_service)
        self.state_manager = StatePersistenceManager(db_session=db_session)
        
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
_engine_instance = None

def initialize_orchestration_engine(config: Optional[Config] = None) -> OrchestrationEngine:
    """
    Initialize or get the Orchestration Engine instance.
    
    This function uses a singleton pattern to ensure only one instance
    of the OrchestrationEngine exists in the application.
    
    Args:
        config: Optional configuration object
        
    Returns:
        OrchestrationEngine instance
    """
    global _engine_instance
    if _engine_instance is None:
        logger.info("Initializing Orchestration Engine...")
        _engine_instance = OrchestrationEngine(config)
        logger.info("Orchestration Engine initialized")
    return _engine_instance