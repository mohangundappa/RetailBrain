"""
Factory for creating LangGraph agents from database definitions.

This module provides a factory class that can create LangGraph agents
from agent definitions stored in the database.
"""
import logging
import json
import sys
import os
from typing import Dict, Any, List, Optional, Union, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.agents.framework.langgraph.langgraph_agent import LangGraphAgent
from backend.agents.framework.langgraph.database_agent import (
    DatabaseAgent, 
    create_database_agent_from_model
)
from backend.repositories.agent_repository import AgentRepository
from backend.database.agent_schema import (
    AgentDefinition, AgentDeployment, AgentComposition,
    LlmAgentConfiguration, RuleAgentConfiguration, RetrievalAgentConfiguration,
    AgentPattern, AgentPatternEmbedding, AgentTool, AgentResponseTemplate
)

logger = logging.getLogger(__name__)


class LangGraphAgentFactory:
    """
    Factory for creating and managing LangGraph agents from database configurations.
    
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
        
    async def initialize(self) -> bool:
        """
        Initialize the agent factory and preload agents.
        
        Returns:
            bool: True if initialization was successful
        """
        try:
            # Load all active agents
            await self.load_all_active_agents()
            return True
        except Exception as e:
            logger.error(f"Error initializing LangGraphAgentFactory: {str(e)}", exc_info=True)
            return False
    
    async def load_all_active_agents(self) -> List[LangGraphAgent]:
        """
        Load all active agents from the database.
        
        Returns:
            List of LangGraphAgent instances
        """
        try:
            # Instead of loading from database, we'll create hardcoded agents for now
            # This is a temporary workaround until we fix the async database loading
            from backend.agents.framework.langgraph.simple_agent import SimpleAgent
            from uuid import uuid4
            
            # Create hardcoded agents for testing
            agents = []
            
            # General Conversation Agent
            general_agent = SimpleAgent(
                id=str(uuid4()),
                name="General Conversation Agent",
                description="Handles general conversation and queries",
                agent_type="LLM",
                config={
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "system_prompt": "You are a helpful assistant at Staples. Answer customer questions professionally and accurately."
                }
            )
            self.agents[general_agent.id] = general_agent
            agents.append(general_agent)
            logger.info(f"Created hardcoded agent: {general_agent.name} (ID: {general_agent.id})")
            
            # Guardrails Agent
            guardrails_agent = SimpleAgent(
                id=str(uuid4()),
                name="Guardrails Agent",
                description="Ensures responses meet content policy guidelines",
                agent_type="LLM",
                config={
                    "model": "gpt-4",
                    "temperature": 0.3,
                    "system_prompt": "You are a content safety system. Ensure responses do not contain harmful, offensive, or inappropriate content."
                }
            )
            self.agents[guardrails_agent.id] = guardrails_agent
            agents.append(guardrails_agent)
            logger.info(f"Created hardcoded agent: {guardrails_agent.name} (ID: {guardrails_agent.id})")
            
            logger.info(f"Successfully loaded {len(agents)} hardcoded agents")
            return agents
            
        except Exception as e:
            logger.error(f"Error loading active agents: {str(e)}", exc_info=True)
            return []
    
    async def get_agent_by_id(self, agent_id: str) -> Optional[LangGraphAgent]:
        """
        Get an agent by its ID. Loads from database if not in memory.
        
        Args:
            agent_id: The agent ID
            
        Returns:
            LangGraphAgent instance or None if not found
        """
        # Check if agent is already loaded
        if agent_id in self.agents:
            return self.agents[agent_id]
        
        # Try to load from database
        try:
            agent_def = await self.agent_repository.get_agent_definition(agent_id)
            if not agent_def:
                logger.warning(f"Agent with ID {agent_id} not found in database")
                return None
                
            agent = await create_database_agent_from_model(agent_def)
            if agent:
                # Add to registry
                self.agents[agent.id] = agent
                logger.info(f"Loaded agent from database: {agent.name} (ID: {agent.id})")
                return agent
            else:
                logger.error(f"Failed to create agent for {agent_def.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading agent {agent_id}: {str(e)}", exc_info=True)
            return None
    
    async def get_agent_by_name(self, name: str) -> Optional[LangGraphAgent]:
        """
        Get an agent by its name.
        
        Args:
            name: The agent name
            
        Returns:
            LangGraphAgent instance or None if not found
        """
        # Check if agent is already loaded
        for agent in self.agents.values():
            if agent.name.lower() == name.lower():
                return agent
        
        # Try to load from database
        try:
            agent_def = await self.agent_repository.get_agent_by_name(name)
            if not agent_def:
                logger.warning(f"Agent with name {name} not found in database")
                return None
                
            agent = await create_database_agent_from_model(agent_def)
            if agent:
                # Add to registry
                self.agents[agent.id] = agent
                logger.info(f"Loaded agent from database: {agent.name} (ID: {agent.id})")
                return agent
            else:
                logger.error(f"Failed to create agent for {name}")
                return None
                
        except Exception as e:
            logger.error(f"Error loading agent {name}: {str(e)}", exc_info=True)
            return None
    
    async def get_all_agents(self) -> List[LangGraphAgent]:
        """
        Get all agents, whether loaded or not.
        
        Returns:
            List of LangGraphAgent instances
        """
        # If no agents are loaded, load them
        if not self.agents:
            await self.load_all_active_agents()
        
        return list(self.agents.values())
    
    async def reload_agent(self, agent_id: str) -> Optional[LangGraphAgent]:
        """
        Reload an agent from the database.
        
        Args:
            agent_id: The agent ID
            
        Returns:
            Reloaded LangGraphAgent instance or None if not found
        """
        # Remove from cache if exists
        if agent_id in self.agents:
            del self.agents[agent_id]
        
        # Load from database
        return await self.get_agent_by_id(agent_id)
    
    async def create_agent(self, agent_data: Dict[str, Any]) -> Optional[LangGraphAgent]:
        """
        Create a new agent in the database and load it.
        
        Args:
            agent_data: Agent data dictionary
            
        Returns:
            Created LangGraphAgent instance or None if creation failed
        """
        try:
            # Create agent in database
            agent_def = await self.agent_repository.create_agent(agent_data)
            if not agent_def:
                logger.error("Failed to create agent in database")
                return None
                
            # Create agent instance
            agent = await create_database_agent_from_model(agent_def)
            if agent:
                # Add to registry
                self.agents[agent.id] = agent
                logger.info(f"Created new agent: {agent.name} (ID: {agent.id})")
                return agent
            else:
                logger.error(f"Failed to create agent instance for {agent_def.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}", exc_info=True)
            return None
    
    async def update_agent(self, agent_id: str, agent_data: Dict[str, Any]) -> Optional[LangGraphAgent]:
        """
        Update an existing agent in the database and reload it.
        
        Args:
            agent_id: The agent ID
            agent_data: Updated agent data
            
        Returns:
            Updated LangGraphAgent instance or None if update failed
        """
        try:
            # Update agent in database
            agent_def = await self.agent_repository.update_agent(agent_id, agent_data)
            if not agent_def:
                logger.error(f"Failed to update agent {agent_id} in database")
                return None
                
            # Reload agent instance
            return await self.reload_agent(agent_id)
                
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {str(e)}", exc_info=True)
            return None
    
    async def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent from the database and registry.
        
        Args:
            agent_id: The agent ID
            
        Returns:
            True if deletion was successful
        """
        try:
            # Delete from database
            success = await self.agent_repository.delete_agent(agent_id)
            if not success:
                logger.error(f"Failed to delete agent {agent_id} from database")
                return False
                
            # Remove from registry
            if agent_id in self.agents:
                del self.agents[agent_id]
                logger.info(f"Removed agent {agent_id} from registry")
                
            return True
                
        except Exception as e:
            logger.error(f"Error deleting agent {agent_id}: {str(e)}", exc_info=True)
            return False