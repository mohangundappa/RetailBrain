"""
Database models for Staples Brain.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

from backend.database.db import Base


class Conversation(Base):
    """Conversation model to store chat sessions."""
    __tablename__ = "conversations"
    
    id: Mapped[int] = mapped_column(
        sa.Integer, primary_key=True, autoincrement=True
    )
    session_id: Mapped[str] = mapped_column(sa.String(50), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # Additional columns from existing schema
    confidence: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    intent: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    selected_agent: Mapped[Optional[str]] = mapped_column(sa.String, nullable=True)
    user_input: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    brain_response: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    
    # Relationships
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete"
    )


class Message(Base):
    """Message model to store individual chat messages."""
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(
        sa.Integer, primary_key=True, autoincrement=True
    )
    conversation_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(sa.String(20), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(sa.Text, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    conversation: Mapped[Conversation] = relationship(
        "Conversation", back_populates="messages"
    )


class TelemetrySession(Base):
    """Telemetry session model to store system telemetry data."""
    __tablename__ = "telemetry_sessions"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[str] = mapped_column(sa.String(50), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # Relationships
    events: Mapped[List["TelemetryEvent"]] = relationship(
        "TelemetryEvent", back_populates="session", cascade="all, delete"
    )


class TelemetryEvent(Base):
    """Telemetry event model to store individual telemetry events."""
    __tablename__ = "telemetry_events"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("telemetry_sessions.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    # Relationships
    session: Mapped[TelemetrySession] = relationship(
        "TelemetrySession", back_populates="events"
    )


class CustomAgent(Base):
    """Custom agent model to store user-created agents."""
    __tablename__ = "custom_agents"
    
    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    creator: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    configuration: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    wizard_completed: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    
    # Relationships
    components: Mapped[List["AgentComponent"]] = relationship(
        "AgentComponent", back_populates="agent", cascade="all, delete"
    )
    connections: Mapped[List["ComponentConnection"]] = relationship(
        "ComponentConnection", back_populates="agent", cascade="all, delete"
    )


class AgentComponent(Base):
    """Agent component model to store components of custom agents."""
    __tablename__ = "agent_components"
    
    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("custom_agents.id"), nullable=False
    )
    component_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    position_x: Mapped[float] = mapped_column(sa.Float, nullable=False)
    position_y: Mapped[float] = mapped_column(sa.Float, nullable=False)
    configuration: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    agent: Mapped[CustomAgent] = relationship(
        "CustomAgent", back_populates="components"
    )
    source_connections: Mapped[List["ComponentConnection"]] = relationship(
        "ComponentConnection", 
        foreign_keys="ComponentConnection.source_id", 
        back_populates="source",
        cascade="all, delete"
    )
    target_connections: Mapped[List["ComponentConnection"]] = relationship(
        "ComponentConnection", 
        foreign_keys="ComponentConnection.target_id", 
        back_populates="target",
        cascade="all, delete"
    )


class ComponentConnection(Base):
    """Component connection model to store connections between agent components."""
    __tablename__ = "component_connections"
    
    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("custom_agents.id"), nullable=False
    )
    source_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("agent_components.id"), nullable=False
    )
    target_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("agent_components.id"), nullable=False
    )
    connection_type: Mapped[str] = mapped_column(sa.String(50), default="default", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    
    # Relationships
    agent: Mapped[CustomAgent] = relationship(
        "CustomAgent", back_populates="connections"
    )
    source: Mapped[AgentComponent] = relationship(
        "AgentComponent", foreign_keys=[source_id], back_populates="source_connections"
    )
    target: Mapped[AgentComponent] = relationship(
        "AgentComponent", foreign_keys=[target_id], back_populates="target_connections"
    )


class ComponentTemplate(Base):
    """Component template model to store reusable component templates."""
    __tablename__ = "component_templates"
    
    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False, unique=True)
    component_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    configuration_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    default_configuration: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
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


class AgentTemplate(Base):
    """Agent template model to store reusable agent templates."""
    __tablename__ = "agent_templates"
    
    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    configuration: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, 
        server_default=func.now(), 
        onupdate=func.now(),
        nullable=False
    )