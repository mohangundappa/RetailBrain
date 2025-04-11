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
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
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
    
    # Relationships
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete"
    )


class Message(Base):
    """Message model to store individual chat messages."""
    __tablename__ = "messages"
    
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=False
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