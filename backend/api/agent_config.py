"""
API routes for agent configuration management.
"""
import uuid
import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_agent_repository

# Direct dependency function to avoid circular imports
def get_db_direct():
    """
    Get a database session directly.
    This is a temporary solution to avoid circular imports.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    import os
    
    # Create minimal db engine for dependency
    db_url = os.environ.get("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    return AsyncSession(engine)
from backend.repositories.agent_repository import AgentRepository
from backend.api.schemas.agent_schema import (
    AgentCreate, AgentUpdate, AgentResponse, AgentListResponse,
    AgentDetailResponse, DeploymentCreate, DeploymentResponse,
    PatternCreate, PatternResponse, ResponseTemplateCreate,
    ResponseTemplateResponse, AgentConfigCreate
)
from backend.api.schemas.entity_schema import (
    EntityMappingCreate, EntityMappingResponse
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/agent-config",
    tags=["agent-config"],
    responses={404: {"description": "Not found"}},
)


@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    status: Optional[str] = Query(None, description="Filter by status (draft, active, archived)"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    environment: Optional[str] = Query(None, description="Filter by deployment environment"),
    is_system: Optional[bool] = Query(None, description="Filter by system agent flag"),
    limit: int = Query(100, description="Maximum number of results to return"),
    offset: int = Query(0, description="Offset for pagination"),
    agent_repo: AgentRepository = Depends(get_agent_repository)
):
    """
    List agents with optional filtering.
    
    Args:
        status: Filter by status (draft, active, archived)
        agent_type: Filter by agent type (LLM, RULE, RETRIEVAL, etc.)
        environment: Filter by deployment environment
        is_system: Filter by whether the agent is a system agent
        limit: Maximum number of results to return
        offset: Offset for pagination
        agent_repo: Agent repository dependency
        
    Returns:
        List of matching agent definitions
    """
    try:
        agents = await agent_repo.list_agents(
            status=status,
            agent_type=agent_type,
            environment=environment,
            is_system=is_system,
            limit=limit,
            offset=offset
        )
        
        # Convert to response models
        items = [
            AgentResponse(
                id=agent.id,
                name=agent.name,
                description=agent.description,
                agent_type=agent.agent_type,
                is_system=agent.is_system,
                status=agent.status,
                version=agent.version,
                created_at=agent.created_at,
                updated_at=agent.updated_at,
                created_by=agent.created_by
            ) for agent in agents
        ]
        
        # Get total count
        total = len(items)  # In a real implementation, you'd do a separate count query
        
        return AgentListResponse(items=items, total=total)
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing agents: {str(e)}"
        )


@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    agent_repo: AgentRepository = Depends(get_agent_repository),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new agent.
    
    Args:
        agent_data: Agent data
        agent_repo: Agent repository dependency
        db: Database session
        
    Returns:
        The newly created agent
    """
    try:
        agent_id = await agent_repo.create_agent(
            name=agent_data.name,
            description=agent_data.description,
            agent_type=agent_data.agent_type,
            is_system=agent_data.is_system
        )
        
        await db.commit()
        
        # Get the created agent
        agent = await agent_repo.get_agent_definition(agent_id, load_related=False)
        
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            agent_type=agent.agent_type,
            is_system=agent.is_system,
            status=agent.status,
            version=agent.version,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            created_by=agent.created_by
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating agent: {str(e)}"
        )


@router.get("/agents/{agent_id}", response_model=AgentDetailResponse)
async def get_agent(
    agent_id: uuid.UUID = Path(..., description="The ID of the agent"),
    agent_repo: AgentRepository = Depends(get_agent_repository)
):
    """
    Get an agent by ID.
    
    Args:
        agent_id: The ID of the agent
        agent_repo: Agent repository dependency
        
    Returns:
        The agent with the specified ID
    """
    try:
        agent = await agent_repo.get_agent_definition(agent_id)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {agent_id}"
            )
        
        # Build the response
        response = AgentDetailResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            agent_type=agent.agent_type,
            is_system=agent.is_system,
            status=agent.status,
            version=agent.version,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            created_by=agent.created_by,
            patterns=[],
            response_templates=[]
        )
        
        # Add type-specific configuration
        if agent.agent_type == "LLM" and hasattr(agent, "llm_configuration"):
            if agent.llm_configuration:
                response.llm_config = {
                    "model_name": agent.llm_configuration.model_name,
                    "temperature": agent.llm_configuration.temperature,
                    "max_tokens": agent.llm_configuration.max_tokens,
                    "timeout_seconds": agent.llm_configuration.timeout_seconds,
                    "confidence_threshold": agent.llm_configuration.confidence_threshold,
                    "system_prompt": agent.llm_configuration.system_prompt,
                    "few_shot_examples": agent.llm_configuration.few_shot_examples,
                    "output_parser": agent.llm_configuration.output_parser
                }
        elif agent.agent_type == "RULE" and hasattr(agent, "rule_configuration"):
            if agent.rule_configuration:
                response.rule_config = {
                    "rules": agent.rule_configuration.rules,
                    "default_confidence": agent.rule_configuration.default_confidence,
                    "fallback_message": agent.rule_configuration.fallback_message
                }
        elif agent.agent_type == "RETRIEVAL" and hasattr(agent, "retrieval_configuration"):
            if agent.retrieval_configuration:
                response.retrieval_config = {
                    "vector_store_id": agent.retrieval_configuration.vector_store_id,
                    "search_type": agent.retrieval_configuration.search_type,
                    "top_k": agent.retrieval_configuration.top_k,
                    "similarity_threshold": agent.retrieval_configuration.similarity_threshold,
                    "reranker_config": agent.retrieval_configuration.reranker_config
                }
        
        # Add patterns
        if agent.patterns:
            response.patterns = [
                PatternResponse(
                    id=pattern.id,
                    agent_id=pattern.agent_id,
                    pattern_type=pattern.pattern_type,
                    pattern_value=pattern.pattern_value,
                    priority=pattern.priority,
                    confidence_boost=pattern.confidence_boost,
                    created_at=pattern.created_at
                ) for pattern in agent.patterns
            ]
        
        # Add response templates
        if agent.response_templates:
            response.response_templates = [
                ResponseTemplateResponse(
                    id=template.id,
                    agent_id=template.agent_id,
                    template_key=template.template_key,
                    template_content=template.template_content,
                    template_type=template.template_type,
                    scenario=template.scenario,
                    language=template.language,
                    tone=template.tone,
                    is_fallback=template.is_fallback,
                    version=template.version,
                    created_at=template.created_at,
                    updated_at=template.updated_at
                ) for template in agent.response_templates
            ]
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting agent: {str(e)}"
        )


@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_data: AgentUpdate,
    agent_id: uuid.UUID = Path(..., description="The ID of the agent"),
    agent_repo: AgentRepository = Depends(get_agent_repository),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an agent.
    
    Args:
        agent_data: Agent data
        agent_id: The ID of the agent
        agent_repo: Agent repository dependency
        db: Database session
        
    Returns:
        The updated agent
    """
    try:
        # Check if agent exists
        agent = await agent_repo.get_agent_definition(agent_id, load_related=False)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {agent_id}"
            )
        
        # Update the agent
        update_data = {}
        if agent_data.name is not None:
            update_data["name"] = agent_data.name
        if agent_data.description is not None:
            update_data["description"] = agent_data.description
        if agent_data.status is not None:
            update_data["status"] = agent_data.status
        
        # Only update if there's data to update
        if update_data:
            success = await agent_repo.update_agent(agent_id, **update_data)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update agent: {agent_id}"
                )
            
            await db.commit()
            
            # Get the updated agent
            agent = await agent_repo.get_agent_definition(agent_id, load_related=False)
        
        return AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            agent_type=agent.agent_type,
            is_system=agent.is_system,
            status=agent.status,
            version=agent.version,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            created_by=agent.created_by
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating agent: {str(e)}"
        )


@router.delete("/agents/{agent_id}", response_model=dict)
async def delete_agent(
    agent_id: uuid.UUID = Path(..., description="The ID of the agent"),
    agent_repo: AgentRepository = Depends(get_agent_repository),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an agent.
    
    Args:
        agent_id: The ID of the agent
        agent_repo: Agent repository dependency
        db: Database session
        
    Returns:
        Success message
    """
    try:
        # Check if agent exists
        agent = await agent_repo.get_agent_definition(agent_id, load_related=False)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {agent_id}"
            )
        
        # Delete the agent
        success = await agent_repo.delete_agent(agent_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete agent: {agent_id}"
            )
        
        await db.commit()
        
        return {"message": f"Agent {agent_id} deleted successfully"}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting agent: {str(e)}"
        )


@router.post("/agents/{agent_id}/deploy", response_model=DeploymentResponse)
async def deploy_agent(
    deployment_data: DeploymentCreate,
    agent_id: uuid.UUID = Path(..., description="The ID of the agent"),
    agent_repo: AgentRepository = Depends(get_agent_repository),
    db: AsyncSession = Depends(get_db)
):
    """
    Deploy an agent to an environment.
    
    Args:
        deployment_data: Deployment data
        agent_id: The ID of the agent
        agent_repo: Agent repository dependency
        db: Database session
        
    Returns:
        The deployment information
    """
    try:
        # Check if agent exists
        agent = await agent_repo.get_agent_definition(agent_id, load_related=False)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {agent_id}"
            )
        
        # Create the deployment
        deployment_id = await agent_repo.create_deployment(
            agent_id=agent_id,
            environment=deployment_data.environment,
            deployment_notes=deployment_data.deployment_notes
        )
        
        await db.commit()
        
        # Get active deployments for this agent in this environment
        query = f"SELECT * FROM agent_deployments WHERE agent_definition_id = '{agent_id}' AND environment = '{deployment_data.environment}' AND is_active = true"
        result = await db.execute(query)
        deployment = result.fetchone()
        
        return DeploymentResponse(
            id=deployment.id,
            agent_id=deployment.agent_definition_id,
            environment=deployment.environment,
            is_active=deployment.is_active,
            deployed_at=deployment.deployed_at,
            deployed_by=deployment.deployed_by,
            deployment_notes=deployment.deployment_notes
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deploying agent: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deploying agent: {str(e)}"
        )


@router.post("/agents/{agent_id}/patterns", response_model=PatternResponse)
async def add_agent_pattern(
    pattern_data: PatternCreate,
    agent_id: uuid.UUID = Path(..., description="The ID of the agent"),
    agent_repo: AgentRepository = Depends(get_agent_repository),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a pattern to an agent.
    
    Args:
        pattern_data: Pattern data
        agent_id: The ID of the agent
        agent_repo: Agent repository dependency
        db: Database session
        
    Returns:
        The newly created pattern
    """
    try:
        # Check if agent exists
        agent = await agent_repo.get_agent_definition(agent_id, load_related=False)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {agent_id}"
            )
        
        # Create the pattern
        pattern_id = await agent_repo.add_agent_pattern(
            agent_id=agent_id,
            pattern_type=pattern_data.pattern_type,
            pattern_value=pattern_data.pattern_value,
            priority=pattern_data.priority,
            confidence_boost=pattern_data.confidence_boost
        )
        
        await db.commit()
        
        # Get the created pattern
        patterns = await agent_repo.get_agent_patterns(agent_id)
        pattern = next((p for p in patterns if p.id == pattern_id), None)
        
        if not pattern:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve created pattern: {pattern_id}"
            )
        
        return PatternResponse(
            id=pattern.id,
            agent_id=pattern.agent_id,
            pattern_type=pattern.pattern_type,
            pattern_value=pattern.pattern_value,
            priority=pattern.priority,
            confidence_boost=pattern.confidence_boost,
            created_at=pattern.created_at
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error adding pattern: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding pattern: {str(e)}"
        )


@router.post("/agents/{agent_id}/templates", response_model=ResponseTemplateResponse)
async def add_response_template(
    template_data: ResponseTemplateCreate,
    agent_id: uuid.UUID = Path(..., description="The ID of the agent"),
    agent_repo: AgentRepository = Depends(get_agent_repository),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a response template to an agent.
    
    Args:
        template_data: Template data
        agent_id: The ID of the agent
        agent_repo: Agent repository dependency
        db: Database session
        
    Returns:
        The newly created template
    """
    try:
        # Check if agent exists
        agent = await agent_repo.get_agent_definition(agent_id, load_related=False)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {agent_id}"
            )
        
        # Create the template
        template_id = await agent_repo.add_response_template(
            agent_id=agent_id,
            template_key=template_data.template_key,
            template_content=template_data.template_content,
            language=template_data.language,
            template_type=template_data.template_type,
            scenario=template_data.scenario,
            tone=template_data.tone,
            is_fallback=template_data.is_fallback
        )
        
        await db.commit()
        
        # Get the created template
        template = await agent_repo.get_response_template(
            agent_id=agent_id,
            template_key=template_data.template_key,
            language=template_data.language
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve created template: {template_id}"
            )
        
        return ResponseTemplateResponse(
            id=template.id,
            agent_id=template.agent_id,
            template_key=template.template_key,
            template_content=template.template_content,
            template_type=template.template_type,
            scenario=template.scenario,
            language=template.language,
            tone=template.tone,
            is_fallback=template.is_fallback,
            version=template.version,
            created_at=template.created_at,
            updated_at=template.updated_at
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error adding template: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding template: {str(e)}"
        )


@router.post("/agents/{agent_id}/entities", response_model=EntityMappingResponse)
async def map_entity_to_agent(
    mapping_data: EntityMappingCreate,
    agent_id: uuid.UUID = Path(..., description="The ID of the agent"),
    agent_repo: AgentRepository = Depends(get_agent_repository),
    db: AsyncSession = Depends(get_db)
):
    """
    Map an entity to an agent.
    
    Args:
        mapping_data: Mapping data
        agent_id: The ID of the agent
        agent_repo: Agent repository dependency
        db: Database session
        
    Returns:
        The entity mapping
    """
    try:
        # Check if agent exists
        agent = await agent_repo.get_agent_definition(agent_id, load_related=False)
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {agent_id}"
            )
        
        # Check if entity exists
        entity = await agent_repo.get_entity_definition(mapping_data.entity_id)
        
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity not found: {mapping_data.entity_id}"
            )
        
        # Create the mapping
        mapping_id = await agent_repo.map_entity_to_agent(
            agent_id=agent_id,
            entity_id=mapping_data.entity_id,
            is_required=mapping_data.is_required,
            extraction_priority=mapping_data.extraction_priority,
            prompt_for_missing=mapping_data.prompt_for_missing,
            prompt_text=mapping_data.prompt_text,
            extraction_method=mapping_data.extraction_method,
            extraction_config=mapping_data.extraction_config
        )
        
        await db.commit()
        
        # Get the mappings for this agent
        mappings = await agent_repo.get_agent_entities(agent_id)
        mapping = next((m for m in mappings if m.id == mapping_id), None)
        
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve created mapping: {mapping_id}"
            )
        
        # Build the entity response
        entity_response = EntityResponse(
            id=entity.id,
            name=entity.name,
            display_name=entity.display_name,
            description=entity.description,
            entity_type=entity.entity_type,
            validation_regex=entity.validation_regex,
            is_required=entity.is_required,
            default_value=entity.default_value,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
        
        return EntityMappingResponse(
            id=mapping.id,
            agent_id=mapping.agent_id,
            entity_id=mapping.entity_id,
            entity=entity_response,
            is_required=mapping.is_required,
            extraction_priority=mapping.extraction_priority,
            prompt_for_missing=mapping.prompt_for_missing,
            prompt_text=mapping.prompt_text,
            extraction_method=mapping.extraction_method,
            extraction_config=mapping.extraction_config
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error mapping entity: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error mapping entity: {str(e)}"
        )