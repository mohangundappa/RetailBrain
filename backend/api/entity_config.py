"""
API routes for entity configuration management.
"""
import uuid
import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_agent_repository, get_db
from backend.repositories.agent_repository import AgentRepository
from backend.api.schemas.entity_schema import (
    EntityCreate, EntityResponse, EntityDetailResponse,
    EntityEnumValueCreate, EntityEnumValueResponse,
    EntityPatternCreate, EntityPatternResponse,
    EntityTransformationCreate, EntityTransformationResponse
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/entity-config",
    tags=["entity-config"],
    responses={404: {"description": "Not found"}},
)


@router.get("/entities", response_model=List[EntityResponse])
async def list_entities(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    agent_repo: AgentRepository = Depends(get_agent_repository)
):
    """
    List entities with optional filtering.
    
    Args:
        entity_type: Filter by entity type
        agent_repo: Agent repository dependency
        
    Returns:
        List of matching entities
    """
    try:
        entities = await agent_repo.list_entities(entity_type=entity_type)
        
        return [
            EntityResponse(
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
            ) for entity in entities
        ]
    except Exception as e:
        logger.error(f"Error listing entities: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing entities: {str(e)}"
        )


@router.post("/entities", response_model=EntityResponse, status_code=status.HTTP_201_CREATED)
async def create_entity(
    entity_data: EntityCreate,
    agent_repo: AgentRepository = Depends(get_agent_repository),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new entity.
    
    Args:
        entity_data: Entity data
        agent_repo: Agent repository dependency
        db: Database session
        
    Returns:
        The newly created entity
    """
    try:
        entity_id = await agent_repo.create_entity(
            name=entity_data.name,
            display_name=entity_data.display_name,
            description=entity_data.description,
            entity_type=entity_data.entity_type,
            validation_regex=entity_data.validation_regex,
            is_required=entity_data.is_required,
            default_value=entity_data.default_value
        )
        
        await db.commit()
        
        # Get the created entity
        entity = await agent_repo.get_entity_definition(entity_id)
        
        return EntityResponse(
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
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating entity: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating entity: {str(e)}"
        )


@router.get("/entities/{entity_id}", response_model=EntityDetailResponse)
async def get_entity(
    entity_id: uuid.UUID = Path(..., description="The ID of the entity"),
    agent_repo: AgentRepository = Depends(get_agent_repository)
):
    """
    Get an entity by ID.
    
    Args:
        entity_id: The ID of the entity
        agent_repo: Agent repository dependency
        
    Returns:
        The entity with the specified ID
    """
    try:
        entity = await agent_repo.get_entity_definition(entity_id, load_related=True)
        
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity not found: {entity_id}"
            )
        
        # Build the basic response
        response = EntityDetailResponse(
            id=entity.id,
            name=entity.name,
            display_name=entity.display_name,
            description=entity.description,
            entity_type=entity.entity_type,
            validation_regex=entity.validation_regex,
            is_required=entity.is_required,
            default_value=entity.default_value,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            enum_values=[],
            extraction_patterns=[],
            transformations=[]
        )
        
        # Add enum values
        if entity.enum_values:
            response.enum_values = [
                EntityEnumValueResponse(
                    id=enum_val.id,
                    entity_id=enum_val.entity_id,
                    value=enum_val.value,
                    display_text=enum_val.display_text,
                    is_default=enum_val.is_default
                ) for enum_val in entity.enum_values
            ]
        
        # Add extraction patterns
        if entity.extraction_patterns:
            response.extraction_patterns = [
                EntityPatternResponse(
                    id=pattern.id,
                    entity_id=pattern.entity_id,
                    pattern_type=pattern.pattern_type,
                    pattern_value=pattern.pattern_value,
                    confidence_value=pattern.confidence_value,
                    description=pattern.description,
                    created_at=pattern.created_at
                ) for pattern in entity.extraction_patterns
            ]
        
        # Add transformations
        if entity.transformations:
            response.transformations = [
                EntityTransformationResponse(
                    id=transform.id,
                    entity_id=transform.entity_id,
                    transformation_type=transform.transformation_type,
                    transformation_order=transform.transformation_order,
                    transformation_config=transform.transformation_config,
                    description=transform.description,
                    created_at=transform.created_at
                ) for transform in entity.transformations
            ]
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting entity: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting entity: {str(e)}"
        )


@router.delete("/entities/{entity_id}", response_model=dict)
async def delete_entity(
    entity_id: uuid.UUID = Path(..., description="The ID of the entity"),
    agent_repo: AgentRepository = Depends(get_agent_repository),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an entity.
    
    Args:
        entity_id: The ID of the entity
        agent_repo: Agent repository dependency
        db: Database session
        
    Returns:
        Success message
    """
    try:
        # Check if entity exists
        entity = await agent_repo.get_entity_definition(entity_id)
        
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity not found: {entity_id}"
            )
        
        # Delete the entity
        success = await agent_repo.delete_entity(entity_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete entity: {entity_id}"
            )
        
        await db.commit()
        
        return {"message": f"Entity {entity_id} deleted successfully"}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting entity: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting entity: {str(e)}"
        )


@router.post("/entities/{entity_id}/enum-values", response_model=EntityEnumValueResponse)
async def add_enum_value(
    enum_data: EntityEnumValueCreate,
    entity_id: uuid.UUID = Path(..., description="The ID of the entity"),
    agent_repo: AgentRepository = Depends(get_agent_repository),
    db: AsyncSession = Depends(get_db)
):
    """
    Add an enum value to an entity.
    
    Args:
        enum_data: Enum value data
        entity_id: The ID of the entity
        agent_repo: Agent repository dependency
        db: Database session
        
    Returns:
        The newly created enum value
    """
    try:
        # Check if entity exists
        entity = await agent_repo.get_entity_definition(entity_id)
        
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity not found: {entity_id}"
            )
        
        # Check if entity is of type enum
        if entity.entity_type != "enum":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Entity {entity_id} is not of type 'enum'"
            )
        
        # Create the enum value
        enum_id = await agent_repo.add_enum_value(
            entity_id=entity_id,
            value=enum_data.value,
            display_text=enum_data.display_text,
            is_default=enum_data.is_default
        )
        
        await db.commit()
        
        # Get the created enum value
        enum_value = await agent_repo.get_enum_value(enum_id)
        
        if not enum_value:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve created enum value: {enum_id}"
            )
        
        return EntityEnumValueResponse(
            id=enum_value.id,
            entity_id=enum_value.entity_id,
            value=enum_value.value,
            display_text=enum_value.display_text,
            is_default=enum_value.is_default
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error adding enum value: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding enum value: {str(e)}"
        )


@router.post("/entities/{entity_id}/patterns", response_model=EntityPatternResponse)
async def add_entity_pattern(
    pattern_data: EntityPatternCreate,
    entity_id: uuid.UUID = Path(..., description="The ID of the entity"),
    agent_repo: AgentRepository = Depends(get_agent_repository),
    db: AsyncSession = Depends(get_db)
):
    """
    Add an extraction pattern to an entity.
    
    Args:
        pattern_data: Pattern data
        entity_id: The ID of the entity
        agent_repo: Agent repository dependency
        db: Database session
        
    Returns:
        The newly created pattern
    """
    try:
        # Check if entity exists
        entity = await agent_repo.get_entity_definition(entity_id)
        
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity not found: {entity_id}"
            )
        
        # Create the pattern
        pattern_id = await agent_repo.add_entity_pattern(
            entity_id=entity_id,
            pattern_type=pattern_data.pattern_type,
            pattern_value=pattern_data.pattern_value,
            confidence_value=pattern_data.confidence_value,
            description=pattern_data.description
        )
        
        await db.commit()
        
        # Get the created pattern
        pattern = await agent_repo.get_entity_pattern(pattern_id)
        
        if not pattern:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve created pattern: {pattern_id}"
            )
        
        return EntityPatternResponse(
            id=pattern.id,
            entity_id=pattern.entity_id,
            pattern_type=pattern.pattern_type,
            pattern_value=pattern.pattern_value,
            confidence_value=pattern.confidence_value,
            description=pattern.description,
            created_at=pattern.created_at
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error adding entity pattern: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding entity pattern: {str(e)}"
        )


@router.post("/entities/{entity_id}/transformations", response_model=EntityTransformationResponse)
async def add_entity_transformation(
    transformation_data: EntityTransformationCreate,
    entity_id: uuid.UUID = Path(..., description="The ID of the entity"),
    agent_repo: AgentRepository = Depends(get_agent_repository),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a transformation to an entity.
    
    Args:
        transformation_data: Transformation data
        entity_id: The ID of the entity
        agent_repo: Agent repository dependency
        db: Database session
        
    Returns:
        The newly created transformation
    """
    try:
        # Check if entity exists
        entity = await agent_repo.get_entity_definition(entity_id)
        
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity not found: {entity_id}"
            )
        
        # Create the transformation
        transformation_id = await agent_repo.add_entity_transformation(
            entity_id=entity_id,
            transformation_type=transformation_data.transformation_type,
            transformation_order=transformation_data.transformation_order,
            transformation_config=transformation_data.transformation_config,
            description=transformation_data.description
        )
        
        await db.commit()
        
        # Get the created transformation
        transformation = await agent_repo.get_entity_transformation(transformation_id)
        
        if not transformation:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve created transformation: {transformation_id}"
            )
        
        return EntityTransformationResponse(
            id=transformation.id,
            entity_id=transformation.entity_id,
            transformation_type=transformation.transformation_type,
            transformation_order=transformation.transformation_order,
            transformation_config=transformation.transformation_config,
            description=transformation.description,
            created_at=transformation.created_at
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error adding entity transformation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding entity transformation: {str(e)}"
        )