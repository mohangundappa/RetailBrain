"""
Database schema for the mem0 memory system.

This module defines the SQLAlchemy models for mem0 memory storage,
including memory entries, indexes, and contextual information.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

# Import the base model from your project's database module
from backend.database.db import Base

class MemoryEntryModel(Base):
    """
    Primary storage for memory entries in the mem0 system.
    
    Each entry represents a single piece of information stored in memory,
    such as a message, fact, or context detail.
    """
    __tablename__ = "memory_entry"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(64), nullable=False, index=True)
    conversation_id = Column(String(64), nullable=False, index=True)
    agent_id = Column(String(64), nullable=True, index=True)
    
    # Memory content
    memory_type = Column(String(32), nullable=False, index=True)  # 'message', 'fact', 'entity', etc.
    role = Column(String(32), nullable=True)  # For message types: 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    
    # Memory metadata
    importance = Column(Float, default=1.0)  # Higher values = more important
    relevance = Column(Float, default=1.0)  # Relevance to current context
    recency = Column(Float, default=1.0)  # Recency factor
    embedding = Column(ARRAY(Float), nullable=True)  # Vector embedding for semantic search
    metadata = Column(JSONB, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    
    # Relationships
    indexes = relationship("MemoryIndexModel", back_populates="entry", cascade="all, delete-orphan")
    contexts = relationship("MemoryContextModel", back_populates="entry", cascade="all, delete-orphan")


class MemoryIndexModel(Base):
    """
    Indexes for efficient memory retrieval.
    
    These entries allow for fast lookup of memory by various criteria
    beyond basic field indexing.
    """
    __tablename__ = "memory_index"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("memory_entry.id", ondelete="CASCADE"), nullable=False)
    
    # Index type and key-value pair
    index_type = Column(String(32), nullable=False, index=True)  # 'entity', 'tag', 'keyword', etc.
    key = Column(String(128), nullable=False, index=True)
    value = Column(String(255), nullable=True, index=True)
    
    # Relationship
    entry = relationship("MemoryEntryModel", back_populates="indexes")
    
    # Composite index on (index_type, key, value) for fast lookups
    __table_args__ = (
        # Intentionally omitted for now, will be added if needed
    )


class MemoryContextModel(Base):
    """
    Context information associated with memory entries.
    
    Provides additional structured context for memory entries,
    such as entity relationships, attributions, or source information.
    """
    __tablename__ = "memory_context"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("memory_entry.id", ondelete="CASCADE"), nullable=False)
    
    # Context type and data
    context_type = Column(String(32), nullable=False, index=True)  # 'source', 'relation', 'attribution', etc.
    data = Column(JSONB, nullable=False)
    
    # Relationship
    entry = relationship("MemoryEntryModel", back_populates="contexts")