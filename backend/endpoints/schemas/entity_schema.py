"""
API schemas for entity-related operations.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from pydantic import BaseModel, Field, constr


class EntityBase(BaseModel):
    """Base model for entity data."""
    name: constr(min_length=1, max_length=100) = Field(..., description="Entity name (code identifier)")
    display_name: constr(min_length=1, max_length=255) = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Entity description")
    entity_type: constr(min_length=1, max_length=50) = Field(..., description="Entity type (basic, composite, enum, regex)")
    validation_regex: Optional[str] = Field(None, description="Regex for validation")
    is_required: bool = Field(False, description="Whether this entity is required")
    default_value: Optional[str] = Field(None, description="Default value")


class EntityCreate(EntityBase):
    """Model for creating a new entity."""
    pass


class EntityResponse(EntityBase):
    """Model for returning entity data."""
    id: uuid.UUID = Field(..., description="Entity ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class EntityEnumValueCreate(BaseModel):
    """Model for creating a new enum value."""
    value: constr(min_length=1, max_length=255) = Field(..., description="The actual value")
    display_text: constr(min_length=1, max_length=255) = Field(..., description="Display text for the value")
    is_default: bool = Field(False, description="Whether this is the default value")


class EntityEnumValueResponse(EntityEnumValueCreate):
    """Model for returning enum value data."""
    id: uuid.UUID = Field(..., description="Enum value ID")
    entity_id: uuid.UUID = Field(..., description="Entity ID")
    
    class Config:
        from_attributes = True


class EntityPatternCreate(BaseModel):
    """Model for creating a new entity extraction pattern."""
    pattern_type: constr(min_length=1, max_length=50) = Field(..., description="Pattern type (regex, example, prompt)")
    pattern_value: str = Field(..., description="The pattern value")
    confidence_value: float = Field(0.8, description="Confidence score (0.0-1.0)")
    description: Optional[str] = Field(None, description="Pattern description")


class EntityPatternResponse(EntityPatternCreate):
    """Model for returning entity pattern data."""
    id: uuid.UUID = Field(..., description="Pattern ID")
    entity_id: uuid.UUID = Field(..., description="Entity ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class EntityMappingCreate(BaseModel):
    """Model for mapping an entity to an agent."""
    entity_id: uuid.UUID = Field(..., description="Entity ID")
    is_required: bool = Field(False, description="Whether this entity is required for the agent")
    extraction_priority: int = Field(0, description="Priority order for extraction")
    prompt_for_missing: bool = Field(True, description="Whether to prompt user if entity is missing")
    prompt_text: Optional[str] = Field(None, description="Text to use when prompting")
    extraction_method: str = Field("llm", description="Method to use for extraction (llm, regex, etc.)")
    extraction_config: Optional[Dict[str, Any]] = Field(None, description="Configuration for extraction")


class EntityMappingResponse(EntityMappingCreate):
    """Model for returning entity mapping data."""
    id: uuid.UUID = Field(..., description="Mapping ID")
    agent_id: uuid.UUID = Field(..., description="Agent ID")
    entity: EntityResponse = Field(..., description="Entity definition")
    
    class Config:
        from_attributes = True


class EntityTransformationCreate(BaseModel):
    """Model for creating a new entity transformation."""
    transformation_type: constr(min_length=1, max_length=50) = Field(..., description="Type of transformation (normalize, format, validate)")
    transformation_order: int = Field(..., description="Order of application (lower numbers are applied first)")
    transformation_config: Dict[str, Any] = Field(..., description="Configuration for the transformation")
    description: Optional[str] = Field(None, description="Description of the transformation")


class EntityTransformationResponse(EntityTransformationCreate):
    """Model for returning entity transformation data."""
    id: uuid.UUID = Field(..., description="Transformation ID")
    entity_id: uuid.UUID = Field(..., description="Entity ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    class Config:
        from_attributes = True


class EntityDetailResponse(EntityResponse):
    """Detailed entity information including related data."""
    enum_values: List[EntityEnumValueResponse] = Field([], description="Enum values")
    extraction_patterns: List[EntityPatternResponse] = Field([], description="Extraction patterns")
    transformations: List[EntityTransformationResponse] = Field([], description="Transformations")
    
    class Config:
        from_attributes = True