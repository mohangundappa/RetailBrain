"""
Agent registry for the orchestration system.
This module provides centralized agent management and access.
"""
import logging
from typing import Dict, List, Optional, Any, Type, Callable

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for managing agents in the system."""
    
    def __init__(self):
        """Initialize an empty agent registry."""
        self.agents = {}  # Map of agent_id to agent instance
        self.factory_methods = {}  # Map of agent_type to factory method
        
    def register(self, agent) -> None:
        """
        Register an agent with the system.
        
        Args:
            agent: Agent instance to register
        """
        self.agents[agent.id] = agent
        logger.info(f"Registered agent: {agent.name} (id: {agent.id})")
        
    def register_factory(self, agent_type: str, factory_method: Callable) -> None:
        """
        Register a factory method for creating agents.
        
        Args:
            agent_type: Type identifier for the agent
            factory_method: Function that creates an agent instance
        """
        self.factory_methods[agent_type] = factory_method
        logger.info(f"Registered factory method for agent type: {agent_type}")
        
    def create_agent(self, agent_type: str, *args, **kwargs):
        """
        Create an agent using a registered factory method.
        
        Args:
            agent_type: The type of agent to create
            *args: Positional arguments for the factory method
            **kwargs: Keyword arguments for the factory method
            
        Returns:
            Created agent instance
            
        Raises:
            ValueError: If agent_type has no registered factory method
        """
        if agent_type not in self.factory_methods:
            raise ValueError(f"No factory method registered for agent type: {agent_type}")
            
        factory = self.factory_methods[agent_type]
        agent = factory(*args, **kwargs)
        
        # Automatically register the created agent
        self.register(agent)
        
        return agent
        
    def get_by_id(self, agent_id: str):
        """
        Get agent by ID.
        
        Args:
            agent_id: The agent's unique identifier
            
        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_id)
        
    def get_by_name(self, name: str):
        """
        Get agent by name (case-insensitive).
        
        Args:
            name: The agent's name
            
        Returns:
            Agent instance or None if not found
        """
        name_lower = name.lower()
        for agent in self.agents.values():
            if agent.name.lower() == name_lower:
                return agent
        return None
        
    def get_all(self) -> List:
        """
        Get all registered agents.
        
        Returns:
            List of all agent instances
        """
        return list(self.agents.values())
        
    def get_agent_names(self) -> List[str]:
        """
        Get names of all registered agents.
        
        Returns:
            List of agent names
        """
        return [agent.name for agent in self.agents.values()]