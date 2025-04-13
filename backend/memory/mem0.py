"""
mem0: Redis-backed memory system for Staples Brain agents.

This module implements a high-performance memory system using Redis as the primary
storage backend, with optional PostgreSQL for long-term archival storage.

Key features:
- Multi-level memory (working, short-term, long-term)
- Semantic search capabilities
- Memory importance and decay
- Efficient indexing and retrieval
"""

import json
import time
import uuid
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta

import redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from backend.memory.schema import MemoryEntryModel, MemoryIndexModel, MemoryContextModel
from backend.memory.config import MemoryConfig
from backend.memory.utils import serialize_datetime, deserialize_datetime, safe_json_dumps, safe_json_loads
from backend.database.db import get_sanitized_db_url

logger = logging.getLogger(__name__)

class MemoryType(str, Enum):
    """Types of memory entries in the mem0 system."""
    MESSAGE = "message"           # Conversation messages
    FACT = "fact"                 # Extracted facts
    ENTITY = "entity"             # Recognized entities
    CONTEXT = "context"           # Context information
    SUMMARY = "summary"           # Conversation summaries
    INSTRUCTION = "instruction"   # System instructions


class MemoryScope(str, Enum):
    """Scope of memory storage."""
    WORKING = "working"           # Very short-term, active processing
    SHORT_TERM = "short_term"     # Recent conversation context
    LONG_TERM = "long_term"       # Persistent knowledge


class MemoryEntry:
    """
    Represents a single memory entry in the mem0 system.
    
    This class is used for both creating new memories and
    representing retrieved memories.
    """
    
    def __init__(
        self,
        content: str,
        memory_type: Union[MemoryType, str],
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        role: Optional[str] = None,
        importance: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        entry_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        embedding: Optional[List[float]] = None,
    ):
        """
        Initialize a memory entry.
        
        Args:
            content: The main content of the memory
            memory_type: Type of memory (message, fact, entity, etc.)
            session_id: Session identifier
            conversation_id: Conversation identifier
            agent_id: Agent that created or owns this memory
            role: For message types, the role (user, assistant, system)
            importance: Importance factor (higher = more important)
            metadata: Additional metadata for the memory
            entry_id: Unique identifier (generated if not provided)
            created_at: Creation timestamp (current time if not provided)
            expires_at: Expiration timestamp (None = never expires)
            embedding: Vector embedding for semantic search
        """
        self.entry_id = entry_id or str(uuid.uuid4())
        self.content = content
        self.memory_type = memory_type if isinstance(memory_type, str) else memory_type.value
        self.session_id = session_id
        self.conversation_id = conversation_id
        self.agent_id = agent_id
        self.role = role
        self.importance = importance
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.utcnow()
        self.expires_at = expires_at
        self.embedding = embedding
        
        # Dynamic attributes
        self.indexes: List[Dict[str, Any]] = []
        self.contexts: List[Dict[str, Any]] = []
        
    def add_index(self, index_type: str, key: str, value: Optional[str] = None) -> None:
        """
        Add an index for efficient retrieval of this memory.
        
        Args:
            index_type: Type of index (entity, tag, keyword, etc.)
            key: The index key
            value: Optional value for the index
        """
        self.indexes.append({
            "index_type": index_type,
            "key": key,
            "value": value
        })
        
    def add_context(self, context_type: str, data: Dict[str, Any]) -> None:
        """
        Add contextual information to this memory.
        
        Args:
            context_type: Type of context (source, relation, etc.)
            data: Context data
        """
        self.contexts.append({
            "context_type": context_type,
            "data": data
        })
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert memory entry to a dictionary for storage.
        
        Returns:
            Dictionary representation of the memory entry
        """
        return {
            "entry_id": self.entry_id,
            "content": self.content,
            "memory_type": self.memory_type,
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "importance": self.importance,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "embedding": self.embedding,
            "indexes": self.indexes,
            "contexts": self.contexts
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """
        Create a memory entry from a dictionary.
        
        Args:
            data: Dictionary containing memory entry data
            
        Returns:
            MemoryEntry instance
        """
        # Handle datetime strings
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
            
        expires_at = data.get('expires_at')
        if isinstance(expires_at, str) and expires_at:
            expires_at = datetime.fromisoformat(expires_at)
        
        # Create the memory entry
        memory = cls(
            content=data.get('content', ''),
            memory_type=data.get('memory_type', MemoryType.FACT),
            session_id=data.get('session_id'),
            conversation_id=data.get('conversation_id'),
            agent_id=data.get('agent_id'),
            role=data.get('role'),
            importance=data.get('importance', 1.0),
            metadata=data.get('metadata', {}),
            entry_id=data.get('entry_id'),
            created_at=created_at,
            expires_at=expires_at,
            embedding=data.get('embedding'),
        )
        
        # Add indexes and contexts
        for idx in data.get('indexes', []):
            memory.add_index(
                index_type=idx.get('index_type', ''),
                key=idx.get('key', ''),
                value=idx.get('value')
            )
            
        for ctx in data.get('contexts', []):
            memory.add_context(
                context_type=ctx.get('context_type', ''),
                data=ctx.get('data', {})
            )
            
        return memory
    
    @classmethod
    def from_database_model(cls, model: MemoryEntryModel) -> 'MemoryEntry':
        """
        Create a memory entry from a database model.
        
        Args:
            model: SQLAlchemy model instance
            
        Returns:
            MemoryEntry instance
        """
        memory = cls(
            content=model.content,
            memory_type=model.memory_type,
            session_id=model.session_id,
            conversation_id=model.conversation_id,
            agent_id=model.agent_id,
            role=model.role,
            importance=model.importance,
            metadata=model.metadata,
            entry_id=str(model.id),
            created_at=model.created_at,
            expires_at=model.expires_at,
            embedding=model.embedding,
        )
        
        # Add indexes and contexts
        for idx in model.indexes:
            memory.add_index(
                index_type=idx.index_type,
                key=idx.key,
                value=idx.value
            )
            
        for ctx in model.contexts:
            memory.add_context(
                context_type=ctx.context_type,
                data=ctx.data
            )
            
        return memory


class Mem0:
    """
    Central implementation of the mem0 memory system.
    
    This class provides the core functionality for storing and retrieving
    memories using Redis as the primary storage backend, with optional
    PostgreSQL for long-term archival.
    """
    
    def __init__(self, config: Optional[Config] = None, db_session: Optional[AsyncSession] = None):
        """
        Initialize the mem0 memory system.
        
        Args:
            config: Application configuration
            db_session: Database session for long-term storage
        """
        self.config = config or Config()
        self.db_session = db_session
        
        # Initialize Redis connection
        redis_url = self.config.get("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        
        # Memory expiration defaults (in seconds)
        self.default_expiration = {
            MemoryScope.WORKING: 300,       # 5 minutes
            MemoryScope.SHORT_TERM: 3600,   # 1 hour
            MemoryScope.LONG_TERM: None     # Never expires
        }
        
        logger.info(f"Initialized mem0 memory system with Redis backend: {redis_url}")
        
        # Test Redis connection
        try:
            self.redis.ping()
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            
    def _get_key(self, memory_type: str, scope: str, identifier: str) -> str:
        """
        Generate a Redis key for a memory entry.
        
        Args:
            memory_type: Type of memory (message, fact, etc.)
            scope: Memory scope (working, short_term, long_term)
            identifier: Unique identifier or grouping
            
        Returns:
            Redis key string
        """
        return f"mem0:{scope}:{memory_type}:{identifier}"
    
    def _get_index_key(self, index_type: str, key: str, value: Optional[str] = None) -> str:
        """
        Generate a Redis key for a memory index.
        
        Args:
            index_type: Type of index (entity, tag, etc.)
            key: Index key
            value: Optional index value
            
        Returns:
            Redis key string
        """
        if value:
            return f"mem0:index:{index_type}:{key}:{value}"
        return f"mem0:index:{index_type}:{key}"
    
    def add_memory(
        self,
        memory: MemoryEntry,
        scope: Union[MemoryScope, str] = MemoryScope.SHORT_TERM,
        ttl: Optional[int] = None
    ) -> str:
        """
        Add a memory entry to the system.
        
        Args:
            memory: The memory entry to add
            scope: Memory scope (working, short_term, long_term)
            ttl: Time-to-live in seconds (overrides default for scope)
            
        Returns:
            Memory entry ID
        """
        # Get the memory as a dictionary
        memory_dict = memory.to_dict()
        memory_json = json.dumps(memory_dict)
        
        # Use the scope string if a MemoryScope enum was provided
        scope_str = scope.value if isinstance(scope, MemoryScope) else scope
        
        # Get TTL based on scope if not explicitly provided
        if ttl is None and scope_str in self.default_expiration:
            ttl = self.default_expiration[scope_str]
        
        # Generate the main memory key
        session_id = memory.session_id or "global"
        conversation_id = memory.conversation_id or session_id
        primary_key = self._get_key(memory.memory_type, scope_str, memory.entry_id)
        
        # Store the memory in Redis
        pipeline = self.redis.pipeline()
        
        # Store the main memory entry
        pipeline.set(primary_key, memory_json)
        if ttl:
            pipeline.expire(primary_key, ttl)
            
        # Add to session list if applicable
        if memory.session_id:
            session_key = f"mem0:sessions:{memory.session_id}"
            pipeline.sadd(session_key, memory.entry_id)
            if ttl:
                pipeline.expire(session_key, ttl)
                
        # Add to conversation list if applicable
        if memory.conversation_id:
            conv_key = f"mem0:conversations:{memory.conversation_id}"
            pipeline.sadd(conv_key, memory.entry_id)
            if ttl:
                pipeline.expire(conv_key, ttl)
                
        # Add to agent list if applicable
        if memory.agent_id:
            agent_key = f"mem0:agents:{memory.agent_id}"
            pipeline.sadd(agent_key, memory.entry_id)
                
        # Add to memory type list
        type_key = f"mem0:types:{memory.memory_type}"
        pipeline.sadd(type_key, memory.entry_id)
        
        # Add to chronological list for this conversation
        if memory.conversation_id:
            # Use a sorted set with timestamp as score for chronological access
            chrono_key = f"mem0:chronological:{memory.conversation_id}"
            timestamp = time.mktime(memory.created_at.timetuple())
            pipeline.zadd(chrono_key, {memory.entry_id: timestamp})
            if ttl:
                pipeline.expire(chrono_key, ttl)
        
        # Add indexes for efficient retrieval
        for idx in memory.indexes:
            index_key = self._get_index_key(idx['index_type'], idx['key'], idx['value'])
            pipeline.sadd(index_key, memory.entry_id)
            if ttl:
                pipeline.expire(index_key, ttl)
        
        # Execute all Redis commands
        pipeline.execute()
        
        # If this is long-term memory and we have a database session, store in PostgreSQL too
        if scope_str == MemoryScope.LONG_TERM.value and self.db_session:
            self._store_in_database(memory)
            
        logger.debug(f"Added memory {memory.entry_id} to {scope_str} memory")
        return memory.entry_id
    
    async def _store_in_database(self, memory: MemoryEntry) -> None:
        """
        Store a memory entry in the PostgreSQL database for long-term storage.
        This is an async operation that should be awaited.
        
        Args:
            memory: The memory entry to store
        """
        if not self.db_session:
            logger.warning("Database session not available for long-term storage")
            return
            
        try:
            # Create the memory entry model
            entry = MemoryEntryModel(
                id=uuid.UUID(memory.entry_id) if isinstance(memory.entry_id, str) else memory.entry_id,
                session_id=memory.session_id,
                conversation_id=memory.conversation_id,
                agent_id=memory.agent_id,
                memory_type=memory.memory_type,
                role=memory.role,
                content=memory.content,
                importance=memory.importance,
                relevance=1.0,  # Default
                recency=1.0,    # Default
                embedding=memory.embedding,
                metadata=memory.metadata,
                created_at=memory.created_at,
                expires_at=memory.expires_at
            )
            
            # Add indexes
            for idx in memory.indexes:
                index = MemoryIndexModel(
                    entry_id=entry.id,
                    index_type=idx['index_type'],
                    key=idx['key'],
                    value=idx['value']
                )
                entry.indexes.append(index)
                
            # Add contexts
            for ctx in memory.contexts:
                context = MemoryContextModel(
                    entry_id=entry.id,
                    context_type=ctx['context_type'],
                    data=ctx['data']
                )
                entry.contexts.append(context)
                
            # Add to database
            self.db_session.add(entry)
            await self.db_session.commit()
            logger.debug(f"Stored memory {memory.entry_id} in database")
            
        except Exception as e:
            logger.error(f"Error storing memory in database: {str(e)}")
            await self.db_session.rollback()
    
    def get_memory(self, memory_id: str, include_expired: bool = False) -> Optional[MemoryEntry]:
        """
        Retrieve a specific memory entry by ID.
        
        Args:
            memory_id: The memory entry ID
            include_expired: Whether to include expired memories
            
        Returns:
            MemoryEntry if found, None otherwise
        """
        # Try to find in any scope
        for scope in [MemoryScope.WORKING, MemoryScope.SHORT_TERM, MemoryScope.LONG_TERM]:
            # We don't know the memory type, so we need to check possible types
            for memory_type in MemoryType:
                key = self._get_key(memory_type.value, scope.value, memory_id)
                memory_json = self.redis.get(key)
                
                if memory_json:
                    try:
                        memory_dict = json.loads(memory_json)
                        memory = MemoryEntry.from_dict(memory_dict)
                        
                        # Check if memory is expired
                        if not include_expired and memory.expires_at:
                            if memory.expires_at < datetime.utcnow():
                                continue
                                
                        return memory
                    except Exception as e:
                        logger.error(f"Error parsing memory {memory_id}: {str(e)}")
            
        # If not found in Redis and we have a database session, try the database
        if self.db_session:
            return self._get_from_database(memory_id)
            
        return None
    
    async def _get_from_database(self, memory_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve a memory entry from the PostgreSQL database.
        This is an async operation that should be awaited.
        
        Args:
            memory_id: The memory entry ID
            
        Returns:
            MemoryEntry if found, None otherwise
        """
        if not self.db_session:
            return None
            
        try:
            # Query the database
            query = select(MemoryEntryModel).where(
                MemoryEntryModel.id == uuid.UUID(memory_id)
            )
            result = await self.db_session.execute(query)
            model = result.scalars().first()
            
            if model:
                return MemoryEntry.from_database_model(model)
                
        except Exception as e:
            logger.error(f"Error retrieving memory from database: {str(e)}")
            
        return None
    
    def get_memories_by_conversation(
        self,
        conversation_id: str,
        memory_type: Optional[Union[MemoryType, str]] = None,
        limit: int = 100,
        offset: int = 0,
        include_expired: bool = False
    ) -> List[MemoryEntry]:
        """
        Retrieve memories for a specific conversation.
        
        Args:
            conversation_id: The conversation ID
            memory_type: Optional filter for memory type
            limit: Maximum number of memories to retrieve
            offset: Offset for pagination
            include_expired: Whether to include expired memories
            
        Returns:
            List of memory entries
        """
        chrono_key = f"mem0:chronological:{conversation_id}"
        
        # Get memory IDs from the chronological sorted set
        memory_ids = self.redis.zrevrange(chrono_key, offset, offset + limit - 1)
        
        # If no memories found, return empty list
        if not memory_ids:
            return []
            
        # Retrieve each memory
        memories = []
        for memory_id in memory_ids:
            memory = self.get_memory(memory_id, include_expired=include_expired)
            
            if memory:
                # Apply memory type filter if provided
                if memory_type:
                    type_value = memory_type.value if isinstance(memory_type, MemoryType) else memory_type
                    if memory.memory_type != type_value:
                        continue
                
                memories.append(memory)
                
        return memories
    
    def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 50,
        include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation messages in a format suitable for LLM context.
        
        Args:
            conversation_id: The conversation ID
            limit: Maximum number of messages to retrieve
            include_expired: Whether to include expired messages
            
        Returns:
            List of message dictionaries with role and content
        """
        memories = self.get_memories_by_conversation(
            conversation_id=conversation_id,
            memory_type=MemoryType.MESSAGE,
            limit=limit,
            include_expired=include_expired
        )
        
        # Convert to the standard format for LLM context
        messages = []
        for memory in memories:
            if memory.role:
                messages.append({
                    "role": memory.role,
                    "content": memory.content
                })
                
        return messages
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: The conversation ID
            role: Message role (user, assistant, system)
            content: Message content
            session_id: Optional session ID
            agent_id: Optional agent ID
            metadata: Optional message metadata
            
        Returns:
            Memory entry ID
        """
        memory = MemoryEntry(
            content=content,
            memory_type=MemoryType.MESSAGE,
            session_id=session_id,
            conversation_id=conversation_id,
            agent_id=agent_id,
            role=role,
            metadata=metadata or {}
        )
        
        return self.add_memory(memory, scope=MemoryScope.SHORT_TERM)
    
    def add_entity(
        self,
        conversation_id: str,
        entity_type: str,
        entity_value: str,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> str:
        """
        Add an entity to memory.
        
        Args:
            conversation_id: The conversation ID
            entity_type: Type of entity (e.g., 'person', 'tracking_number')
            entity_value: Value of the entity
            confidence: Confidence score for the extraction
            metadata: Optional entity metadata
            session_id: Optional session ID
            agent_id: Optional agent ID
            
        Returns:
            Memory entry ID
        """
        # Create metadata if not provided
        metadata = metadata or {}
        metadata.update({
            "entity_type": entity_type,
            "confidence": confidence
        })
        
        memory = MemoryEntry(
            content=entity_value,
            memory_type=MemoryType.ENTITY,
            session_id=session_id,
            conversation_id=conversation_id,
            agent_id=agent_id,
            metadata=metadata
        )
        
        # Add indexes for easy retrieval
        memory.add_index("entity_type", entity_type, entity_value)
        
        return self.add_memory(memory, scope=MemoryScope.SHORT_TERM)
    
    def search_memories(
        self,
        query: Dict[str, Any],
        limit: int = 10,
        include_expired: bool = False
    ) -> List[MemoryEntry]:
        """
        Search for memories based on various criteria.
        
        Args:
            query: Query parameters (e.g., conversation_id, memory_type, etc.)
            limit: Maximum number of results
            include_expired: Whether to include expired memories
            
        Returns:
            List of matching memory entries
        """
        # Implement memory search logic here
        # This could use Redis search capabilities or fallback to manual filtering
        # For now, using a simplified implementation
        
        results = []
        
        # Check for conversation_id
        if 'conversation_id' in query:
            conv_key = f"mem0:conversations:{query['conversation_id']}"
            memory_ids = self.redis.smembers(conv_key)
            
            for memory_id in memory_ids:
                memory = self.get_memory(memory_id, include_expired=include_expired)
                if not memory:
                    continue
                    
                # Apply additional filters
                match = True
                for key, value in query.items():
                    if key == 'conversation_id':
                        continue  # Already filtered by conversation
                        
                    if key == 'memory_type':
                        if memory.memory_type != value:
                            match = False
                            break
                    elif key == 'agent_id':
                        if memory.agent_id != value:
                            match = False
                            break
                    elif key == 'role':
                        if memory.role != value:
                            match = False
                            break
                    # Add other filters as needed
                
                if match:
                    results.append(memory)
                    if len(results) >= limit:
                        break
                        
        # Return the results
        return results[:limit]
    
    def clear_working_memory(self) -> int:
        """
        Clear all working memory.
        
        Returns:
            Number of memories cleared
        """
        # Find all working memory keys
        pattern = f"mem0:{MemoryScope.WORKING.value}:*"
        keys = self.redis.keys(pattern)
        
        if keys:
            return self.redis.delete(*keys)
            
        return 0
    
    def clear_conversation_memory(self, conversation_id: str) -> int:
        """
        Clear all memory for a specific conversation.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            Number of memories cleared
        """
        # Get all memory IDs for this conversation
        conv_key = f"mem0:conversations:{conversation_id}"
        memory_ids = self.redis.smembers(conv_key)
        
        if not memory_ids:
            return 0
            
        # Delete each memory and its associated indexes
        pipeline = self.redis.pipeline()
        
        # Delete the conversation set itself
        pipeline.delete(conv_key)
        
        # Delete the chronological record
        chrono_key = f"mem0:chronological:{conversation_id}"
        pipeline.delete(chrono_key)
        
        # Delete individual memories
        count = 0
        for memory_id in memory_ids:
            # We don't know the memory type or scope, so find and delete all occurrences
            for scope in [MemoryScope.WORKING, MemoryScope.SHORT_TERM, MemoryScope.LONG_TERM]:
                for memory_type in MemoryType:
                    key = self._get_key(memory_type.value, scope.value, memory_id)
                    pipeline.delete(key)
            count += 1
            
        # Execute the pipeline
        pipeline.execute()
        
        return count