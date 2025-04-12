"""
Conversation memory management for Staples Brain.

This module provides memory storage and retrieval functions for conversation
state, working memory, and conversation history.
"""

import json
import logging
import time
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

from backend.config.agent_constants import MEMORY_EXPIRATION_SECONDS

logger = logging.getLogger(__name__)

# Set environment-specific memory limits
DEV_MAX_HISTORY = 20
PROD_MAX_HISTORY = 50

# Default for development
MAX_HISTORY = DEV_MAX_HISTORY

# Check if we're in production
try:
    from sqlalchemy.ext.asyncio import AsyncSession
    # More likely to be in production if we have this import
    MAX_HISTORY = PROD_MAX_HISTORY
except ImportError:
    # Stick with development default
    pass

logger.info(f"Memory configured for development environment with max_history={MAX_HISTORY}")


class MemoryAccessLevel(Enum):
    """Access level for memory items."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"


class ConversationMemory:
    """
    Memory storage for conversation contexts.
    
    This class provides:
    - Conversation history management
    - Working memory for agent coordination
    - User profile information
    - Entity tracking across conversation turns
    - Memory expiration
    """
    
    def __init__(self, session_id: str):
        """
        Initialize conversation memory.
        
        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.created_at = time.time()
        self.last_accessed = time.time()
        
        # Main memory storage
        self.conversation_history = []  # List of messages in the conversation
        self.working_memory = {}  # Temporary storage for cross-turn context
        self.entities = {}  # Extracted entities from the conversation
        self.user_profile = {}  # Information about the user
        
        # Access control for memory items
        self.memory_access = {}
        
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: Role of the message sender (user, assistant, system)
            content: Message content
            metadata: Optional metadata about the message
        """
        if not metadata:
            metadata = {}
            
        self.last_accessed = time.time()
        
        # Create message object
        message = {
            'role': role,
            'content': content,
            'timestamp': time.time(),
            'metadata': metadata
        }
        
        # Add to history
        self.conversation_history.append(message)
        
        # Trim history if it exceeds the maximum
        if len(self.conversation_history) > MAX_HISTORY:
            self.conversation_history = self.conversation_history[-MAX_HISTORY:]
            
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get the conversation history.
        
        Args:
            limit: Optional maximum number of messages to return (most recent first)
            
        Returns:
            List of messages
        """
        self.last_accessed = time.time()
        
        if limit and limit > 0:
            return self.conversation_history[-limit:]
        
        return self.conversation_history
        
    def set_memory_access(self, agent_name: str, access_level: MemoryAccessLevel, memory_keys: Optional[Dict[str, MemoryAccessLevel]] = None) -> None:
        """
        Set access levels for an agent to specific memory keys.
        
        Args:
            agent_name: Name of the agent
            access_level: Default access level for this agent
            memory_keys: Optional dictionary of memory keys to specific access levels
        """
        if not memory_keys:
            memory_keys = {}
            
        self.memory_access[agent_name] = {
            'default': access_level,
            'keys': memory_keys
        }
        
    def can_access(self, agent_name: str, memory_key: str, access_type: MemoryAccessLevel) -> bool:
        """
        Check if an agent has the specified access level to a memory key.
        
        Args:
            agent_name: Name of the agent
            memory_key: Memory key to check
            access_type: Access type to check for
            
        Returns:
            True if agent has the specified access, False otherwise
        """
        if agent_name not in self.memory_access:
            # No specific access rules, deny access
            return False
            
        agent_access = self.memory_access[agent_name]
        
        # Check for specific access rule for this key
        if 'keys' in agent_access and memory_key in agent_access['keys']:
            key_access = agent_access['keys'][memory_key]
            
            # READ_WRITE access includes READ_ONLY
            if access_type == MemoryAccessLevel.READ_ONLY:
                return True
            
            # For READ_WRITE access, the agent must have READ_WRITE access
            return key_access == MemoryAccessLevel.READ_WRITE
            
        # Fall back to default access level
        default_access = agent_access.get('default', MemoryAccessLevel.READ_ONLY)
        
        # READ_WRITE access includes READ_ONLY
        if access_type == MemoryAccessLevel.READ_ONLY:
            return True
            
        # For READ_WRITE access, the agent must have READ_WRITE access
        return default_access == MemoryAccessLevel.READ_WRITE
        
    def get_from_working_memory(self, key: str, default=None):
        """
        Get an item from working memory.
        
        Args:
            key: Memory key
            default: Default value if key not found
            
        Returns:
            Value from working memory, or default if not found
        """
        self.last_accessed = time.time()
        return self.working_memory.get(key, default)
        
    def update_working_memory(self, key: str, value) -> None:
        """
        Update an item in working memory.
        
        Args:
            key: Memory key
            value: Value to store
        """
        self.last_accessed = time.time()
        self.working_memory[key] = value
        
    def clear_working_memory(self) -> None:
        """Clear all working memory."""
        self.last_accessed = time.time()
        self.working_memory = {}
        
    def add_entity(self, entity_type: str, entity_value: str, agent_name: Optional[str] = None, confidence: float = 1.0) -> None:
        """
        Add an entity to the entities collection.
        
        Args:
            entity_type: Type of entity (e.g., product, store, order)
            entity_value: Value of the entity
            agent_name: Optional name of the agent that detected the entity
            confidence: Confidence score for the entity detection
        """
        self.last_accessed = time.time()
        
        if entity_type not in self.entities:
            self.entities[entity_type] = []
            
        # Add entity with metadata
        self.entities[entity_type].append({
            'value': entity_value,
            'agent': agent_name,
            'confidence': confidence,
            'timestamp': time.time()
        })
        
    def get_entities(self, entity_type: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get entities from memory.
        
        Args:
            entity_type: Optional entity type to filter by
            
        Returns:
            Dictionary of entity types to lists of entity values
        """
        self.last_accessed = time.time()
        
        if entity_type:
            return {entity_type: self.entities.get(entity_type, [])}
            
        return self.entities
        
    def update_user_profile(self, key: str, value) -> None:
        """
        Update user profile information.
        
        Args:
            key: Profile key
            value: Profile value
        """
        self.last_accessed = time.time()
        self.user_profile[key] = value
        
    def get_user_profile(self, key: Optional[str] = None):
        """
        Get user profile information.
        
        Args:
            key: Optional profile key to get
            
        Returns:
            Profile value if key provided, otherwise entire profile
        """
        self.last_accessed = time.time()
        
        if key:
            return self.user_profile.get(key)
            
        return self.user_profile
        
    def is_expired(self) -> bool:
        """
        Check if this memory has expired.
        
        Returns:
            True if memory has expired, False otherwise
        """
        seconds_since_access = time.time() - self.last_accessed
        return seconds_since_access > MEMORY_EXPIRATION_SECONDS
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert memory to dictionary for serialization.
        
        Returns:
            Dictionary representation of memory
        """
        return {
            'session_id': self.session_id,
            'created_at': self.created_at,
            'last_accessed': self.last_accessed,
            'conversation_history': self.conversation_history,
            'working_memory': self.working_memory,
            'entities': self.entities,
            'user_profile': self.user_profile
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMemory':
        """
        Create memory instance from dictionary.
        
        Args:
            data: Dictionary representation of memory
            
        Returns:
            ConversationMemory instance
        """
        memory = cls(data['session_id'])
        memory.created_at = data.get('created_at', time.time())
        memory.last_accessed = data.get('last_accessed', time.time())
        memory.conversation_history = data.get('conversation_history', [])
        memory.working_memory = data.get('working_memory', {})
        memory.entities = data.get('entities', {})
        memory.user_profile = data.get('user_profile', {})
        
        return memory
        
    def to_json(self) -> str:
        """
        Convert memory to JSON string.
        
        Returns:
            JSON string representation of memory
        """
        return json.dumps(self.to_dict())
        
    @classmethod
    def from_json(cls, json_str: str) -> 'ConversationMemory':
        """
        Create memory instance from JSON string.
        
        Args:
            json_str: JSON string representation of memory
            
        Returns:
            ConversationMemory instance
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


class AsyncConversationMemory:
    """
    Asynchronous wrapper for ConversationMemory that uses database storage.
    
    This class provides the same interface as ConversationMemory, but stores
    the memory in a database for persistence across restarts.
    """
    
    def __init__(self, session_id: str, db: AsyncSession):
        """
        Initialize async conversation memory.
        
        Args:
            session_id: Unique session identifier
            db: Database session
        """
        self.session_id = session_id
        self.db = db
        self.memory = None
        
    async def load(self) -> None:
        """Load memory from database."""
        from backend.repositories.memory_repository import MemoryRepository
        
        repository = MemoryRepository(self.db)
        memory_data = await repository.get_memory(self.session_id)
        
        if memory_data:
            self.memory = ConversationMemory.from_dict(memory_data)
        else:
            self.memory = ConversationMemory(self.session_id)
            
    async def save(self) -> None:
        """Save memory to database."""
        from backend.repositories.memory_repository import MemoryRepository
        
        if self.memory:
            repository = MemoryRepository(self.db)
            await repository.save_memory(self.memory.to_dict())
            
    async def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: Role of the message sender (user, assistant, system)
            content: Message content
            metadata: Optional metadata about the message
        """
        if not self.memory:
            await self.load()
            
        self.memory.add_message(role, content, metadata)
        await self.save()
        
    async def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get the conversation history.
        
        Args:
            limit: Optional maximum number of messages to return (most recent first)
            
        Returns:
            List of messages
        """
        if not self.memory:
            await self.load()
            
        return self.memory.get_conversation_history(limit)
        
    async def set_memory_access(self, agent_name: str, access_level: MemoryAccessLevel, memory_keys: Optional[Dict[str, MemoryAccessLevel]] = None) -> None:
        """
        Set access levels for an agent to specific memory keys.
        
        Args:
            agent_name: Name of the agent
            access_level: Default access level for this agent
            memory_keys: Optional dictionary of memory keys to specific access levels
        """
        if not self.memory:
            await self.load()
            
        self.memory.set_memory_access(agent_name, access_level, memory_keys)
        await self.save()
        
    async def can_access(self, agent_name: str, memory_key: str, access_type: MemoryAccessLevel) -> bool:
        """
        Check if an agent has the specified access level to a memory key.
        
        Args:
            agent_name: Name of the agent
            memory_key: Memory key to check
            access_type: Access type to check for
            
        Returns:
            True if agent has the specified access, False otherwise
        """
        if not self.memory:
            await self.load()
            
        return self.memory.can_access(agent_name, memory_key, access_type)
        
    async def get_from_working_memory(self, key: str, default=None):
        """
        Get an item from working memory.
        
        Args:
            key: Memory key
            default: Default value if key not found
            
        Returns:
            Value from working memory, or default if not found
        """
        if not self.memory:
            await self.load()
            
        return self.memory.get_from_working_memory(key, default)
        
    async def update_working_memory(self, key: str, value) -> None:
        """
        Update an item in working memory.
        
        Args:
            key: Memory key
            value: Value to store
        """
        if not self.memory:
            await self.load()
            
        self.memory.update_working_memory(key, value)
        await self.save()
        
    async def clear_working_memory(self) -> None:
        """Clear all working memory."""
        if not self.memory:
            await self.load()
            
        self.memory.clear_working_memory()
        await self.save()
        
    async def add_entity(self, entity_type: str, entity_value: str, agent_name: Optional[str] = None, confidence: float = 1.0) -> None:
        """
        Add an entity to the entities collection.
        
        Args:
            entity_type: Type of entity (e.g., product, store, order)
            entity_value: Value of the entity
            agent_name: Optional name of the agent that detected the entity
            confidence: Confidence score for the entity detection
        """
        if not self.memory:
            await self.load()
            
        self.memory.add_entity(entity_type, entity_value, agent_name, confidence)
        await self.save()
        
    async def get_entities(self, entity_type: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get entities from memory.
        
        Args:
            entity_type: Optional entity type to filter by
            
        Returns:
            Dictionary of entity types to lists of entity values
        """
        if not self.memory:
            await self.load()
            
        return self.memory.get_entities(entity_type)
        
    async def update_user_profile(self, key: str, value) -> None:
        """
        Update user profile information.
        
        Args:
            key: Profile key
            value: Profile value
        """
        if not self.memory:
            await self.load()
            
        self.memory.update_user_profile(key, value)
        await self.save()
        
    async def get_user_profile(self, key: Optional[str] = None):
        """
        Get user profile information.
        
        Args:
            key: Optional profile key to get
            
        Returns:
            Profile value if key provided, otherwise entire profile
        """
        if not self.memory:
            await self.load()
            
        return self.memory.get_user_profile(key)
        
    async def is_expired(self) -> bool:
        """
        Check if this memory has expired.
        
        Returns:
            True if memory has expired, False otherwise
        """
        if not self.memory:
            await self.load()
            
        return self.memory.is_expired()


# Function to create a memory repository table in the database
async def create_memory_table(db: AsyncSession):
    """
    Create the memory table in the database if it doesn't exist.
    
    Args:
        db: Database session
    """
    # Execute raw SQL to create the table if needed
    query = """
    CREATE TABLE IF NOT EXISTS conversation_memory (
        session_id VARCHAR(255) PRIMARY KEY,
        memory_data JSONB NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    await db.execute(query)
    await db.commit()


# Function to migrate data if needed
async def migrate_memory_data(db: AsyncSession):
    """
    Migrate memory data if needed (for version upgrades).
    
    Args:
        db: Database session
    """
    # This function would be implemented when migrations are needed
    pass