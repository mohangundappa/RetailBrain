"""
Factory for creating LangGraph agents from agent definitions.

This module provides a factory class that can create LangGraph agents
from agent definitions stored in the database.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.agents.framework.langgraph.langgraph_agent import LangGraphAgent
from backend.repositories.agent_repository import AgentRepository
from backend.database.agent_schema import (
    AgentDefinition, AgentDeployment, AgentComposition,
    LlmAgentConfiguration, RuleAgentConfiguration, RetrievalAgentConfiguration,
    AgentPattern, AgentPatternEmbedding, AgentTool, AgentResponseTemplate
)

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
    
    def _agent_model_to_dict(self, agent: AgentDefinition) -> Dict[str, Any]:
        """
        Convert an agent database model to a dictionary for agent creation.
        
        Args:
            agent: AgentDefinition instance from the database
            
        Returns:
            Dictionary representation of the agent
        """
        # Start with the base fields
        result = {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description or f"Agent {agent.name}",
            "agent_type": agent.agent_type,
            "status": agent.status,
            "version": agent.version,
            "is_system": agent.is_system,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
            "created_by": agent.created_by,
            "patterns": [],
            "tools": [],
            "response_templates": {},
            "entity_mappings": []
        }
        
        # Add patterns if available
        if hasattr(agent, 'patterns') and agent.patterns:
            result["patterns"] = [
                {
                    "id": str(pattern.id),
                    "pattern": pattern.pattern,
                    "confidence": pattern.confidence,
                    "embedding": pattern.embedding.embedding if hasattr(pattern, 'embedding') and pattern.embedding else None
                }
                for pattern in agent.patterns
            ]
        
        # Add tools if available
        if hasattr(agent, 'tools') and agent.tools:
            result["tools"] = [
                {
                    "id": str(tool.id),
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "required": tool.required,
                    "tool_type": tool.tool_type
                }
                for tool in agent.tools
            ]
            
        # Add response templates if available
        if hasattr(agent, 'response_templates') and agent.response_templates:
            for template in agent.response_templates:
                result["response_templates"][template.template_key] = {
                    "content": template.content,
                    "parameters": template.parameters,
                    "description": template.description
                }
        
        # Add entity mappings if available
        if hasattr(agent, 'entity_mappings') and agent.entity_mappings:
            result["entity_mappings"] = [
                {
                    "id": str(mapping.id),
                    "entity_id": str(mapping.entity_id),
                    "entity_name": mapping.entity.name if hasattr(mapping, 'entity') and mapping.entity else None,
                    "is_required": mapping.is_required,
                    "prompt_for_value": mapping.prompt_for_value,
                    "prompt_message": mapping.prompt_message
                }
                for mapping in agent.entity_mappings
            ]
            
        # Add type-specific configuration
        if agent.agent_type == "LLM" and hasattr(agent, 'llm_configuration') and agent.llm_configuration:
            result["llm_config"] = {
                "model": agent.llm_configuration.model,
                "temperature": agent.llm_configuration.temperature,
                "max_tokens": agent.llm_configuration.max_tokens,
                "system_prompt": agent.llm_configuration.system_prompt,
                "prompt_template": agent.llm_configuration.prompt_template
            }
        elif agent.agent_type == "RULE" and hasattr(agent, 'rule_configuration') and agent.rule_configuration:
            result["rule_config"] = {
                "rules": agent.rule_configuration.rules,
                "default_response": agent.rule_configuration.default_response
            }
        elif agent.agent_type == "RETRIEVAL" and hasattr(agent, 'retrieval_configuration') and agent.retrieval_configuration:
            result["retrieval_config"] = {
                "datasource_id": agent.retrieval_configuration.datasource_id,
                "max_results": agent.retrieval_configuration.max_results,
                "similarity_threshold": agent.retrieval_configuration.similarity_threshold
            }
            
        return result
            
    async def get_all_active_agents(self) -> List[LangGraphAgent]:
        """
        Get all active agents from the database.
        
        Returns:
            List of LangGraphAgent instances
        """
        try:
            # Get agent definitions from repository
            agent_definitions = await self.agent_repository.get_all_active_agents()
            
            agents = []
            for agent_def in agent_definitions:
                try:
                    # Convert the model to a dictionary
                    agent_dict = self._agent_model_to_dict(agent_def)
                    
                    # Create agent from definition
                    agent = await self.create_agent_from_definition(agent_dict)
                    if agent:
                        agents.append(agent)
                        # Cache the agent
                        self.agents[agent.get_id()] = agent
                except Exception as e:
                    logger.error(f"Error creating agent {getattr(agent_def, 'id', 'unknown')}: {str(e)}", exc_info=True)
            
            # If no agents were created, create a default agent
            if not agents:
                logger.warning("No agents found in database, creating default agent")
                default_agent = DefaultLangGraphAgent(
                    id="default-agent",
                    name="Default Agent",
                    description="A default agent that responds to all requests"
                )
                agents.append(default_agent)
                self.agents[default_agent.get_id()] = default_agent
            
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
            self.agents[default_agent.get_id()] = default_agent
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
    
    async def get_agent_by_id(self, agent_id: str, version: Optional[int] = None) -> Optional[LangGraphAgent]:
        """
        Get an agent by its ID, optionally specifying a version.
        
        Args:
            agent_id: Agent ID
            version: Specific version to retrieve (None for latest)
            
        Returns:
            LangGraphAgent instance or None if not found
        """
        # Generate a cache key that includes the version if provided
        cache_key = f"{agent_id}_v{version}" if version else agent_id
        
        # Check cache first
        if cache_key in self.agents:
            return self.agents[cache_key]
        
        try:
            # Get agent definition from repository
            agent_def = None
            
            if version:
                # Get a specific version
                agent_def = await self.agent_repository.get_agent_version(agent_id, version)
                if not agent_def:
                    logger.warning(f"Agent with ID {agent_id} version {version} not found")
                    return None
            else:
                # Get the latest version
                agent_def = await self.agent_repository.get_agent_definition(agent_id, load_related=True)
                if not agent_def:
                    logger.warning(f"Agent with ID {agent_id} not found")
                    return None
            
            # Convert the model to a dictionary
            agent_dict = self._agent_model_to_dict(agent_def)
            
            # Create agent from definition
            agent = await self.create_agent_from_definition(agent_dict)
            
            # Cache the agent if created successfully
            if agent:
                self.agents[cache_key] = agent
            
            return agent
            
        except Exception as e:
            logger.error(f"Error getting agent by ID {agent_id} version {version}: {str(e)}", exc_info=True)
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
            # First find any cached agent with this name
            for agent_id, agent in self.agents.items():
                if agent.get_name() == agent_name:
                    return agent
            
            # If not found in cache, query the database
            # Using a query to find agent by name
            query = select(AgentDefinition).where(AgentDefinition.name == agent_name)
            result = await self.agent_repository.session.execute(query)
            agent_def = result.scalar_one_or_none()
            
            if not agent_def:
                logger.warning(f"Agent with name {agent_name} not found")
                return None
            
            # Get the full definition with all relations
            agent_def = await self.agent_repository.get_agent_definition(str(agent_def.id), load_related=True)
            
            # Convert the model to a dictionary
            agent_dict = self._agent_model_to_dict(agent_def)
            
            # Create agent from definition
            agent = await self.create_agent_from_definition(agent_dict)
            
            # Cache the agent if created successfully
            if agent:
                self.agents[agent.get_id()] = agent
            
            return agent
            
        except Exception as e:
            logger.error(f"Error getting agent by name {agent_name}: {str(e)}", exc_info=True)
            return None