"""
Repository for accessing agent configurations from the database.
This module implements the data access layer for agent definitions and related entities.
"""
import uuid
import logging
from typing import List, Dict, Any, Optional, Union, Tuple, TypeVar, Type

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from backend.database.agent_schema import (
    AgentDefinition, AgentDeployment, AgentComposition,
    LlmAgentConfiguration, RuleAgentConfiguration, RetrievalAgentConfiguration,
    AgentPattern, AgentPatternEmbedding, AgentTool, AgentResponseTemplate
)
from backend.database.entity_schema import (
    EntityDefinition, EntityEnumValue, AgentEntityMapping,
    EntityExtractionPattern, EntityTransformation
)

logger = logging.getLogger(__name__)

# Type variable for model classes
T = TypeVar('T')


class AgentRepository:
    """
    Repository for agent configurations.
    Provides methods to access and manipulate agent configurations in the database.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def get_agent_definition(
        self, agent_id: Union[uuid.UUID, str], load_related: bool = True
    ) -> Optional[AgentDefinition]:
        """
        Get an agent definition by ID.
        
        Args:
            agent_id: The ID of the agent
            load_related: Whether to load related entities (configurations, patterns, etc.)
            
        Returns:
            AgentDefinition or None if not found
        """
        if isinstance(agent_id, str):
            try:
                agent_id = uuid.UUID(agent_id)
            except ValueError:
                logger.error(f"Invalid UUID: {agent_id}")
                return None
        
        query = select(AgentDefinition).where(AgentDefinition.id == agent_id)
        
        if load_related:
            # Load all the related entities
            query = query.options(
                selectinload(AgentDefinition.deployments),
                selectinload(AgentDefinition.patterns).selectinload(AgentPattern.embedding),
                selectinload(AgentDefinition.tools),
                selectinload(AgentDefinition.response_templates),
                selectinload(AgentDefinition.entity_mappings).joinedload(AgentEntityMapping.entity),
                selectinload(AgentDefinition.child_relationships),
                selectinload(AgentDefinition.parent_relationships)
            )
        
        result = await self.session.execute(query)
        agent = result.scalar_one_or_none()
        
        if agent and load_related:
            # Load type-specific configuration based on agent type
            if agent.agent_type == "LLM":
                query = select(LlmAgentConfiguration).where(
                    LlmAgentConfiguration.agent_id == agent.id
                )
                result = await self.session.execute(query)
                agent.llm_configuration = result.scalar_one_or_none()
            elif agent.agent_type == "RULE":
                query = select(RuleAgentConfiguration).where(
                    RuleAgentConfiguration.agent_id == agent.id
                )
                result = await self.session.execute(query)
                agent.rule_configuration = result.scalar_one_or_none()
            elif agent.agent_type == "RETRIEVAL":
                query = select(RetrievalAgentConfiguration).where(
                    RetrievalAgentConfiguration.agent_id == agent.id
                )
                result = await self.session.execute(query)
                agent.retrieval_configuration = result.scalar_one_or_none()
        
        return agent
    
    async def get_all_active_agents(self) -> List[AgentDefinition]:
        """
        Get all active agent definitions.
        
        Returns:
            List of active agent definitions
        """
        return await self.list_agents(status="active")
    
    async def list_agents(
        self, 
        status: Optional[str] = None,
        agent_type: Optional[str] = None,
        environment: Optional[str] = None,
        is_system: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AgentDefinition]:
        """
        List agents with optional filtering.
        
        Args:
            status: Filter by status (draft, active, archived)
            agent_type: Filter by agent type (LLM, RULE, RETRIEVAL, etc.)
            environment: Filter by deployment environment
            is_system: Filter by whether the agent is a system agent
            limit: Maximum number of results to return
            offset: Offset for pagination
            
        Returns:
            List of matching agent definitions
        """
        query = select(AgentDefinition)
        
        # Apply filters
        filters = []
        if status is not None:
            filters.append(AgentDefinition.status == status)
        if agent_type is not None:
            filters.append(AgentDefinition.agent_type == agent_type)
        if is_system is not None:
            filters.append(AgentDefinition.is_system == is_system)
            
        # Environment filter requires a join
        if environment is not None:
            query = query.join(
                AgentDeployment,
                and_(
                    AgentDeployment.agent_definition_id == AgentDefinition.id,
                    AgentDeployment.environment == environment,
                    AgentDeployment.is_active == True
                )
            )
        
        if filters:
            query = query.where(and_(*filters))
            
        # Add pagination
        query = query.order_by(AgentDefinition.name).limit(limit).offset(offset)
        
        # Execute the query
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def list_active_deployments(
        self, environment: str
    ) -> List[AgentDeployment]:
        """
        List all active deployments for a given environment.
        
        Args:
            environment: The deployment environment (dev, staging, production)
            
        Returns:
            List of active deployments
        """
        query = select(AgentDeployment).where(
            and_(
                AgentDeployment.environment == environment,
                AgentDeployment.is_active == True
            )
        ).order_by(AgentDeployment.deployed_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create_agent(
        self, 
        name: str,
        description: str,
        agent_type: str,
        created_by: Optional[str] = None,
        is_system: bool = False,
        status: str = "draft"
    ) -> uuid.UUID:
        """
        Create a new agent definition.
        
        Args:
            name: Agent name
            description: Agent description
            agent_type: Agent type (LLM, RULE, RETRIEVAL, etc.)
            created_by: User who created the agent
            is_system: Whether this is a system agent
            status: Initial status (draft, active, archived)
            
        Returns:
            ID of the newly created agent
        """
        agent = AgentDefinition(
            name=name,
            description=description,
            agent_type=agent_type,
            created_by=created_by,
            is_system=is_system,
            status=status
        )
        
        self.session.add(agent)
        await self.session.flush()
        
        return agent.id
    
    async def update_agent(
        self, 
        agent_id: Union[uuid.UUID, str],
        **kwargs
    ) -> bool:
        """
        Update an agent definition.
        
        Args:
            agent_id: ID of the agent to update
            **kwargs: Fields to update
            
        Returns:
            True if successful, False otherwise
        """
        if isinstance(agent_id, str):
            try:
                agent_id = uuid.UUID(agent_id)
            except ValueError:
                logger.error(f"Invalid UUID: {agent_id}")
                return False
        
        agent = await self.get_agent_definition(agent_id, load_related=False)
        if not agent:
            return False
        
        # Update the fields
        valid_fields = ['name', 'description', 'status', 'version']
        for field, value in kwargs.items():
            if field in valid_fields:
                setattr(agent, field, value)
        
        await self.session.flush()
        return True
    
    async def delete_agent(self, agent_id: Union[uuid.UUID, str]) -> bool:
        """
        Delete an agent definition.
        
        Args:
            agent_id: ID of the agent to delete
            
        Returns:
            True if successful, False otherwise
        """
        if isinstance(agent_id, str):
            try:
                agent_id = uuid.UUID(agent_id)
            except ValueError:
                logger.error(f"Invalid UUID: {agent_id}")
                return False
        
        agent = await self.get_agent_definition(agent_id, load_related=False)
        if not agent:
            return False
        
        await self.session.delete(agent)
        await self.session.flush()
        return True
    
    async def create_deployment(
        self,
        agent_id: Union[uuid.UUID, str],
        environment: str,
        deployed_by: Optional[str] = None,
        deployment_notes: Optional[str] = None
    ) -> uuid.UUID:
        """
        Create a new agent deployment.
        
        Args:
            agent_id: ID of the agent
            environment: Deployment environment (dev, staging, production)
            deployed_by: User who created the deployment
            deployment_notes: Notes about the deployment
            
        Returns:
            ID of the newly created deployment
        """
        if isinstance(agent_id, str):
            try:
                agent_id = uuid.UUID(agent_id)
            except ValueError:
                logger.error(f"Invalid UUID: {agent_id}")
                raise ValueError(f"Invalid agent_id: {agent_id}")
        
        # Check if agent exists
        agent = await self.get_agent_definition(agent_id, load_related=False)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
        
        # Deactivate any existing deployments for this agent in this environment
        query = select(AgentDeployment).where(
            and_(
                AgentDeployment.agent_definition_id == agent_id,
                AgentDeployment.environment == environment,
                AgentDeployment.is_active == True
            )
        )
        result = await self.session.execute(query)
        
        for existing_deployment in result.scalars().all():
            existing_deployment.is_active = False
        
        # Create new deployment
        deployment = AgentDeployment(
            agent_definition_id=agent_id,
            environment=environment,
            deployed_by=deployed_by,
            deployment_notes=deployment_notes,
            is_active=True
        )
        
        self.session.add(deployment)
        await self.session.flush()
        
        return deployment.id
    
    async def get_agent_patterns(
        self, agent_id: Union[uuid.UUID, str]
    ) -> List[AgentPattern]:
        """
        Get all patterns for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of agent patterns
        """
        if isinstance(agent_id, str):
            try:
                agent_id = uuid.UUID(agent_id)
            except ValueError:
                logger.error(f"Invalid UUID: {agent_id}")
                return []
        
        query = select(AgentPattern).where(
            AgentPattern.agent_id == agent_id
        ).options(
            selectinload(AgentPattern.embedding)
        ).order_by(AgentPattern.priority.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def add_agent_pattern(
        self,
        agent_id: Union[uuid.UUID, str],
        pattern_type: str,
        pattern_value: str,
        priority: int = 0,
        confidence_boost: float = 0.1
    ) -> uuid.UUID:
        """
        Add a pattern to an agent.
        
        Args:
            agent_id: ID of the agent
            pattern_type: Type of pattern (regex, keyword, semantic)
            pattern_value: The pattern value
            priority: Pattern priority (higher number = higher priority)
            confidence_boost: Confidence boost when pattern matches
            
        Returns:
            ID of the newly created pattern
        """
        if isinstance(agent_id, str):
            try:
                agent_id = uuid.UUID(agent_id)
            except ValueError:
                logger.error(f"Invalid UUID: {agent_id}")
                raise ValueError(f"Invalid agent_id: {agent_id}")
        
        pattern = AgentPattern(
            agent_id=agent_id,
            pattern_type=pattern_type,
            pattern_value=pattern_value,
            priority=priority,
            confidence_boost=confidence_boost
        )
        
        self.session.add(pattern)
        await self.session.flush()
        
        return pattern.id
    
    async def add_pattern_embedding(
        self,
        pattern_id: Union[uuid.UUID, str],
        embedding_vector: List[float],
        embedding_model: str
    ) -> bool:
        """
        Add an embedding to a pattern.
        
        Args:
            pattern_id: ID of the pattern
            embedding_vector: The embedding vector
            embedding_model: The model used to generate the embedding
            
        Returns:
            True if successful, False otherwise
        """
        if isinstance(pattern_id, str):
            try:
                pattern_id = uuid.UUID(pattern_id)
            except ValueError:
                logger.error(f"Invalid UUID: {pattern_id}")
                return False
        
        # Check if embedding already exists
        query = select(AgentPatternEmbedding).where(
            AgentPatternEmbedding.pattern_id == pattern_id
        )
        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing embedding
            existing.embedding_vector = embedding_vector
            existing.embedding_model = embedding_model
        else:
            # Create new embedding
            embedding = AgentPatternEmbedding(
                pattern_id=pattern_id,
                embedding_vector=embedding_vector,
                embedding_model=embedding_model
            )
            self.session.add(embedding)
        
        await self.session.flush()
        return True
    
    async def get_agent_tools(
        self, agent_id: Union[uuid.UUID, str]
    ) -> List[AgentTool]:
        """
        Get all tools for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of agent tools
        """
        if isinstance(agent_id, str):
            try:
                agent_id = uuid.UUID(agent_id)
            except ValueError:
                logger.error(f"Invalid UUID: {agent_id}")
                return []
        
        query = select(AgentTool).where(
            AgentTool.agent_id == agent_id
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def add_agent_tool(
        self,
        agent_id: Union[uuid.UUID, str],
        tool_name: str,
        tool_description: Optional[str] = None,
        tool_class_path: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        is_enabled: bool = True,
        requires_confirmation: bool = False
    ) -> uuid.UUID:
        """
        Add a tool to an agent.
        
        Args:
            agent_id: ID of the agent
            tool_name: Name of the tool
            tool_description: Description of the tool
            tool_class_path: Python path to the tool implementation
            parameters: Tool parameters
            is_enabled: Whether the tool is enabled
            requires_confirmation: Whether the tool requires user confirmation
            
        Returns:
            ID of the newly created tool
        """
        if isinstance(agent_id, str):
            try:
                agent_id = uuid.UUID(agent_id)
            except ValueError:
                logger.error(f"Invalid UUID: {agent_id}")
                raise ValueError(f"Invalid agent_id: {agent_id}")
        
        tool = AgentTool(
            agent_id=agent_id,
            tool_name=tool_name,
            tool_description=tool_description,
            tool_class_path=tool_class_path,
            parameters=parameters or {},
            is_enabled=is_enabled,
            requires_confirmation=requires_confirmation
        )
        
        self.session.add(tool)
        await self.session.flush()
        
        return tool.id
    
    async def get_response_template(
        self,
        agent_id: Union[uuid.UUID, str],
        template_key: str,
        language: str = "en",
        version: Optional[int] = None,
        is_fallback: Optional[bool] = None
    ) -> Optional[AgentResponseTemplate]:
        """
        Get a response template.
        
        Args:
            agent_id: ID of the agent
            template_key: The template key
            language: Template language code
            version: Specific version to retrieve (None for latest)
            is_fallback: Whether to get fallback template only
            
        Returns:
            The response template or None if not found
        """
        if isinstance(agent_id, str):
            try:
                agent_id = uuid.UUID(agent_id)
            except ValueError:
                logger.error(f"Invalid UUID: {agent_id}")
                return None
        
        query = select(AgentResponseTemplate).where(
            and_(
                AgentResponseTemplate.agent_id == agent_id,
                AgentResponseTemplate.template_key == template_key,
                AgentResponseTemplate.language == language
            )
        )
        
        if version is not None:
            query = query.where(AgentResponseTemplate.version == version)
        
        if is_fallback is not None:
            query = query.where(AgentResponseTemplate.is_fallback == is_fallback)
        
        if version is None:
            # Get the latest version
            query = query.order_by(AgentResponseTemplate.version.desc())
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def add_response_template(
        self,
        agent_id: Union[uuid.UUID, str],
        template_key: str,
        template_content: str,
        language: str = "en",
        template_type: str = "text",
        scenario: Optional[str] = None,
        tone: str = "neutral",
        is_fallback: bool = False
    ) -> uuid.UUID:
        """
        Add a response template to an agent.
        
        Args:
            agent_id: ID of the agent
            template_key: Template identifier
            template_content: The template content
            language: Language code
            template_type: Template type (text, markdown, html)
            scenario: Optional scenario classification
            tone: Template tone (friendly, formal, etc.)
            is_fallback: Whether this is a fallback template
            
        Returns:
            ID of the newly created template
        """
        if isinstance(agent_id, str):
            try:
                agent_id = uuid.UUID(agent_id)
            except ValueError:
                logger.error(f"Invalid UUID: {agent_id}")
                raise ValueError(f"Invalid agent_id: {agent_id}")
        
        # Get the latest version
        query = select(func.max(AgentResponseTemplate.version)).where(
            and_(
                AgentResponseTemplate.agent_id == agent_id,
                AgentResponseTemplate.template_key == template_key,
                AgentResponseTemplate.language == language
            )
        )
        result = await self.session.execute(query)
        max_version = result.scalar() or 0
        
        template = AgentResponseTemplate(
            agent_id=agent_id,
            template_key=template_key,
            template_content=template_content,
            language=language,
            template_type=template_type,
            scenario=scenario,
            tone=tone,
            is_fallback=is_fallback,
            version=max_version + 1
        )
        
        self.session.add(template)
        await self.session.flush()
        
        return template.id
    
    # Entity-related methods
    
    async def get_entity_definition(
        self, entity_id: Union[uuid.UUID, str]
    ) -> Optional[EntityDefinition]:
        """
        Get an entity definition by ID.
        
        Args:
            entity_id: The ID of the entity
            
        Returns:
            EntityDefinition or None if not found
        """
        if isinstance(entity_id, str):
            try:
                entity_id = uuid.UUID(entity_id)
            except ValueError:
                logger.error(f"Invalid UUID: {entity_id}")
                return None
        
        query = select(EntityDefinition).where(
            EntityDefinition.id == entity_id
        ).options(
            selectinload(EntityDefinition.enum_values),
            selectinload(EntityDefinition.extraction_patterns),
            selectinload(EntityDefinition.transformations)
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_entity_by_name(
        self, name: str
    ) -> Optional[EntityDefinition]:
        """
        Get an entity definition by name.
        
        Args:
            name: The name of the entity
            
        Returns:
            EntityDefinition or None if not found
        """
        query = select(EntityDefinition).where(
            EntityDefinition.name == name
        ).options(
            selectinload(EntityDefinition.enum_values),
            selectinload(EntityDefinition.extraction_patterns),
            selectinload(EntityDefinition.transformations)
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def list_entities(
        self, entity_type: Optional[str] = None
    ) -> List[EntityDefinition]:
        """
        List all entity definitions with optional filtering.
        
        Args:
            entity_type: Optional filter by entity type
            
        Returns:
            List of EntityDefinition objects
        """
        query = select(EntityDefinition)
        
        if entity_type:
            query = query.where(EntityDefinition.entity_type == entity_type)
        
        query = query.order_by(EntityDefinition.name)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create_entity(
        self,
        name: str,
        display_name: str,
        entity_type: str,
        description: Optional[str] = None,
        validation_regex: Optional[str] = None,
        is_required: bool = False,
        default_value: Optional[str] = None
    ) -> uuid.UUID:
        """
        Create a new entity definition.
        
        Args:
            name: Entity name (code identifier)
            display_name: Human-readable name
            entity_type: Entity type (basic, composite, enum, regex)
            description: Optional description
            validation_regex: Optional regex for validation
            is_required: Whether this entity is required
            default_value: Optional default value
            
        Returns:
            ID of the newly created entity
        """
        entity = EntityDefinition(
            name=name,
            display_name=display_name,
            entity_type=entity_type,
            description=description,
            validation_regex=validation_regex,
            is_required=is_required,
            default_value=default_value
        )
        
        self.session.add(entity)
        await self.session.flush()
        
        return entity.id
    
    async def add_entity_enum_value(
        self,
        entity_id: Union[uuid.UUID, str],
        value: str,
        display_text: str,
        is_default: bool = False
    ) -> uuid.UUID:
        """
        Add an enum value to an entity.
        
        Args:
            entity_id: ID of the entity
            value: The actual value
            display_text: Display text for the value
            is_default: Whether this is the default value
            
        Returns:
            ID of the newly created enum value
        """
        if isinstance(entity_id, str):
            try:
                entity_id = uuid.UUID(entity_id)
            except ValueError:
                logger.error(f"Invalid UUID: {entity_id}")
                raise ValueError(f"Invalid entity_id: {entity_id}")
        
        enum_value = EntityEnumValue(
            entity_id=entity_id,
            value=value,
            display_text=display_text,
            is_default=is_default
        )
        
        self.session.add(enum_value)
        await self.session.flush()
        
        return enum_value.id
    
    async def get_agent_entities(
        self, 
        agent_id: Union[uuid.UUID, str],
        is_required: Optional[bool] = None
    ) -> List[AgentEntityMapping]:
        """
        Get all entity mappings for an agent.
        
        Args:
            agent_id: ID of the agent
            is_required: Optional filter for required entities only
            
        Returns:
            List of agent-entity mappings
        """
        if isinstance(agent_id, str):
            try:
                agent_id = uuid.UUID(agent_id)
            except ValueError:
                logger.error(f"Invalid UUID: {agent_id}")
                return []
        
        query = select(AgentEntityMapping).where(
            AgentEntityMapping.agent_id == agent_id
        ).options(
            joinedload(AgentEntityMapping.entity)
        )
        
        if is_required is not None:
            query = query.where(AgentEntityMapping.is_required == is_required)
        
        query = query.order_by(AgentEntityMapping.extraction_priority.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def map_entity_to_agent(
        self,
        agent_id: Union[uuid.UUID, str],
        entity_id: Union[uuid.UUID, str],
        is_required: bool = False,
        extraction_priority: int = 0,
        prompt_for_missing: bool = True,
        prompt_text: Optional[str] = None,
        extraction_method: str = "llm",
        extraction_config: Optional[Dict[str, Any]] = None
    ) -> uuid.UUID:
        """
        Map an entity to an agent with extraction configuration.
        
        Args:
            agent_id: ID of the agent
            entity_id: ID of the entity
            is_required: Whether the entity is required for the agent
            extraction_priority: Priority order for extraction
            prompt_for_missing: Whether to prompt user if entity is missing
            prompt_text: Text to use when prompting for this entity
            extraction_method: Method to use for extraction (llm, regex, etc.)
            extraction_config: Configuration for the extraction method
            
        Returns:
            ID of the newly created mapping
        """
        if isinstance(agent_id, str):
            try:
                agent_id = uuid.UUID(agent_id)
            except ValueError:
                logger.error(f"Invalid UUID: {agent_id}")
                raise ValueError(f"Invalid agent_id: {agent_id}")
                
        if isinstance(entity_id, str):
            try:
                entity_id = uuid.UUID(entity_id)
            except ValueError:
                logger.error(f"Invalid UUID: {entity_id}")
                raise ValueError(f"Invalid entity_id: {entity_id}")
        
        mapping = AgentEntityMapping(
            agent_id=agent_id,
            entity_id=entity_id,
            is_required=is_required,
            extraction_priority=extraction_priority,
            prompt_for_missing=prompt_for_missing,
            prompt_text=prompt_text,
            extraction_method=extraction_method,
            extraction_config=extraction_config or {}
        )
        
        self.session.add(mapping)
        await self.session.flush()
        
        return mapping.id
    
    async def add_entity_extraction_pattern(
        self,
        entity_id: Union[uuid.UUID, str],
        pattern_type: str,
        pattern_value: str,
        confidence_value: float = 0.8,
        description: Optional[str] = None
    ) -> uuid.UUID:
        """
        Add an extraction pattern to an entity.
        
        Args:
            entity_id: ID of the entity
            pattern_type: Type of pattern (regex, example, prompt)
            pattern_value: The actual pattern
            confidence_value: Confidence score for this pattern
            description: Optional description of what this pattern matches
            
        Returns:
            ID of the newly created pattern
        """
        if isinstance(entity_id, str):
            try:
                entity_id = uuid.UUID(entity_id)
            except ValueError:
                logger.error(f"Invalid UUID: {entity_id}")
                raise ValueError(f"Invalid entity_id: {entity_id}")
        
        pattern = EntityExtractionPattern(
            entity_id=entity_id,
            pattern_type=pattern_type,
            pattern_value=pattern_value,
            confidence_value=confidence_value,
            description=description
        )
        
        self.session.add(pattern)
        await self.session.flush()
        
        return pattern.id
    
    async def get_entity_patterns(
        self, 
        entity_id: Union[uuid.UUID, str],
        pattern_type: Optional[str] = None
    ) -> List[EntityExtractionPattern]:
        """
        Get extraction patterns for an entity.
        
        Args:
            entity_id: ID of the entity
            pattern_type: Optional filter by pattern type
            
        Returns:
            List of extraction patterns
        """
        if isinstance(entity_id, str):
            try:
                entity_id = uuid.UUID(entity_id)
            except ValueError:
                logger.error(f"Invalid UUID: {entity_id}")
                return []
        
        query = select(EntityExtractionPattern).where(
            EntityExtractionPattern.entity_id == entity_id
        )
        
        if pattern_type:
            query = query.where(EntityExtractionPattern.pattern_type == pattern_type)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def add_entity_transformation(
        self,
        entity_id: Union[uuid.UUID, str],
        transformation_type: str,
        transformation_order: int,
        transformation_config: Dict[str, Any],
        description: Optional[str] = None
    ) -> uuid.UUID:
        """
        Add a transformation to an entity.
        
        Args:
            entity_id: ID of the entity
            transformation_type: Type of transformation (normalize, format, validate)
            transformation_order: Order of application
            transformation_config: Configuration for the transformation
            description: Optional description
            
        Returns:
            ID of the newly created transformation
        """
        if isinstance(entity_id, str):
            try:
                entity_id = uuid.UUID(entity_id)
            except ValueError:
                logger.error(f"Invalid UUID: {entity_id}")
                raise ValueError(f"Invalid entity_id: {entity_id}")
        
        transformation = EntityTransformation(
            entity_id=entity_id,
            transformation_type=transformation_type,
            transformation_order=transformation_order,
            transformation_config=transformation_config,
            description=description
        )
        
        self.session.add(transformation)
        await self.session.flush()
        
        return transformation.id
    
    async def get_entity_transformations(
        self, entity_id: Union[uuid.UUID, str]
    ) -> List[EntityTransformation]:
        """
        Get transformations for an entity.
        
        Args:
            entity_id: ID of the entity
            
        Returns:
            List of transformations, sorted by order
        """
        if isinstance(entity_id, str):
            try:
                entity_id = uuid.UUID(entity_id)
            except ValueError:
                logger.error(f"Invalid UUID: {entity_id}")
                return []
        
        query = select(EntityTransformation).where(
            EntityTransformation.entity_id == entity_id
        ).order_by(EntityTransformation.transformation_order)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())