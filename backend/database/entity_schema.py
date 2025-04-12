"""
Database models for Entity Extraction Schema.
This module defines the SQLAlchemy models for entity extraction configurations.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from backend.database.db import Base


class EntityDefinition(Base):
    """
    Definition of extractable entities.
    """
    __tablename__ = "entity_definitions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    entity_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    validation_regex: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    default_value: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    
    # Unique constraint
    __table_args__ = (
        sa.UniqueConstraint("name"),
    )
    
    # Relationships
    enum_values: Mapped[List["EntityEnumValue"]] = relationship(
        "EntityEnumValue", back_populates="entity", cascade="all, delete"
    )
    extraction_patterns: Mapped[List["EntityExtractionPattern"]] = relationship(
        "EntityExtractionPattern", back_populates="entity", cascade="all, delete"
    )
    transformations: Mapped[List["EntityTransformation"]] = relationship(
        "EntityTransformation", back_populates="entity", cascade="all, delete"
    )
    agent_mappings: Mapped[List["AgentEntityMapping"]] = relationship(
        "AgentEntityMapping", back_populates="entity", cascade="all, delete"
    )


class EntityEnumValue(Base):
    """
    Possible values for enum-type entities.
    """
    __tablename__ = "entity_enum_values"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("entity_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    value: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    display_text: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    is_default: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    
    # Unique constraint
    __table_args__ = (
        sa.UniqueConstraint("entity_id", "value"),
    )
    
    # Relationship
    entity: Mapped["EntityDefinition"] = relationship(
        "EntityDefinition", back_populates="enum_values"
    )


class AgentEntityMapping(Base):
    """
    Maps entities to agents with extraction configuration.
    """
    __tablename__ = "agent_entity_mappings"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("entity_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    is_required: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    extraction_priority: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    prompt_for_missing: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    prompt_text: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    extraction_method: Mapped[str] = mapped_column(sa.String(50), default="llm", nullable=False)
    extraction_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Unique constraint
    __table_args__ = (
        sa.UniqueConstraint("agent_id", "entity_id"),
    )
    
    # Relationships - Use string reference to avoid circular imports
    agent: Mapped["backend.database.agent_schema.AgentDefinition"] = relationship(
        "backend.database.agent_schema.AgentDefinition", back_populates="entity_mappings"
    )
    entity: Mapped["EntityDefinition"] = relationship(
        "EntityDefinition", back_populates="agent_mappings"
    )


class EntityExtractionPattern(Base):
    """
    Patterns used for entity extraction.
    """
    __tablename__ = "entity_extraction_patterns"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("entity_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    pattern_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    pattern_value: Mapped[str] = mapped_column(sa.Text, nullable=False)
    confidence_value: Mapped[float] = mapped_column(sa.Float, default=0.8, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    
    # Unique constraint
    __table_args__ = (
        sa.UniqueConstraint("entity_id", "pattern_value", "pattern_type"),
    )
    
    # Relationship
    entity: Mapped["EntityDefinition"] = relationship(
        "EntityDefinition", back_populates="extraction_patterns"
    )


class EntityTransformation(Base):
    """
    Transformations to apply to extracted entities.
    """
    __tablename__ = "entity_transformations"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("entity_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    transformation_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    transformation_order: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    transformation_config: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    
    # Relationship
    entity: Mapped["EntityDefinition"] = relationship(
        "EntityDefinition", back_populates="transformations"
    )


# Don't import here to avoid circular imports
# The relationship to AgentDefinition is defined using string references