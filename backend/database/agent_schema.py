"""
Database models for the Agent Configuration Schema.
This module defines the SQLAlchemy models for storing agent configurations in the database.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from pgvector.sqlalchemy import Vector

from backend.database.db import Base


class AgentDefinition(Base):
    """
    Core model for agent definitions.
    Stores the basic metadata for an agent, with type-specific configuration in related tables.
    """
    __tablename__ = "agent_definitions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    agent_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(50), default="draft", nullable=False
    )
    is_system: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    created_by: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    
    # Relationships
    deployments: Mapped[List["AgentDeployment"]] = relationship(
        "AgentDeployment", back_populates="agent_definition", cascade="all, delete"
    )
    patterns: Mapped[List["AgentPattern"]] = relationship(
        "AgentPattern", back_populates="agent", cascade="all, delete"
    )
    tools: Mapped[List["AgentTool"]] = relationship(
        "AgentTool", back_populates="agent", cascade="all, delete"
    )
    response_templates: Mapped[List["AgentResponseTemplate"]] = relationship(
        "AgentResponseTemplate", back_populates="agent", cascade="all, delete"
    )
    # Use string reference for entity mappings to avoid circular imports
    entity_mappings: Mapped[List["backend.database.entity_schema.AgentEntityMapping"]] = relationship(
        "backend.database.entity_schema.AgentEntityMapping", 
        back_populates="agent", 
        cascade="all, delete"
    )
    # Type-specific configurations are accessed through separate properties
    
    # Parent-child relationships
    child_relationships: Mapped[List["AgentComposition"]] = relationship(
        "AgentComposition", 
        foreign_keys="AgentComposition.parent_agent_id",
        back_populates="parent_agent",
        cascade="all, delete"
    )
    parent_relationships: Mapped[List["AgentComposition"]] = relationship(
        "AgentComposition", 
        foreign_keys="AgentComposition.child_agent_id",
        back_populates="child_agent",
        cascade="all, delete"
    )


class AgentDeployment(Base):
    """
    Agent deployment information.
    Tracks when and where an agent is deployed.
    """
    __tablename__ = "agent_deployments"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    environment: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    deployed_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    deployed_by: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    deployment_notes: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    
    # Relationship
    agent_definition: Mapped["AgentDefinition"] = relationship(
        "AgentDefinition", back_populates="deployments"
    )


class AgentComposition(Base):
    """
    Agent composition model.
    Defines parent-child relationships between agents.
    """
    __tablename__ = "agent_compositions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    parent_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    child_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    execution_order: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    configuration: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Add unique constraint
    __table_args__ = (
        sa.UniqueConstraint("parent_agent_id", "child_agent_id"),
    )
    
    # Relationships
    parent_agent: Mapped["AgentDefinition"] = relationship(
        "AgentDefinition", foreign_keys=[parent_agent_id], back_populates="child_relationships"
    )
    child_agent: Mapped["AgentDefinition"] = relationship(
        "AgentDefinition", foreign_keys=[child_agent_id], back_populates="parent_relationships"
    )


# Type-specific configuration tables

class LlmAgentConfiguration(Base):
    """
    Configuration for LLM-based agents.
    """
    __tablename__ = "llm_agent_configurations"
    
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        primary_key=True
    )
    model_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    temperature: Mapped[float] = mapped_column(sa.Float, default=0.7, nullable=False)
    max_tokens: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(sa.Integer, default=30, nullable=False)
    confidence_threshold: Mapped[float] = mapped_column(sa.Float, default=0.7, nullable=False)
    system_prompt: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    few_shot_examples: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    output_parser: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    
    # Relationship - use backref to ensure the relationship isn't duplicated
    agent: Mapped["AgentDefinition"] = relationship(
        "AgentDefinition", backref="llm_configuration"
    )


class RuleAgentConfiguration(Base):
    """
    Configuration for rule-based agents.
    """
    __tablename__ = "rule_agent_configurations"
    
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        primary_key=True
    )
    rules: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    default_confidence: Mapped[float] = mapped_column(sa.Float, default=0.5, nullable=False)
    fallback_message: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    
    # Relationship - use backref to ensure the relationship isn't duplicated
    agent: Mapped["AgentDefinition"] = relationship(
        "AgentDefinition", backref="rule_configuration"
    )


class RetrievalAgentConfiguration(Base):
    """
    Configuration for retrieval-based agents.
    """
    __tablename__ = "retrieval_agent_configurations"
    
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        primary_key=True
    )
    vector_store_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    search_type: Mapped[str] = mapped_column(sa.String(50), default="similarity", nullable=False)
    top_k: Mapped[int] = mapped_column(sa.Integer, default=3, nullable=False)
    similarity_threshold: Mapped[float] = mapped_column(sa.Float, default=0.7, nullable=False)
    reranker_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Relationship - use backref to ensure the relationship isn't duplicated
    agent: Mapped["AgentDefinition"] = relationship(
        "AgentDefinition", backref="retrieval_configuration"
    )


# Pattern recognition tables

class AgentPattern(Base):
    """
    Pattern recognition configuration for agents.
    Stores patterns that help identify when an agent should be used.
    """
    __tablename__ = "agent_patterns"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    pattern_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    pattern_value: Mapped[str] = mapped_column(sa.Text, nullable=False)
    priority: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    confidence_boost: Mapped[float] = mapped_column(sa.Float, default=0.1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    
    # Relationships
    agent: Mapped["AgentDefinition"] = relationship(
        "AgentDefinition", back_populates="patterns"
    )
    embedding: Mapped[Optional["AgentPatternEmbedding"]] = relationship(
        "AgentPatternEmbedding", back_populates="pattern", 
        uselist=False, cascade="all, delete"
    )


class AgentPatternEmbedding(Base):
    """
    Vector embeddings for semantic patterns.
    """
    __tablename__ = "agent_pattern_embeddings"
    
    pattern_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("agent_patterns.id", ondelete="CASCADE"),
        primary_key=True
    )
    embedding_vector = mapped_column(Vector(1536))  # Using pgvector for embeddings
    embedding_model: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    
    # Relationship
    pattern: Mapped["AgentPattern"] = relationship(
        "AgentPattern", back_populates="embedding"
    )


# Tool configuration tables

class AgentTool(Base):
    """
    Tools available to agents.
    """
    __tablename__ = "agent_tools"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    tool_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    tool_description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    tool_class_path: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    requires_confirmation: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    
    # Relationship
    agent: Mapped["AgentDefinition"] = relationship(
        "AgentDefinition", back_populates="tools"
    )


# Response template tables

class AgentResponseTemplate(Base):
    """
    Templates for agent responses.
    """
    __tablename__ = "agent_response_templates"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        sa.ForeignKey("agent_definitions.id", ondelete="CASCADE"),
        nullable=False
    )
    template_key: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    template_content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    template_type: Mapped[str] = mapped_column(sa.String(50), default="text", nullable=False)
    scenario: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    language: Mapped[str] = mapped_column(sa.String(10), default="en", nullable=False)
    tone: Mapped[str] = mapped_column(sa.String(50), default="neutral", nullable=False)
    is_fallback: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(sa.Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationship
    agent: Mapped["AgentDefinition"] = relationship(
        "AgentDefinition", back_populates="response_templates"
    )
    
    # Unique constraint for key, language, and version
    __table_args__ = (
        sa.UniqueConstraint("agent_id", "template_key", "language", "version"),
    )