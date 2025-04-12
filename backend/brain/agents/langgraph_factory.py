"""
Factory for creating LangGraph agents from agent definitions.

This module provides a factory class that can create LangGraph agents
from agent definitions stored in the database.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from backend.brain.agents.langgraph_agent import LangGraphAgent
from backend.repositories.agent_repository import AgentRepository

logger = logging.getLogger(__name__)


class DefaultLangGraphAgent(LangGraphAgent):
    """
    Default implementation of LangGraphAgent for testing and fallback.
    
    This agent provides basic functionality for the orchestration system
    and returns specialized responses based on its type and input.
    """
    
    def __init__(self, id: str, name: str, description: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize a default LangGraph agent.
        
        Args:
            id: Unique identifier for the agent
            name: Display name of the agent
            description: Description of the agent's purpose
            config: Optional configuration parameters
        """
        self.id = id
        self.name = name
        self.description = description
        self.config = config or {}
        self._tools = [] if not hasattr(self, '_tools') else self._tools
        self._metrics = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "avg_response_time": 0
        }
    
    def process(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message synchronously and generate an appropriate response.
        This is a non-async version for use with the LangGraph orchestrator.
        
        Args:
            message: User input message
            context: Additional context information
            
        Returns:
            Dictionary containing the response and metadata
        """
        import time
        start_time = time.time()
        
        # For testing, generate a contextual response based on the agent type and message
        if "package" in self.id or "package" in message.lower():
            response_text = (
                "I'll help you track your package. To get started, I'll need your tracking number. "
                "You can find this in your order confirmation email or on your receipt."
            )
        elif "password" in self.id or "reset" in message.lower():
            response_text = (
                "I can help you reset your password. To protect your account, "
                "I'll need to verify your identity first. Please provide your email address."
            )
        elif "store" in self.id or "location" in message.lower():
            response_text = (
                "I can help you find the nearest Staples store. "
                "Could you please share your zip code or city and state?"
            )
        else:
            response_text = (
                f"I'm the {self.name}. {self.description} "
                "How can I assist you today?"
            )
            
        # Create the response object
        response = {
            "response": response_text,
            "agent": self.name,
            "confidence": 0.9,  # High confidence for demo purposes
            "metadata": {
                "agent_id": self.id,
                "agent_name": self.name,
                "agent_type": "default",
                "processed_at": time.time()
            }
        }
        
        # Update metrics
        elapsed_time = time.time() - start_time
        self.update_metrics(success=True, response_time=elapsed_time)
        
        return response
        
    async def process(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a message asynchronously and generate an appropriate response.
        
        Args:
            message: User input message
            context: Additional context information
            
        Returns:
            Dictionary containing the response and metadata
        """
        # For the default agent, we just call the synchronous version
        # In a real implementation, this would be properly async
        # Note that we aren't awaiting anything here because the synchronous version
        # does everything we need
        return self.process(message, context)
    
    def update_metrics(self, success: bool, response_time: float) -> None:
        """
        Update agent metrics.
        
        Args:
            success: Whether the processing was successful
            response_time: Time taken to generate the response
        """
        self._metrics["total_calls"] += 1
        if success:
            self._metrics["successful_calls"] += 1
        else:
            self._metrics["failed_calls"] += 1
            
        # Update average response time
        avg_time = self._metrics["avg_response_time"]
        total_calls = self._metrics["total_calls"]
        self._metrics["avg_response_time"] = (avg_time * (total_calls - 1) + response_time) / total_calls
        
    def get_id(self) -> str:
        """
        Get the unique identifier for this agent.
        
        Returns:
            Agent ID
        """
        return self.id
        
    def get_name(self) -> str:
        """
        Get the display name of this agent.
        
        Returns:
            Agent name
        """
        return self.name
        
    def get_description(self) -> str:
        """
        Get the description of this agent.
        
        Returns:
            Agent description
        """
        return self.description
        
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get the tools available to this agent.
        
        Returns:
            List of tool configurations
        """
        return self._tools


class LangGraphAgentFactory:
    """
    Factory for creating and managing LangGraph agents.
    
    This class is responsible for creating agent instances from database records
    and maintaining the collection of available agents.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the factory with a database session.
        
        Args:
            db_session: Async database session
        """
        self.db_session = db_session
        self.agent_repository = AgentRepository(db_session)
        self.agents: Dict[str, LangGraphAgent] = {}
        
        logger.info("Initialized LangGraph agent factory")
    
    async def get_all_active_agents(self) -> List[LangGraphAgent]:
        """
        Get all active agents from the database.
        
        Returns:
            List of LangGraphAgent instances
        """
        try:
            # Get agent definitions from repository
            agent_definitions = await self.agent_repository.list_agents(
                status="active",  # Only active agents
                with_details=True  # Include all agent details
            )
            
            agents = []
            for agent_def in agent_definitions:
                try:
                    agent = await self.create_agent_from_definition(agent_def)
                    if agent:
                        agents.append(agent)
                        # Cache the agent
                        self.agents[agent.id] = agent
                except Exception as e:
                    logger.error(f"Error creating agent {agent_def.get('id', 'unknown')}: {str(e)}", exc_info=True)
            
            # If no agents were created, create a default agent
            if not agents:
                logger.warning("No agents found in database, creating default agent")
                default_agent = DefaultLangGraphAgent(
                    id="default-agent",
                    name="Default Agent",
                    description="A default agent that responds to all requests"
                )
                agents.append(default_agent)
                self.agents[default_agent.id] = default_agent
            
            logger.info(f"Loaded {len(agents)} agents from database")
            return agents
            
        except Exception as e:
            logger.error(f"Error getting active agents: {str(e)}", exc_info=True)
            # Return a default agent in case of error
            default_agent = DefaultLangGraphAgent(
                id="default-agent-error",
                name="Default Agent (Error Recovery)",
                description="A default agent created due to an error loading agents"
            )
            self.agents[default_agent.id] = default_agent
            return [default_agent]
    
    async def create_agent_from_definition(self, agent_def: Dict[str, Any]) -> Optional[LangGraphAgent]:
        """
        Create a LangGraphAgent instance from an agent definition.
        
        Args:
            agent_def: Agent definition dictionary
            
        Returns:
            LangGraphAgent instance or None if creation fails
        """
        try:
            agent_id = agent_def.get("id")
            agent_name = agent_def.get("name")
            agent_description = agent_def.get("description")
            agent_type = agent_def.get("agent_type", "default")
            
            if not agent_id or not agent_name:
                logger.error(f"Invalid agent definition: {agent_def}")
                return None
            
            # For now, create a default agent for all types
            # In the future, we can implement specialized agent classes based on type
            agent = DefaultLangGraphAgent(
                id=agent_id,
                name=agent_name,
                description=agent_description or f"Agent {agent_name}",
                config=agent_def
            )
            
            logger.info(f"Created agent {agent_name} with ID {agent_id}")
            return agent
            
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}", exc_info=True)
            return None
    
    async def get_agent_by_id(self, agent_id: str) -> Optional[LangGraphAgent]:
        """
        Get an agent by its ID.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            LangGraphAgent instance or None if not found
        """
        # Check cache first
        if agent_id in self.agents:
            return self.agents[agent_id]
        
        try:
            # Get agent definition from repository
            agent_def = await self.agent_repository.get_agent_by_id(agent_id)
            
            if not agent_def:
                logger.warning(f"Agent with ID {agent_id} not found")
                return None
            
            # Create agent from definition
            agent = await self.create_agent_from_definition(agent_def)
            
            # Cache the agent if created successfully
            if agent:
                self.agents[agent_id] = agent
            
            return agent
            
        except Exception as e:
            logger.error(f"Error getting agent by ID {agent_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_agent_by_name(self, agent_name: str) -> Optional[LangGraphAgent]:
        """
        Get an agent by its name.
        
        Args:
            agent_name: Agent name
            
        Returns:
            LangGraphAgent instance or None if not found
        """
        try:
            # Get agent definition from repository
            agent_def = await self.agent_repository.get_agent_by_name(agent_name)
            
            if not agent_def:
                logger.warning(f"Agent with name {agent_name} not found")
                return None
            
            agent_id = agent_def.get("id")
            
            # Check cache first
            if agent_id and agent_id in self.agents:
                return self.agents[agent_id]
            
            # Create agent from definition
            agent = await self.create_agent_from_definition(agent_def)
            
            # Cache the agent if created successfully
            if agent and agent_id:
                self.agents[agent_id] = agent
            
            return agent
            
        except Exception as e:
            logger.error(f"Error getting agent by name {agent_name}: {str(e)}", exc_info=True)
            return None