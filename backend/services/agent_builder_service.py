"""
Agent Builder Service for Staples Brain.

This service provides functionality for creating, testing, and managing agent configurations.
It connects the API layer with the repository layer and implements business logic for
agent management.
"""
import logging
import time
import uuid
import json
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.agent_repository import AgentRepository
from backend.database.agent_schema import (
    AgentDefinition, AgentDeployment, AgentComposition,
    LlmAgentConfiguration, RuleAgentConfiguration, RetrievalAgentConfiguration,
    AgentPattern, AgentPatternEmbedding, AgentTool, AgentResponseTemplate
)
from backend.database.entity_schema import (
    EntityDefinition, EntityEnumValue, AgentEntityMapping,
    EntityExtractionPattern, EntityTransformation
)
from backend.endpoints.schemas.agent_schema import (
    AgentDetailModel, AgentCreateRequest, AgentUpdateRequest,
    AgentPersonaModel, AgentToolModel, EntityMappingModel,
    AgentLlmConfigModel, AgentPatternModel, AgentResponseTemplateModel,
    AgentTestRequest, AgentTestResponse
)
from backend.agents.framework.langgraph.agent_factory_util import create_agent_from_definition
from backend.services.graph_brain_service import GraphBrainService

logger = logging.getLogger(__name__)


class AgentBuilderService:
    """
    Service for building and managing agent configurations.
    
    This service provides operations for creating, updating, testing, and deploying
    agent configurations, as well as managing agent tools, entities, and templates.
    """
    
    def __init__(self, db_session: AsyncSession, brain_service: Optional[GraphBrainService] = None):
        """
        Initialize the agent builder service.
        
        Args:
            db_session: Async database session
            brain_service: Optional GraphBrainService for testing agents
        """
        self.db_session = db_session
        self.agent_repository = AgentRepository(db_session)
        self.brain_service = brain_service
        
        logger.info("Initialized Agent Builder Service")
    
    async def list_agents(
        self, 
        agent_type: Optional[str] = None,
        is_system: Optional[bool] = None,
        status: Optional[str] = None
    ) -> List[AgentDetailModel]:
        """
        List agents with optional filtering.
        
        Args:
            agent_type: Optional filter by agent type
            is_system: Optional filter by system agent flag
            status: Optional filter by agent status
            
        Returns:
            List of agent details
        """
        try:
            agents = await self.agent_repository.list_agents(
                agent_type=agent_type,
                is_system=is_system,
                status=status
            )
            
            result = []
            for agent in agents:
                agent_data = self._convert_agent_to_model(agent)
                result.append(agent_data)
            
            return result
        except Exception as e:
            logger.error(f"Error listing agents: {str(e)}", exc_info=True)
            raise
    
    async def get_agent(self, agent_id: str) -> Optional[AgentDetailModel]:
        """
        Get detailed information about a specific agent.
        
        Args:
            agent_id: ID of the agent to retrieve
            
        Returns:
            Detailed agent information or None if not found
        """
        try:
            agent = await self.agent_repository.get_agent_by_id(agent_id, load_related=True)
            if not agent:
                return None
            
            return await self._build_agent_detail_model(agent)
        except Exception as e:
            logger.error(f"Error getting agent {agent_id}: {str(e)}", exc_info=True)
            raise
    
    async def create_agent(self, agent_data: AgentCreateRequest) -> AgentDetailModel:
        """
        Create a new agent configuration.
        
        Args:
            agent_data: Agent configuration data
            
        Returns:
            Created agent details
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Validate agent data
            self._validate_agent_data(agent_data)
            
            # Create agent definition
            agent_definition = AgentDefinition(
                id=uuid.uuid4(),
                name=agent_data.name,
                description=agent_data.description,
                agent_type=agent_data.agent_type,
                version=1,
                status="draft",
                is_system=agent_data.is_system,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Use a template if specified
            if agent_data.template_id:
                template = await self.agent_repository.get_agent_by_id(agent_data.template_id, load_related=True)
                if not template:
                    raise ValueError(f"Template with ID {agent_data.template_id} not found")
                
                # Clone configurations from template
                await self._clone_agent_config(template, agent_definition)
            
            # Add agent to database
            await self.agent_repository.create_agent(agent_definition)
            
            # Add additional configurations if provided
            if agent_data.persona:
                await self.update_agent_persona(str(agent_definition.id), agent_data.persona)
            
            if agent_data.llm_config:
                await self._create_llm_config(str(agent_definition.id), agent_data.llm_config)
            
            if agent_data.patterns:
                for pattern in agent_data.patterns:
                    await self._create_pattern(str(agent_definition.id), pattern)
            
            if agent_data.tools:
                for tool in agent_data.tools:
                    await self.add_agent_tool(str(agent_definition.id), tool)
            
            if agent_data.response_templates:
                for template in agent_data.response_templates:
                    await self._create_response_template(str(agent_definition.id), template)
            
            if agent_data.entities:
                for entity in agent_data.entities:
                    await self.add_agent_entity(str(agent_definition.id), entity)
            
            # Return the created agent
            return await self.get_agent(str(agent_definition.id))
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error creating agent: {str(e)}", exc_info=True)
            raise
    
    async def update_agent(self, agent_id: str, agent_data: AgentUpdateRequest) -> Optional[AgentDetailModel]:
        """
        Update an existing agent configuration.
        
        Args:
            agent_id: ID of the agent to update
            agent_data: Updated agent configuration data
            
        Returns:
            Updated agent details or None if not found
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Get existing agent
            agent = await self.agent_repository.get_agent_by_id(agent_id)
            if not agent:
                return None
            
            # Cannot update active agents directly, must create a new version
            if agent.status == "active" and not agent.is_system:
                # Create a new version
                new_agent = AgentDefinition(
                    id=uuid.uuid4(),
                    name=agent_data.name or agent.name,
                    description=agent_data.description or agent.description,
                    agent_type=agent_data.agent_type or agent.agent_type,
                    version=agent.version + 1,
                    status="draft",
                    is_system=agent.is_system,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    created_by=agent.created_by
                )
                
                # Clone configurations from the existing agent
                await self._clone_agent_config(agent, new_agent)
                
                # Add the new agent to the database
                await self.agent_repository.create_agent(new_agent)
                
                # Update with new data
                agent_id = str(new_agent.id)
            else:
                # Update existing agent
                if agent_data.name:
                    agent.name = agent_data.name
                if agent_data.description:
                    agent.description = agent_data.description
                if agent_data.agent_type:
                    agent.agent_type = agent_data.agent_type
                
                agent.updated_at = datetime.now()
                await self.agent_repository.update_agent(agent)
            
            # Update additional configurations if provided
            if agent_data.persona:
                await self.update_agent_persona(agent_id, agent_data.persona)
            
            if agent_data.llm_config:
                await self._update_llm_config(agent_id, agent_data.llm_config)
            
            if agent_data.patterns:
                # Replace all patterns
                await self.agent_repository.delete_agent_patterns(agent_id)
                for pattern in agent_data.patterns:
                    await self._create_pattern(agent_id, pattern)
            
            if agent_data.response_templates:
                # Replace all templates
                await self.agent_repository.delete_agent_response_templates(agent_id)
                for template in agent_data.response_templates:
                    await self._create_response_template(agent_id, template)
            
            # Return the updated agent
            return await self.get_agent(agent_id)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error updating agent {agent_id}: {str(e)}", exc_info=True)
            raise
    
    async def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent configuration.
        
        Args:
            agent_id: ID of the agent to delete
            
        Returns:
            True if the agent was deleted, False if not found
        """
        try:
            # Get existing agent
            agent = await self.agent_repository.get_agent_by_id(agent_id)
            if not agent:
                return False
            
            # System agents cannot be deleted
            if agent.is_system:
                raise ValueError("System agents cannot be deleted")
            
            # Archive instead of delete if the agent is active
            if agent.status == "active":
                agent.status = "archived"
                agent.updated_at = datetime.now()
                await self.agent_repository.update_agent(agent)
                return True
            
            # Delete the agent
            await self.agent_repository.delete_agent(agent_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting agent {agent_id}: {str(e)}", exc_info=True)
            raise
    
    async def get_agent_persona(self, agent_id: str) -> Optional[AgentPersonaModel]:
        """
        Get the persona configuration for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent persona configuration or None if not found
        """
        try:
            agent = await self.agent_repository.get_agent_by_id(agent_id, load_related=True)
            if not agent:
                return None
            
            llm_config = next((c for c in agent.llm_configuration if c.agent_id == agent.id), None)
            if not llm_config:
                return None
            
            # Basic persona from system prompt
            system_prompt = llm_config.system_prompt or f"You are {agent.name}, an AI assistant."
            
            # Create a default persona model
            persona = AgentPersonaModel(
                system_prompt=system_prompt,
                tone="professional",
                verbosity="balanced",
                formality="formal",
                persona_traits=[],
                language_style=None
            )
            
            return persona
        except Exception as e:
            logger.error(f"Error getting persona for agent {agent_id}: {str(e)}", exc_info=True)
            raise
    
    async def update_agent_persona(self, agent_id: str, persona_data: AgentPersonaModel) -> Optional[AgentPersonaModel]:
        """
        Update the persona configuration for an agent.
        
        Args:
            agent_id: ID of the agent
            persona_data: Updated persona configuration
            
        Returns:
            Updated agent persona or None if not found
        """
        try:
            agent = await self.agent_repository.get_agent_by_id(agent_id)
            if not agent:
                return None
            
            # Get LLM configuration
            llm_config = await self.agent_repository.get_llm_config(agent_id)
            
            if llm_config:
                # Update existing configuration
                llm_config.system_prompt = persona_data.system_prompt
                await self.agent_repository.update_llm_config(llm_config)
            else:
                # Create new configuration
                llm_config = LlmAgentConfiguration(
                    agent_id=agent.id,
                    model_name="gpt-4o",  # Default model
                    temperature=0.7,
                    max_tokens=500,
                    timeout_seconds=30,
                    confidence_threshold=0.7,
                    system_prompt=persona_data.system_prompt
                )
                self.db_session.add(llm_config)
                await self.db_session.flush()
            
            # Store additional persona attributes (could be extended to persist in a separate table)
            # For now, this is a simplified implementation
            
            return persona_data
        except Exception as e:
            logger.error(f"Error updating persona for agent {agent_id}: {str(e)}", exc_info=True)
            raise
    
    async def list_agent_tools(self, agent_id: str) -> List[AgentToolModel]:
        """
        List all tools available to an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of agent tools
        """
        try:
            tools = await self.agent_repository.get_agent_tools(agent_id)
            result = []
            
            for tool in tools:
                tool_model = AgentToolModel(
                    id=str(tool.id),
                    tool_name=tool.tool_name,
                    tool_description=tool.tool_description or "",
                    tool_class_path=tool.tool_class_path or "",
                    parameters=tool.parameters,
                    is_enabled=tool.is_enabled,
                    requires_confirmation=False,  # Could be extended in the schema
                    usage_threshold=0.7  # Default threshold
                )
                result.append(tool_model)
            
            return result
        except Exception as e:
            logger.error(f"Error listing tools for agent {agent_id}: {str(e)}", exc_info=True)
            raise
    
    async def add_agent_tool(self, agent_id: str, tool_data: AgentToolModel) -> AgentToolModel:
        """
        Add a tool to an agent.
        
        Args:
            agent_id: ID of the agent
            tool_data: Tool configuration data
            
        Returns:
            Added tool details
        """
        try:
            # Validate input
            if not tool_data.tool_name:
                raise ValueError("Tool name is required")
            
            # Check if agent exists
            agent = await self.agent_repository.get_agent_by_id(agent_id)
            if not agent:
                raise ValueError(f"Agent with ID {agent_id} not found")
            
            # Create tool
            tool_id = await self.agent_repository.add_agent_tool(
                agent_id=agent_id,
                tool_name=tool_data.tool_name,
                tool_description=tool_data.tool_description,
                tool_class_path=tool_data.tool_class_path,
                parameters=tool_data.parameters,
                is_enabled=tool_data.is_enabled
            )
            
            # Return the created tool
            tool_data.id = str(tool_id)
            return tool_data
        except Exception as e:
            logger.error(f"Error adding tool to agent {agent_id}: {str(e)}", exc_info=True)
            raise
    
    async def update_agent_tool(self, agent_id: str, tool_id: str, tool_data: AgentToolModel) -> Optional[AgentToolModel]:
        """
        Update a tool configuration for an agent.
        
        Args:
            agent_id: ID of the agent
            tool_id: ID of the tool to update
            tool_data: Updated tool configuration
            
        Returns:
            Updated tool details or None if not found
        """
        try:
            # Get the tool
            tool = await self.agent_repository.get_agent_tool(tool_id)
            if not tool or str(tool.agent_id) != agent_id:
                return None
            
            # Update tool
            tool.tool_name = tool_data.tool_name
            tool.tool_description = tool_data.tool_description
            tool.tool_class_path = tool_data.tool_class_path
            tool.parameters = tool_data.parameters
            tool.is_enabled = tool_data.is_enabled
            
            # Save changes
            self.db_session.add(tool)
            await self.db_session.flush()
            
            # Return updated tool
            tool_data.id = tool_id
            return tool_data
        except Exception as e:
            logger.error(f"Error updating tool {tool_id}: {str(e)}", exc_info=True)
            raise
    
    async def delete_agent_tool(self, agent_id: str, tool_id: str) -> bool:
        """
        Delete a tool from an agent.
        
        Args:
            agent_id: ID of the agent
            tool_id: ID of the tool to delete
            
        Returns:
            True if the tool was deleted, False if not found
        """
        try:
            # Get the tool
            tool = await self.agent_repository.get_agent_tool(tool_id)
            if not tool or str(tool.agent_id) != agent_id:
                return False
            
            # Delete the tool
            await self.db_session.delete(tool)
            await self.db_session.flush()
            
            return True
        except Exception as e:
            logger.error(f"Error deleting tool {tool_id}: {str(e)}", exc_info=True)
            raise
    
    async def list_entities(self) -> List[EntityMappingModel]:
        """
        List all available entity definitions.
        
        Returns:
            List of entity definitions
        """
        try:
            entities = await self.agent_repository.get_all_entities()
            result = []
            
            for entity in entities:
                entity_model = EntityMappingModel(
                    id=str(entity.id),
                    entity_id=str(entity.id),
                    entity_name=entity.name,
                    display_name=entity.display_name,
                    extraction_strategy="llm",
                    confidence_threshold=0.7,
                    is_required=entity.is_required,
                    persistence_scope="session",
                    validation_regex=entity.validation_regex,
                    default_value=entity.default_value
                )
                result.append(entity_model)
            
            return result
        except Exception as e:
            logger.error(f"Error listing entities: {str(e)}", exc_info=True)
            raise
    
    async def list_agent_entities(self, agent_id: str) -> List[EntityMappingModel]:
        """
        List all entities configured for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of entity mappings for the agent
        """
        try:
            mappings = await self.agent_repository.get_agent_entity_mappings(agent_id)
            result = []
            
            for mapping in mappings:
                entity = mapping.entity
                entity_model = EntityMappingModel(
                    id=str(mapping.id),
                    entity_id=str(entity.id),
                    entity_name=entity.name,
                    display_name=entity.display_name,
                    extraction_strategy=mapping.extraction_strategy or "llm",
                    confidence_threshold=mapping.confidence_threshold or 0.7,
                    is_required=mapping.is_required or entity.is_required,
                    persistence_scope=mapping.persistence_scope or "session",
                    validation_regex=entity.validation_regex,
                    default_value=entity.default_value
                )
                result.append(entity_model)
            
            return result
        except Exception as e:
            logger.error(f"Error listing entities for agent {agent_id}: {str(e)}", exc_info=True)
            raise
    
    async def add_agent_entity(self, agent_id: str, entity_data: EntityMappingModel) -> EntityMappingModel:
        """
        Add an entity mapping to an agent.
        
        Args:
            agent_id: ID of the agent
            entity_data: Entity mapping configuration
            
        Returns:
            Added entity mapping
        """
        try:
            # Check if agent exists
            agent = await self.agent_repository.get_agent_by_id(agent_id)
            if not agent:
                raise ValueError(f"Agent with ID {agent_id} not found")
            
            # Check if entity exists
            entity = await self.agent_repository.get_entity_by_id(entity_data.entity_id)
            if not entity:
                raise ValueError(f"Entity with ID {entity_data.entity_id} not found")
            
            # Create mapping
            mapping_id = await self.agent_repository.add_agent_entity_mapping(
                agent_id=agent_id,
                entity_id=entity_data.entity_id,
                extraction_strategy=entity_data.extraction_strategy,
                confidence_threshold=entity_data.confidence_threshold,
                is_required=entity_data.is_required,
                persistence_scope=entity_data.persistence_scope
            )
            
            # Return the created mapping
            entity_data.id = str(mapping_id)
            return entity_data
        except Exception as e:
            logger.error(f"Error adding entity to agent {agent_id}: {str(e)}", exc_info=True)
            raise
    
    async def update_agent_entity(self, agent_id: str, mapping_id: str, entity_data: EntityMappingModel) -> Optional[EntityMappingModel]:
        """
        Update an entity mapping for an agent.
        
        Args:
            agent_id: ID of the agent
            mapping_id: ID of the entity mapping to update
            entity_data: Updated entity mapping configuration
            
        Returns:
            Updated entity mapping or None if not found
        """
        try:
            # Get the mapping
            mapping = await self.agent_repository.get_agent_entity_mapping(mapping_id)
            if not mapping or str(mapping.agent_id) != agent_id:
                return None
            
            # Update mapping
            mapping.extraction_strategy = entity_data.extraction_strategy
            mapping.confidence_threshold = entity_data.confidence_threshold
            mapping.is_required = entity_data.is_required
            mapping.persistence_scope = entity_data.persistence_scope
            
            # Save changes
            self.db_session.add(mapping)
            await self.db_session.flush()
            
            # Return updated mapping
            entity_data.id = mapping_id
            return entity_data
        except Exception as e:
            logger.error(f"Error updating entity mapping {mapping_id}: {str(e)}", exc_info=True)
            raise
    
    async def delete_agent_entity(self, agent_id: str, mapping_id: str) -> bool:
        """
        Delete an entity mapping from an agent.
        
        Args:
            agent_id: ID of the agent
            mapping_id: ID of the entity mapping to delete
            
        Returns:
            True if the mapping was deleted, False if not found
        """
        try:
            # Get the mapping
            mapping = await self.agent_repository.get_agent_entity_mapping(mapping_id)
            if not mapping or str(mapping.agent_id) != agent_id:
                return False
            
            # Delete the mapping
            await self.db_session.delete(mapping)
            await self.db_session.flush()
            
            return True
        except Exception as e:
            logger.error(f"Error deleting entity mapping {mapping_id}: {str(e)}", exc_info=True)
            raise
    
    async def test_agent(self, agent_id: str, test_data: AgentTestRequest) -> AgentTestResponse:
        """
        Test an agent with a sample message.
        
        Args:
            agent_id: ID of the agent to test
            test_data: Test configuration with sample message
            
        Returns:
            Test results including agent response
        """
        try:
            # Get the agent
            agent = await self.agent_repository.get_agent_by_id(agent_id, load_related=True)
            if not agent:
                raise ValueError(f"Agent with ID {agent_id} not found")
            
            # Convert agent to a dictionary for testing
            agent_dict = await self._convert_agent_to_dict(agent)
            
            start_time = time.time()
            
            if self.brain_service:
                # Test using the brain service
                context = test_data.context or {}
                context["agent_id"] = agent_id
                response = await self.brain_service.process_message(
                    user_message=test_data.message,
                    session_id=str(uuid.uuid4()),
                    context=context
                )
                
                processed_time = time.time() - start_time
                
                return AgentTestResponse(
                    success=True,
                    agent_id=agent_id,
                    agent_name=agent.name,
                    message=test_data.message,
                    response=response.get("response", ""),
                    confidence=response.get("confidence", 0.0),
                    processing_time=processed_time * 1000,  # Convert to milliseconds
                    extracted_entities=response.get("entities", {}),
                    debug_info=response if test_data.include_debug else None
                )
            else:
                # Create a temporary agent for testing
                temp_agent = await create_agent_from_definition(agent_dict)
                if not temp_agent:
                    raise ValueError("Failed to create test agent instance")
                
                # Process the test message
                response = await temp_agent.process_message(
                    test_data.message,
                    "test_user",
                    "test_session",
                    test_data.context or {}
                )
                
                processed_time = time.time() - start_time
                
                return AgentTestResponse(
                    success=True,
                    agent_id=agent_id,
                    agent_name=agent.name,
                    message=test_data.message,
                    response=response.get("response", ""),
                    confidence=response.get("confidence", 0.0),
                    processing_time=processed_time * 1000,  # Convert to milliseconds
                    extracted_entities=response.get("entities", {}),
                    debug_info=response if test_data.include_debug else None
                )
        except Exception as e:
            logger.error(f"Error testing agent {agent_id}: {str(e)}", exc_info=True)
            return AgentTestResponse(
                success=False,
                agent_id=agent_id,
                agent_name="Unknown",
                message=test_data.message,
                response="Failed to process test message",
                confidence=0.0,
                processing_time=0.0,
                error=str(e)
            )
    
    async def publish_agent(self, agent_id: str) -> Optional[AgentDetailModel]:
        """
        Publish an agent from draft to active status.
        
        Args:
            agent_id: ID of the agent to publish
            
        Returns:
            Published agent details or None if not found
        """
        try:
            # Get the agent
            agent = await self.agent_repository.get_agent_by_id(agent_id)
            if not agent:
                return None
            
            # Validate agent for publishing
            if agent.status == "active":
                raise ValueError("Agent is already published")
            
            # Test the agent before publishing
            test_result = await self.test_agent(
                agent_id,
                AgentTestRequest(
                    message="Test message for pre-publish validation",
                    include_debug=True
                )
            )
            
            if not test_result.success:
                raise ValueError(f"Agent validation failed: {test_result.error}")
            
            # Update status to active
            agent.status = "active"
            agent.updated_at = datetime.now()
            await self.agent_repository.update_agent(agent)
            
            # Return the published agent
            return await self.get_agent(agent_id)
        except Exception as e:
            logger.error(f"Error publishing agent {agent_id}: {str(e)}", exc_info=True)
            raise
    
    async def list_agent_templates(self) -> List[AgentDetailModel]:
        """
        List available agent templates.
        
        Returns:
            List of agent templates
        """
        try:
            # Get all system agents that can be used as templates
            agents = await self.agent_repository.list_agents(
                is_system=True,
                status="active"
            )
            
            result = []
            for agent in agents:
                agent_data = self._convert_agent_to_model(agent)
                result.append(agent_data)
            
            return result
        except Exception as e:
            logger.error(f"Error listing agent templates: {str(e)}", exc_info=True)
            raise
    
    # =================== Helper Methods ===================
    
    def _validate_agent_data(self, agent_data: Union[AgentCreateRequest, AgentUpdateRequest]) -> None:
        """
        Validate agent data for creation or update.
        
        Args:
            agent_data: Agent data to validate
            
        Raises:
            ValueError: If validation fails
        """
        if isinstance(agent_data, AgentCreateRequest):
            if not agent_data.name:
                raise ValueError("Agent name is required")
            if not agent_data.description:
                raise ValueError("Agent description is required")
            if not agent_data.agent_type:
                raise ValueError("Agent type is required")
    
    async def _build_agent_detail_model(self, agent: AgentDefinition) -> AgentDetailModel:
        """
        Build a detailed agent model from an agent definition.
        
        Args:
            agent: Agent definition
            
        Returns:
            Detailed agent model
        """
        # Convert basic information
        agent_model = self._convert_agent_to_model(agent)
        
        # Add persona configuration
        persona = await self.get_agent_persona(str(agent.id))
        if persona:
            agent_model.persona = persona
        
        # Add LLM configuration
        llm_config = await self._get_llm_config_model(str(agent.id))
        if llm_config:
            agent_model.llm_config = llm_config
        
        # Add patterns
        patterns = await self._get_pattern_models(str(agent.id))
        if patterns:
            agent_model.patterns = patterns
        
        # Add tools
        tools = await self.list_agent_tools(str(agent.id))
        if tools:
            agent_model.tools = tools
        
        # Add response templates
        templates = await self._get_response_template_models(str(agent.id))
        if templates:
            agent_model.response_templates = templates
        
        # Add entity mappings
        entities = await self.list_agent_entities(str(agent.id))
        if entities:
            agent_model.entities = entities
        
        return agent_model
    
    def _convert_agent_to_model(self, agent: AgentDefinition) -> AgentDetailModel:
        """
        Convert an agent definition to a basic agent model.
        
        Args:
            agent: Agent definition
            
        Returns:
            Basic agent model
        """
        return AgentDetailModel(
            id=str(agent.id),
            name=agent.name,
            description=agent.description or "",
            agent_type=agent.agent_type,
            version=agent.version,
            status=agent.status,
            is_system=agent.is_system,
            created_at=agent.created_at.isoformat() if agent.created_at else None,
            updated_at=agent.updated_at.isoformat() if agent.updated_at else None,
            created_by=agent.created_by
        )
    
    async def _convert_agent_to_dict(self, agent: AgentDefinition) -> Dict[str, Any]:
        """
        Convert an agent definition to a dictionary for agent creation.
        
        Args:
            agent: Agent definition
            
        Returns:
            Agent dictionary
        """
        agent_dict = {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description,
            "agent_type": agent.agent_type,
            "version": agent.version,
            "status": agent.status,
            "is_system": agent.is_system
        }
        
        # Add LLM configuration
        llm_config = next((c for c in agent.llm_configuration if c.agent_id == agent.id), None)
        if llm_config:
            agent_dict["model_name"] = llm_config.model_name
            agent_dict["temperature"] = llm_config.temperature
            agent_dict["max_tokens"] = llm_config.max_tokens
            agent_dict["timeout_seconds"] = llm_config.timeout_seconds
            agent_dict["confidence_threshold"] = llm_config.confidence_threshold
            agent_dict["system_prompt"] = llm_config.system_prompt
            agent_dict["few_shot_examples"] = llm_config.few_shot_examples
        
        # Add patterns
        patterns = []
        for pattern in agent.patterns:
            patterns.append({
                "pattern_type": pattern.pattern_type,
                "pattern_value": pattern.pattern_value,
                "confidence_boost": pattern.confidence_boost,
                "priority": pattern.priority
            })
        agent_dict["patterns"] = patterns
        
        # Add tools
        tools = []
        for tool in agent.tools:
            tools.append({
                "tool_name": tool.tool_name,
                "tool_description": tool.tool_description,
                "tool_class_path": tool.tool_class_path,
                "parameters": tool.parameters,
                "is_enabled": tool.is_enabled
            })
        agent_dict["tools"] = tools
        
        # Add response templates
        templates = []
        for template in agent.response_templates:
            templates.append({
                "template_key": template.template_key,
                "template_content": template.template_content,
                "template_type": template.template_type,
                "language": template.language,
                "tone": template.tone,
                "version": template.version
            })
        agent_dict["response_templates"] = templates
        
        return agent_dict
    
    async def _clone_agent_config(self, source: AgentDefinition, target: AgentDefinition) -> None:
        """
        Clone configuration from a source agent to a target agent.
        
        Args:
            source: Source agent definition
            target: Target agent definition
        """
        # Clone LLM configuration
        for config in source.llm_configuration:
            new_config = LlmAgentConfiguration(
                agent_id=target.id,
                model_name=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                timeout_seconds=config.timeout_seconds,
                confidence_threshold=config.confidence_threshold,
                system_prompt=config.system_prompt,
                few_shot_examples=config.few_shot_examples,
                output_parser=config.output_parser
            )
            self.db_session.add(new_config)
        
        # Clone patterns
        for pattern in source.patterns:
            new_pattern = AgentPattern(
                agent_id=target.id,
                pattern_type=pattern.pattern_type,
                pattern_value=pattern.pattern_value,
                confidence_boost=pattern.confidence_boost,
                priority=pattern.priority
            )
            self.db_session.add(new_pattern)
        
        # Clone tools
        for tool in source.tools:
            new_tool = AgentTool(
                agent_id=target.id,
                tool_name=tool.tool_name,
                tool_description=tool.tool_description,
                tool_class_path=tool.tool_class_path,
                parameters=tool.parameters,
                is_enabled=tool.is_enabled
            )
            self.db_session.add(new_tool)
        
        # Clone response templates
        for template in source.response_templates:
            new_template = AgentResponseTemplate(
                agent_id=target.id,
                template_key=template.template_key,
                template_content=template.template_content,
                template_type=template.template_type,
                language=template.language,
                tone=template.tone,
                version=template.version
            )
            self.db_session.add(new_template)
        
        # Clone entity mappings
        for mapping in source.entity_mappings:
            new_mapping = AgentEntityMapping(
                agent_id=target.id,
                entity_id=mapping.entity_id,
                extraction_strategy=mapping.extraction_strategy,
                confidence_threshold=mapping.confidence_threshold,
                is_required=mapping.is_required,
                persistence_scope=mapping.persistence_scope
            )
            self.db_session.add(new_mapping)
        
        await self.db_session.flush()
    
    async def _create_llm_config(self, agent_id: str, config_data: AgentLlmConfigModel) -> None:
        """
        Create LLM configuration for an agent.
        
        Args:
            agent_id: Agent ID
            config_data: LLM configuration data
        """
        # Check if configuration already exists
        existing_config = await self.agent_repository.get_llm_config(agent_id)
        if existing_config:
            raise ValueError(f"LLM configuration already exists for agent {agent_id}")
        
        # Create configuration
        llm_config = LlmAgentConfiguration(
            agent_id=uuid.UUID(agent_id),
            model_name=config_data.model_name,
            temperature=config_data.temperature,
            max_tokens=config_data.max_tokens,
            timeout_seconds=config_data.timeout_seconds,
            confidence_threshold=config_data.confidence_threshold,
            few_shot_examples=config_data.few_shot_examples,
            output_parser=config_data.output_parser
        )
        
        self.db_session.add(llm_config)
        await self.db_session.flush()
    
    async def _update_llm_config(self, agent_id: str, config_data: AgentLlmConfigModel) -> None:
        """
        Update LLM configuration for an agent.
        
        Args:
            agent_id: Agent ID
            config_data: Updated LLM configuration data
        """
        # Get existing configuration
        config = await self.agent_repository.get_llm_config(agent_id)
        if not config:
            await self._create_llm_config(agent_id, config_data)
            return
        
        # Update configuration
        config.model_name = config_data.model_name
        config.temperature = config_data.temperature
        config.max_tokens = config_data.max_tokens
        config.timeout_seconds = config_data.timeout_seconds
        config.confidence_threshold = config_data.confidence_threshold
        config.few_shot_examples = config_data.few_shot_examples
        config.output_parser = config_data.output_parser
        
        self.db_session.add(config)
        await self.db_session.flush()
    
    async def _get_llm_config_model(self, agent_id: str) -> Optional[AgentLlmConfigModel]:
        """
        Get LLM configuration model for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            LLM configuration model or None if not found
        """
        config = await self.agent_repository.get_llm_config(agent_id)
        if not config:
            return None
        
        return AgentLlmConfigModel(
            model_name=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            timeout_seconds=config.timeout_seconds,
            confidence_threshold=config.confidence_threshold,
            few_shot_examples=config.few_shot_examples,
            output_parser=config.output_parser
        )
    
    async def _create_pattern(self, agent_id: str, pattern_data: AgentPatternModel) -> None:
        """
        Create a pattern for an agent.
        
        Args:
            agent_id: Agent ID
            pattern_data: Pattern data
        """
        pattern = AgentPattern(
            agent_id=uuid.UUID(agent_id),
            pattern_type=pattern_data.pattern_type,
            pattern_value=pattern_data.pattern_value,
            confidence_boost=pattern_data.confidence_boost,
            priority=pattern_data.priority
        )
        
        self.db_session.add(pattern)
        await self.db_session.flush()
    
    async def _get_pattern_models(self, agent_id: str) -> List[AgentPatternModel]:
        """
        Get pattern models for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of pattern models
        """
        patterns = await self.agent_repository.get_agent_patterns(agent_id)
        result = []
        
        for pattern in patterns:
            pattern_model = AgentPatternModel(
                id=str(pattern.id),
                pattern_type=pattern.pattern_type,
                pattern_value=pattern.pattern_value,
                confidence_boost=pattern.confidence_boost,
                priority=pattern.priority
            )
            result.append(pattern_model)
        
        return result
    
    async def _create_response_template(self, agent_id: str, template_data: AgentResponseTemplateModel) -> None:
        """
        Create a response template for an agent.
        
        Args:
            agent_id: Agent ID
            template_data: Template data
        """
        template = AgentResponseTemplate(
            agent_id=uuid.UUID(agent_id),
            template_key=template_data.template_key,
            template_content=template_data.template_content,
            template_type=template_data.template_type,
            language=template_data.language,
            tone=template_data.tone,
            version=template_data.version
        )
        
        self.db_session.add(template)
        await self.db_session.flush()
    
    async def _get_response_template_models(self, agent_id: str) -> List[AgentResponseTemplateModel]:
        """
        Get response template models for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List of response template models
        """
        templates = await self.agent_repository.get_agent_response_templates(agent_id)
        result = []
        
        for template in templates:
            template_model = AgentResponseTemplateModel(
                id=str(template.id),
                template_key=template.template_key,
                template_content=template.template_content,
                template_type=template.template_type,
                language=template.language,
                tone=template.tone,
                version=template.version
            )
            result.append(template_model)
        
        return result
"""