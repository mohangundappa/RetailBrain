"""
Database models for Staples Brain.
Defines SQLAlchemy models with PgVector support for vector embeddings.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from database.db import Base

class Conversation(Base):
    """
    Conversation model for storing chat history with vector embeddings.
    """
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    user_input = Column(Text, nullable=False)
    brain_response = Column(Text, nullable=False)
    intent = Column(String(255))
    confidence = Column(Float)
    selected_agent = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Vector embeddings for semantic search (1536 is OpenAI embedding dimension)
    embedding = Column(Vector(1536), nullable=True)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation")
    telemetry_events = relationship("TelemetryEvent", back_populates="conversation")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, session_id={self.session_id})>"

class Message(Base):
    """
    Message model for storing individual messages in a conversation.
    """
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String(50), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional metadata
    tokens = Column(Integer, nullable=True)
    processing_time = Column(Float, nullable=True)
    metadata = Column(JSONB, nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role})>"

class AgentConfig(Base):
    """
    Agent configuration model for storing agent settings.
    """
    __tablename__ = "agent_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    icon = Column(String(255), nullable=True)
    prompt_template = Column(Text, nullable=False)
    response_format = Column(Text)
    entity_definitions = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<AgentConfig(id={self.id}, name={self.name})>"

class TelemetryEvent(Base):
    """
    Telemetry event model for tracking system events.
    """
    __tablename__ = "telemetry_events"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    event_type = Column(String(255), nullable=False, index=True)
    event_data = Column(JSONB, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="telemetry_events")
    
    def __repr__(self):
        return f"<TelemetryEvent(id={self.id}, event_type={self.event_type})>"

class AgentSelectionEvent(Base):
    """
    Agent selection event model for tracking agent selection decisions.
    """
    __tablename__ = "agent_selection_events"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    user_input = Column(Text, nullable=False)
    selected_agent = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False)
    agent_scores = Column(JSONB)  # Scores for all agents
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<AgentSelectionEvent(id={self.id}, selected_agent={self.selected_agent})>"