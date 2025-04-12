"""
Agent factory for Staples Brain.
This module provides factory methods for creating agents from database configurations.
"""
import logging
from typing import Dict, Any, List, Optional, Type, Union, Callable
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.agent_repository import AgentRepository
from backend.database.agent_schema import (
    AgentDefinition, LlmAgentConfiguration, RuleAgentConfiguration, RetrievalAgentConfiguration
)
from backend.agents.base_agent import BaseAgent
from backend.agents.package_tracking_agent import PackageTrackingAgent
from backend.agents.reset_password_agent import ResetPasswordAgent
from backend.agents.store_locator_agent import StoreLocatorAgent
from backend.agents.product_info_agent import ProductInfoAgent
from backend.agents.returns_processing_agent import ReturnsProcessingAgent
from backend.config.agent_constants import (
    PACKAGE_TRACKING_AGENT,
    RESET_PASSWORD_AGENT,
    STORE_LOCATOR_AGENT,
    PRODUCT_INFO_AGENT,
    RETURNS_PROCESSING_AGENT
)

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Factory class for creating agent instances from database configurations.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the factory with a database session.
        
        Args:
            db_session: SQLAlchemy async session
        """
        self.db_session = db_session
        self.agent_repository = AgentRepository(db_session)
        
        # Register agent class mappings
        self.agent_class_mapping = {
            PACKAGE_TRACKING_AGENT: PackageTrackingAgent,
            RESET_PASSWORD_AGENT: ResetPasswordAgent,
            STORE_LOCATOR_AGENT: StoreLocatorAgent,
            PRODUCT_INFO_AGENT: ProductInfoAgent,
            RETURNS_PROCESSING_AGENT: ReturnsProcessingAgent,
        }
    
    async def get_all_active_agents(self) -> List[BaseAgent]:
        """
        Get all active agents from the database.
        
        Returns:
            List of agent instances
        """
        agents = []
        # Get all active agent definitions
        agent_definitions = await self.agent_repository.list_agents(status="active")
        
        for agent_def in agent_definitions:
            try:
                agent = await self._create_agent_from_definition(agent_def)
                if agent:
                    agents.append(agent)
            except Exception as e:
                logger.error(f"Error creating agent {agent_def.name}: {str(e)}", exc_info=True)
        
        return agents
    
    async def get_agent_by_id(self, agent_id: Union[uuid.UUID, str]) -> Optional[BaseAgent]:
        """
        Get an agent by its ID.
        
        Args:
            agent_id: The agent ID
            
        Returns:
            Agent instance or None if not found or could not be created
        """
        agent_def = await self.agent_repository.get_agent_definition(agent_id)
        if not agent_def:
            return None
        
        return await self._create_agent_from_definition(agent_def)
    
    async def get_agent_by_type(self, agent_type: str) -> Optional[BaseAgent]:
        """
        Get an agent by its type.
        
        Args:
            agent_type: The agent type
            
        Returns:
            Agent instance or None if not found or could not be created
        """
        # List agents of the specified type
        agent_defs = await self.agent_repository.list_agents(agent_type=agent_type)
        
        # If none found, return None
        if not agent_defs:
            return None
        
        # Otherwise, create an agent from the first definition
        return await self._create_agent_from_definition(agent_defs[0])
    
    async def _create_agent_from_definition(self, agent_def: AgentDefinition) -> Optional[BaseAgent]:
        """
        Create an agent instance from its database definition.
        
        Args:
            agent_def: The agent definition from the database
            
        Returns:
            Agent instance or None if could not be created
        """
        # Get the appropriate agent class based on agent type
        agent_class = self.agent_class_mapping.get(agent_def.agent_type)
        
        if not agent_class:
            logger.warning(f"No agent class found for type {agent_def.agent_type}")
            return None
        
        try:
            # Get agent patterns
            patterns = await self.agent_repository.get_agent_patterns(agent_def.id)
            
            # Get agent tools
            tools = await self.agent_repository.get_agent_tools(agent_def.id)
            
            # Create configuration dictionary
            config = {
                "id": str(agent_def.id),
                "name": agent_def.name,
                "description": agent_def.description,
                "patterns": [
                    {
                        "type": p.pattern_type,
                        "value": p.pattern_value,
                        "priority": p.priority,
                        "confidence_boost": p.confidence_boost
                    }
                    for p in patterns
                ],
                "tools": [
                    {
                        "name": t.tool_name,
                        "description": t.tool_description,
                        "class_path": t.tool_class_path,
                        "config": t.tool_config
                    }
                    for t in tools
                ],
                "response_templates": {
                    t.template_key: t.template_content
                    for t in agent_def.response_templates
                }
            }
            
            # Add type-specific configuration
            if agent_def.agent_type == "LLM" and agent_def.llm_configuration:
                config.update({
                    "model_name": agent_def.llm_configuration.model_name,
                    "temperature": agent_def.llm_configuration.temperature,
                    "max_tokens": agent_def.llm_configuration.max_tokens,
                    "timeout_seconds": agent_def.llm_configuration.timeout_seconds,
                    "system_prompt": agent_def.llm_configuration.system_prompt,
                })
            
            # Create the agent instance
            agent = agent_class(config)
            return agent
            
        except Exception as e:
            logger.error(f"Error creating agent {agent_def.name}: {str(e)}", exc_info=True)
            return None
    
    async def register_agent_with_orchestrator(self, orchestrator: Any, agent_type: str) -> bool:
        """
        Register an agent with the orchestrator.
        
        Args:
            orchestrator: The orchestrator instance
            agent_type: The agent type to register
            
        Returns:
            True if successful, False otherwise
        """
        try:
            agent = await self.get_agent_by_type(agent_type)
            if agent and orchestrator:
                # Check if the agent is already registered
                already_registered = False
                for existing_agent in orchestrator.agents:
                    if existing_agent.name == agent.name:
                        already_registered = True
                        break
                
                if not already_registered:
                    orchestrator.agents.append(agent)
                    logger.info(f"Registered agent {agent.name} with orchestrator")
                    return True
                else:
                    logger.info(f"Agent {agent.name} already registered with orchestrator")
                    return True
            else:
                logger.warning(f"Failed to register agent of type {agent_type}: Agent not found or orchestrator not provided")
                return False
        except Exception as e:
            logger.error(f"Error registering agent of type {agent_type}: {str(e)}", exc_info=True)
            return False
    
    async def register_all_agents_with_orchestrator(self, orchestrator: Any) -> int:
        """
        Register all active agents with the orchestrator.
        
        Args:
            orchestrator: The orchestrator instance
            
        Returns:
            Number of agents registered
        """
        if not orchestrator:
            logger.warning("Cannot register agents: No orchestrator provided")
            return 0
        
        registered_count = 0
        all_agents = await self.get_all_active_agents()
        
        for agent in all_agents:
            # Check if the agent is already registered
            already_registered = False
            for existing_agent in orchestrator.agents:
                if existing_agent.name == agent.name:
                    already_registered = True
                    break
            
            if not already_registered:
                orchestrator.agents.append(agent)
                registered_count += 1
                logger.info(f"Registered agent {agent.name} with orchestrator")
        
        logger.info(f"Registered {registered_count} agents with orchestrator")
        return registered_count