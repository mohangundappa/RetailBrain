"""
Factory for creating LangGraph agents from database configurations.

This module connects the database agent definitions with LangGraph agent implementations.
"""
import logging
import uuid
from typing import Dict, Any, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.agent_repository import AgentRepository
from backend.database.agent_schema import AgentDefinition
from backend.brain.agents.langgraph_agent import LangGraphAgent

logger = logging.getLogger(__name__)


class LangGraphAgentFactory:
    """
    Factory for creating LangGraph agent instances from database configurations.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the factory with a database session.
        
        Args:
            db_session: SQLAlchemy async session
        """
        self.db_session = db_session
        self.agent_repository = AgentRepository(db_session)
        self._agent_cache: Dict[str, LangGraphAgent] = {}
    
    async def get_all_active_agents(self) -> List[LangGraphAgent]:
        """
        Get all active agents from the database.
        
        Returns:
            List of LangGraph agent instances
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
    
    async def get_agent_by_id(self, agent_id: Union[uuid.UUID, str]) -> Optional[LangGraphAgent]:
        """
        Get an agent by its ID.
        
        Args:
            agent_id: The agent ID
            
        Returns:
            LangGraph agent instance or None if not found or could not be created
        """
        # Check cache first
        cache_key = str(agent_id)
        if cache_key in self._agent_cache:
            return self._agent_cache[cache_key]
            
        agent_def = await self.agent_repository.get_agent_definition(agent_id)
        if not agent_def:
            return None
        
        agent = await self._create_agent_from_definition(agent_def)
        if agent:
            self._agent_cache[cache_key] = agent
            
        return agent
    
    async def get_agent_by_name(self, agent_name: str) -> Optional[LangGraphAgent]:
        """
        Get an agent by its name.
        
        Args:
            agent_name: The agent name
            
        Returns:
            LangGraph agent instance or None if not found or could not be created
        """
        # Check cache first
        if agent_name in self._agent_cache:
            return self._agent_cache[agent_name]
            
        # List all agents and filter by name
        all_agents = await self.agent_repository.list_agents()
        matching_agents = [agent for agent in all_agents if agent.name == agent_name]
        
        # If none found, return None
        if not matching_agents:
            return None
        
        # Otherwise, create an agent from the first matching definition
        agent = await self._create_agent_from_definition(matching_agents[0])
        if agent:
            self._agent_cache[agent_name] = agent
            
        return agent
    
    async def _create_agent_from_definition(self, agent_def: AgentDefinition) -> Optional[LangGraphAgent]:
        """
        Create a LangGraph agent instance from its database definition.
        
        Args:
            agent_def: The agent definition from the database
            
        Returns:
            LangGraph agent instance or None if could not be created
        """
        try:
            # Get agent patterns
            patterns = await self.agent_repository.get_agent_patterns(agent_def.id)
            
            # Get agent tools
            tools = await self.agent_repository.get_agent_tools(agent_def.id)
            
            # Get entity definitions
            # Note: This is currently a stub as entity mappings are not fully implemented
            # We will implement the entity mapping retrieval when that part of the schema is available
            entity_definitions = []
            
            # TODO: Implement entity mapping retrieval
            # For now, we'll use a simplified approach
            # Example of what the data structure would look like:
            # entity_definitions = [
            #     {
            #         "name": "order_number",
            #         "description": "The order number to track",
            #         "required": True,
            #         "validation_pattern": r"^\d{10}$",
            #         "error_message": "Order number must be 10 digits",
            #         "examples": ["1234567890"]
            #     }
            # ]
            
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
                        "parameters": t.parameters or {}
                    }
                    for t in tools
                ],
                "response_templates": {
                    t.template_key: t.template_content
                    for t in agent_def.response_templates
                },
                "entity_definitions": entity_definitions
            }
            
            # Add type-specific configuration
            if agent_def.agent_type == "LLM" and hasattr(agent_def, "llm_configuration") and agent_def.llm_configuration:
                config.update({
                    "model_name": agent_def.llm_configuration.model_name,
                    "temperature": agent_def.llm_configuration.temperature,
                    "max_tokens": agent_def.llm_configuration.max_tokens,
                    "timeout_seconds": agent_def.llm_configuration.timeout_seconds,
                    "system_prompt": agent_def.llm_configuration.system_prompt,
                })
            
            # Create the agent instance
            agent = LangGraphAgent(config)
            return agent
            
        except Exception as e:
            logger.error(f"Error creating agent {agent_def.name}: {str(e)}", exc_info=True)
            return None