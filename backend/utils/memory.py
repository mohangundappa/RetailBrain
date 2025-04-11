"""
Memory management utilities for Staples Brain.

This module provides classes and functions for managing conversation memory
and context persistence between agent interactions.

This module is environment-aware and will configure memory settings based on the
current environment (development, qa, staging, production).

The memory system supports bidirectional communication between Core Components and Agents,
allowing agents to both read from and write to the shared memory system.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Set, Union, Tuple
from enum import Enum
from datetime import datetime, timedelta
from backend.database.models import Conversation, Message
from backend.database.db import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Environment-specific memory configurations
MEMORY_CONFIG = {
    "development": {
        "max_history": 20,
        "memory_ttl": 60 * 30,  # 30 minutes in seconds
        "session_ttl": 60 * 60 * 24,  # 24 hours in seconds
    },
    "testing": {
        "max_history": 10,
        "memory_ttl": 60 * 5,  # 5 minutes in seconds
        "session_ttl": 60 * 60,  # 1 hour in seconds
    },
    "qa": {
        "max_history": 30,
        "memory_ttl": 60 * 60,  # 1 hour in seconds
        "session_ttl": 60 * 60 * 24 * 2,  # 2 days in seconds
    },
    "staging": {
        "max_history": 50,
        "memory_ttl": 60 * 60 * 3,  # 3 hours in seconds
        "session_ttl": 60 * 60 * 24 * 3,  # 3 days in seconds
    },
    "production": {
        "max_history": 100,
        "memory_ttl": 60 * 60 * 6,  # 6 hours in seconds
        "session_ttl": 60 * 60 * 24 * 7,  # 7 days in seconds
    }
}

# Get current environment (default to development)
CURRENT_ENV = os.environ.get("APP_ENV", "development")
if CURRENT_ENV not in MEMORY_CONFIG:
    logger.warning(f"Unknown environment '{CURRENT_ENV}'. Using development memory settings.")
    CURRENT_ENV = "development"

# Apply environment-specific configuration
current_memory_config = MEMORY_CONFIG[CURRENT_ENV]
DEFAULT_MAX_HISTORY = current_memory_config["max_history"]
MEMORY_TTL = current_memory_config["memory_ttl"]
SESSION_TTL = current_memory_config["session_ttl"]

logger.info(f"Memory configured for {CURRENT_ENV} environment with max_history={DEFAULT_MAX_HISTORY}")

class MemoryAccessLevel(Enum):
    """Access levels for memory operations."""
    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"

class MemoryScope(Enum):
    """Scope of memory storage."""
    SESSION = "session"        # Persists for the current session only
    CONVERSATION = "conversation"  # Persists for current conversation only
    USER = "user"              # Persists across all user sessions
    GLOBAL = "global"          # Shared across all users and sessions

class MemoryChannel:
    """
    Represents a bidirectional communication channel between components.
    
    A channel is identified by a name and allows exchange of data
    between Core Components and Agents with appropriate access control.
    """
    
    def __init__(
        self, 
        name: str, 
        description: str,
        scope: MemoryScope = MemoryScope.SESSION,
        permissions: Dict[str, MemoryAccessLevel] = None
    ):
        """
        Initialize a memory channel.
        
        Args:
            name: Channel identifier
            description: Human-readable description of the channel's purpose
            scope: Persistence scope (session, conversation, user, global)
            permissions: Dict mapping component names to access levels
        """
        self.name = name
        self.description = description
        self.scope = scope
        self.permissions = permissions or {}
        self.data: Dict[str, Any] = {}
        self.subscribers: Set[str] = set()
        self.last_updated: Optional[datetime] = None
        
    def can_read(self, component_name: str) -> bool:
        """Check if a component has read access."""
        access = self.permissions.get(component_name, None)
        if access is None:
            # Check for wildcard access
            access = self.permissions.get("*", None)
        return access in (MemoryAccessLevel.READ, MemoryAccessLevel.READ_WRITE)
    
    def can_write(self, component_name: str) -> bool:
        """Check if a component has write access."""
        access = self.permissions.get(component_name, None)
        if access is None:
            # Check for wildcard access
            access = self.permissions.get("*", None)
        return access in (MemoryAccessLevel.WRITE, MemoryAccessLevel.READ_WRITE)
    
    def subscribe(self, component_name: str) -> bool:
        """Subscribe a component to updates on this channel."""
        if self.can_read(component_name):
            self.subscribers.add(component_name)
            return True
        return False
    
    def unsubscribe(self, component_name: str) -> None:
        """Unsubscribe a component from updates."""
        self.subscribers.discard(component_name)
    
    def get_value(self, key: str, default: Any = None, component_name: str = None) -> Any:
        """Get a value from the channel, checking read permissions if component_name provided."""
        if component_name and not self.can_read(component_name):
            logger.warning(f"Access denied: {component_name} attempted to read from {self.name}")
            return default
        return self.data.get(key, default)
    
    def set_value(self, key: str, value: Any, component_name: str = None) -> bool:
        """Set a value in the channel, checking write permissions if component_name provided."""
        if component_name and not self.can_write(component_name):
            logger.warning(f"Access denied: {component_name} attempted to write to {self.name}")
            return False
        
        self.data[key] = value
        self.last_updated = datetime.utcnow()
        return True
    
    def get_all(self, component_name: str = None) -> Dict[str, Any]:
        """Get all data in the channel, checking read permissions if component_name provided."""
        if component_name and not self.can_read(component_name):
            logger.warning(f"Access denied: {component_name} attempted to read all data from {self.name}")
            return {}
        return self.data.copy()
    
    def update(self, updates: Dict[str, Any], component_name: str = None) -> bool:
        """Update multiple values in the channel, checking write permissions if component_name provided."""
        if component_name and not self.can_write(component_name):
            logger.warning(f"Access denied: {component_name} attempted to update {self.name}")
            return False
        
        self.data.update(updates)
        self.last_updated = datetime.utcnow()
        return True
    
    def clear(self, component_name: str = None) -> bool:
        """Clear all data in the channel, checking write permissions if component_name provided."""
        if component_name and not self.can_write(component_name):
            logger.warning(f"Access denied: {component_name} attempted to clear {self.name}")
            return False
        
        self.data.clear()
        self.last_updated = datetime.utcnow()
        return True

class MemoryManager:
    """
    Central memory management system for Staples Brain.
    
    This class provides a unified interface for managing communication channels,
    persistent conversation memory, and context sharing between core components
    and agents. It supports bidirectional communication with access control
    and different persistence scopes.
    """
    
    # Default communication channels
    DEFAULT_CHANNELS = [
        {
            "name": "orchestrator",
            "description": "Communication channel for orchestrator to agents",
            "scope": MemoryScope.SESSION,
            "permissions": {
                "orchestrator": MemoryAccessLevel.READ_WRITE,
                "intent_handler": MemoryAccessLevel.READ,
                "*": MemoryAccessLevel.READ  # All agents can read
            }
        },
        {
            "name": "agent_outputs",
            "description": "Channel for agent outputs and results",
            "scope": MemoryScope.SESSION,
            "permissions": {
                "orchestrator": MemoryAccessLevel.READ_WRITE,
                "intent_handler": MemoryAccessLevel.READ,
                "*": MemoryAccessLevel.WRITE  # All agents can write
            }
        },
        {
            "name": "user_info",
            "description": "User profile and preferences",
            "scope": MemoryScope.USER,
            "permissions": {
                "orchestrator": MemoryAccessLevel.READ_WRITE,
                "intent_handler": MemoryAccessLevel.READ_WRITE,
                "*": MemoryAccessLevel.READ  # All agents can read
            }
        },
        {
            "name": "shared_context",
            "description": "Cross-agent shared context",
            "scope": MemoryScope.SESSION,
            "permissions": {
                "*": MemoryAccessLevel.READ_WRITE  # All components can read/write
            }
        },
        {
            "name": "api_cache",
            "description": "Cache for API responses",
            "scope": MemoryScope.SESSION,
            "permissions": {
                "orchestrator": MemoryAccessLevel.READ_WRITE,
                "*": MemoryAccessLevel.READ_WRITE  # All components can read/write
            }
        }
    ]
    
    def __init__(self, session_id: str):
        """
        Initialize the memory manager.
        
        Args:
            session_id: The unique session identifier
        """
        self.session_id = session_id
        self.user_id = None  # Will be set when user is identified
        self.channels: Dict[str, MemoryChannel] = {}
        
        # Initialize default channels
        for channel_config in self.DEFAULT_CHANNELS:
            self.create_channel(
                name=channel_config["name"],
                description=channel_config["description"],
                scope=channel_config["scope"],
                permissions=channel_config["permissions"]
            )
        
        logger.debug(f"Initialized memory manager for session {session_id} with {len(self.channels)} channels")
    
    def create_channel(
        self, 
        name: str, 
        description: str,
        scope: MemoryScope = MemoryScope.SESSION,
        permissions: Dict[str, MemoryAccessLevel] = None
    ) -> MemoryChannel:
        """
        Create a new communication channel.
        
        Args:
            name: Channel identifier
            description: Human-readable description of the channel's purpose
            scope: Persistence scope
            permissions: Dict mapping component names to access levels
            
        Returns:
            The created channel
        """
        if name in self.channels:
            logger.warning(f"Channel {name} already exists, returning existing channel")
            return self.channels[name]
        
        channel = MemoryChannel(name, description, scope, permissions)
        self.channels[name] = channel
        
        logger.debug(f"Created memory channel: {name} ({scope.value})")
        return channel
    
    def get_channel(self, name: str) -> Optional[MemoryChannel]:
        """
        Get a channel by name.
        
        Args:
            name: Channel identifier
            
        Returns:
            The channel or None if not found
        """
        return self.channels.get(name)
    
    def set_value(self, channel_name: str, key: str, value: Any, component_name: str = None) -> bool:
        """
        Set a value in a channel.
        
        Args:
            channel_name: Channel identifier
            key: Key to store the value under
            value: The value to store
            component_name: Optional component name for access control
            
        Returns:
            True if successful, False otherwise
        """
        channel = self.get_channel(channel_name)
        if not channel:
            logger.warning(f"Channel {channel_name} not found")
            return False
        
        return channel.set_value(key, value, component_name)
    
    def get_value(self, channel_name: str, key: str, default: Any = None, component_name: str = None) -> Any:
        """
        Get a value from a channel.
        
        Args:
            channel_name: Channel identifier
            key: Key to retrieve
            default: Default value if key not found
            component_name: Optional component name for access control
            
        Returns:
            The value or default if not found
        """
        channel = self.get_channel(channel_name)
        if not channel:
            logger.warning(f"Channel {channel_name} not found")
            return default
        
        return channel.get_value(key, default, component_name)
    
    def update_channel(self, channel_name: str, updates: Dict[str, Any], component_name: str = None) -> bool:
        """
        Update multiple values in a channel.
        
        Args:
            channel_name: Channel identifier
            updates: Dictionary of updates
            component_name: Optional component name for access control
            
        Returns:
            True if successful, False otherwise
        """
        channel = self.get_channel(channel_name)
        if not channel:
            logger.warning(f"Channel {channel_name} not found")
            return False
        
        return channel.update(updates, component_name)
    
    def subscribe(self, channel_name: str, component_name: str) -> bool:
        """
        Subscribe a component to channel updates.
        
        Args:
            channel_name: Channel identifier
            component_name: Component to subscribe
            
        Returns:
            True if successful, False otherwise
        """
        channel = self.get_channel(channel_name)
        if not channel:
            logger.warning(f"Channel {channel_name} not found")
            return False
        
        return channel.subscribe(component_name)
    
    def get_subscribers(self, channel_name: str) -> Set[str]:
        """
        Get all subscribers to a channel.
        
        Args:
            channel_name: Channel identifier
            
        Returns:
            Set of subscriber component names
        """
        channel = self.get_channel(channel_name)
        if not channel:
            logger.warning(f"Channel {channel_name} not found")
            return set()
        
        return channel.subscribers.copy()
    
    def get_channel_data(self, channel_name: str, component_name: str = None) -> Dict[str, Any]:
        """
        Get all data from a channel.
        
        Args:
            channel_name: Channel identifier
            component_name: Optional component name for access control
            
        Returns:
            Dictionary of channel data
        """
        channel = self.get_channel(channel_name)
        if not channel:
            logger.warning(f"Channel {channel_name} not found")
            return {}
        
        return channel.get_all(component_name)
    
    def serialize_channels(self) -> Dict[str, Any]:
        """
        Serialize all channels for storage or transmission.
        
        Returns:
            Dictionary of serialized channels
        """
        serialized = {}
        for name, channel in self.channels.items():
            serialized[name] = {
                "name": channel.name,
                "description": channel.description,
                "scope": channel.scope.value,
                "data": channel.data,
                "last_updated": channel.last_updated.isoformat() if channel.last_updated else None
            }
        return serialized
    
    def get_all_channel_data(self, component_name: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all accessible channel data for a component.
        
        Args:
            component_name: Component requesting data
            
        Returns:
            Dictionary mapping channel names to their data
        """
        result = {}
        for name, channel in self.channels.items():
            if channel.can_read(component_name):
                result[name] = channel.get_all(component_name)
        return result


class ConversationMemory:
    """
    Manages persistent conversation memory across sessions and agents.
    
    This class provides an interface for storing and retrieving conversation
    history from the database and maintaining context between agent interactions.
    
    It integrates with the MemoryManager for bidirectional communication between
    core components and agents.
    """
    
    def __init__(self, session_id: str, max_history: Optional[int] = None):
        """
        Initialize a conversation memory manager.
        
        Args:
            session_id: The session ID to track conversation history
            max_history: Maximum number of messages to include in history (defaults to environment setting)
        """
        self.session_id = session_id
        self.max_history = max_history if max_history is not None else DEFAULT_MAX_HISTORY
        self.working_memory: Dict[str, Any] = {}
        self.context: Dict[str, Any] = {}
        
        # Initialize memory manager for bidirectional communication
        self.memory_manager = MemoryManager(session_id)
        
        logger.debug(f"Initialized conversation memory for session {session_id} with max_history={self.max_history}")
        
    def load_conversation_history(self, conversation_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load conversation history from the database.
        
        Args:
            conversation_id: Optional specific conversation ID to load
            
        Returns:
            List of message dictionaries in chronological order
        """
        try:
            if conversation_id:
                # Load messages from a specific conversation
                conversation = Conversation.query.get(conversation_id)
                if not conversation:
                    logger.warning(f"Conversation {conversation_id} not found")
                    return []
                
                messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at).all()
            else:
                # Load latest messages from the session
                conversations = Conversation.query.filter_by(session_id=self.session_id).order_by(Conversation.created_at.desc()).limit(5).all()
                conversation_ids = [conv.id for conv in conversations]
                
                if not conversation_ids:
                    return []
                
                messages = Message.query.filter(Message.conversation_id.in_(conversation_ids)).order_by(Message.created_at).limit(self.max_history).all()
            
            # Convert to list of dictionaries
            message_list = [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.created_at.isoformat(),
                    "conversation_id": msg.conversation_id
                }
                for msg in messages
            ]
            
            logger.debug(f"Loaded {len(message_list)} messages from history")
            return message_list
            
        except Exception as e:
            logger.error(f"Error loading conversation history: {str(e)}", exc_info=True)
            return []
    
    def add_message(self, role: str, content: str, conversation_id: int) -> bool:
        """
        Add a message to the conversation history.
        
        Args:
            role: The role of the message sender ('user', 'assistant', 'system')
            content: The message content
            conversation_id: The ID of the conversation to add this message to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create and add message to database
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content
            )
            db.session.add(message)
            db.session.commit()
            
            logger.debug(f"Added {role} message to conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding message to history: {str(e)}", exc_info=True)
            db.session.rollback()
            return False
    
    def get_system_prompt(self, agent_name: str) -> str:
        """
        Get a system prompt with context from conversation history.
        
        Args:
            agent_name: The name of the agent requesting the prompt
            
        Returns:
            A system prompt string with relevant context
        """
        # Load the conversation history
        history = self.load_conversation_history()
        
        # Extract agent-specific context
        agent_context = self.get_agent_context(agent_name)
        
        # Prepare a condensed version of the conversation history
        history_summary = self._create_history_summary(history)
        
        # Combine history and context into a system prompt
        system_prompt = f"""You are a helpful Staples assistant specializing in {agent_name}.
        
Conversation history summary:
{history_summary}

Relevant context:
{self._format_context(agent_context)}

Use this information to provide a helpful and contextually relevant response.
"""
        return system_prompt
    
    def _create_history_summary(self, history: List[Dict[str, Any]]) -> str:
        """Create a summary of conversation history."""
        if not history:
            return "No previous conversation."
        
        # Include last few turns of conversation
        recent_turns = history[-min(5, len(history)):]
        history_text = "\n".join([
            f"{msg['role'].title()}: {msg['content']}" 
            for msg in recent_turns
        ])
        
        return history_text
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as a readable string."""
        if not context:
            return "No specific context information available."
        
        lines = []
        for key, value in context.items():
            if isinstance(value, dict):
                lines.append(f"- {key}:")
                for sub_key, sub_value in value.items():
                    lines.append(f"  - {sub_key}: {sub_value}")
            else:
                lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)
    
    def update_working_memory(self, key: str, value: Any, component_name: str = None) -> None:
        """
        Update working memory with a key-value pair.
        
        This method maintains backward compatibility with the legacy approach
        while also utilizing the new MemoryManager for bidirectional communication.
        
        Args:
            key: Memory key
            value: Memory value
            component_name: Optional component name for access control
        """
        # Update legacy working memory
        self.working_memory[key] = value
        
        # Also update in the shared context channel
        self.memory_manager.set_value("shared_context", key, value, component_name)
        
        logger.debug(f"Updated working memory: {key}")
    
    def get_working_memory(self, key: str, default: Any = None, component_name: str = None) -> Any:
        """
        Get a value from working memory.
        
        Args:
            key: Memory key
            default: Default value to return if key not found
            component_name: Optional component name for access control
            
        Returns:
            The stored value or default if not found
        """
        # Try to get from memory manager first (respects access control)
        if component_name:
            value = self.memory_manager.get_value("shared_context", key, None, component_name)
            if value is not None:
                return value
                
        # Fall back to legacy memory
        return self.working_memory.get(key, default)
    
    def update_context(self, agent_name: str, context_updates: Dict[str, Any]) -> None:
        """
        Update context for a specific agent.
        
        This method uses both legacy context storage and the new memory manager
        to ensure backward compatibility while enabling bidirectional communication.
        
        Args:
            agent_name: The name of the agent
            context_updates: Dictionary of context updates
        """
        # Update legacy context
        if agent_name not in self.context:
            self.context[agent_name] = {}
        
        self.context[agent_name].update(context_updates)
        
        # Update in the memory manager
        # Store in agent-specific namespace within shared context
        agent_key = f"agent:{agent_name}"
        current_data = self.memory_manager.get_value("shared_context", agent_key, {})
        current_data.update(context_updates)
        self.memory_manager.set_value("shared_context", agent_key, current_data, agent_name)
        
        # Also update in the agent outputs channel for other components to consume
        self.memory_manager.update_channel("agent_outputs", {agent_name: context_updates}, agent_name)
        
        logger.debug(f"Updated context for {agent_name}")
    
    def get_agent_context(self, agent_name: str) -> Dict[str, Any]:
        """
        Get context for a specific agent.
        
        Combines data from both legacy storage and the memory manager.
        
        Args:
            agent_name: The name of the agent
            
        Returns:
            The agent's context dictionary
        """
        # Get from legacy context
        legacy_context = self.context.get(agent_name, {})
        
        # Get from memory manager's shared context
        agent_key = f"agent:{agent_name}"
        manager_context = self.memory_manager.get_value("shared_context", agent_key, {}, agent_name)
        
        # Merge both contexts with manager context taking precedence
        merged_context = {**legacy_context, **manager_context}
        
        return merged_context
    
    def get_full_context(self) -> Dict[str, Any]:
        """
        Get the full context across all agents.
        
        Returns:
            The complete context dictionary
        """
        # Combine legacy working memory and agent contexts
        legacy_context = {
            "working_memory": self.working_memory,
            "agent_contexts": self.context,
            "session_id": self.session_id,
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Get context from memory manager
        manager_context = {
            "channels": self.memory_manager.serialize_channels(),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Combine both sources
        full_context = {
            "legacy": legacy_context,
            "memory_manager": manager_context
        }
        
        return full_context
        
    # New methods for bidirectional communication
    
    def send_message(self, from_component: str, to_component: str, message_type: str, content: Any) -> bool:
        """
        Send a message from one component to another.
        
        Args:
            from_component: Sender component name
            to_component: Recipient component name
            message_type: Type of message (e.g., 'command', 'result', 'status')
            content: Message content
            
        Returns:
            True if message was sent successfully
        """
        message = {
            "from": from_component,
            "to": to_component,
            "type": message_type,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store message in the orchestrator channel
        return self.memory_manager.set_value("orchestrator", 
                                            f"message:{datetime.utcnow().timestamp()}", 
                                            message, 
                                            from_component)
    
    def get_messages_for(self, component_name: str) -> List[Dict[str, Any]]:
        """
        Get all messages addressed to a specific component.
        
        Args:
            component_name: Component name to get messages for
            
        Returns:
            List of messages
        """
        # Get all messages from orchestrator channel
        all_messages = self.memory_manager.get_channel_data("orchestrator", component_name)
        
        # Filter messages for this component
        component_messages = []
        for key, message in all_messages.items():
            if isinstance(message, dict) and message.get("to") == component_name:
                component_messages.append(message)
                
        # Sort by timestamp
        component_messages.sort(key=lambda m: m.get("timestamp", ""))
        
        return component_messages
    
    def create_custom_channel(self, name: str, description: str, permissions: Dict[str, MemoryAccessLevel]) -> bool:
        """
        Create a custom communication channel.
        
        Args:
            name: Channel name
            description: Channel description
            permissions: Dictionary mapping component names to access levels
            
        Returns:
            True if channel was created
        """
        try:
            self.memory_manager.create_channel(name, description, MemoryScope.SESSION, permissions)
            return True
        except Exception as e:
            logger.error(f"Error creating channel {name}: {str(e)}")
            return False
    
    def store_api_result(self, api_name: str, endpoint: str, params: Dict[str, Any], result: Any) -> None:
        """
        Store an API result in the cache.
        
        Args:
            api_name: Name of the API service
            endpoint: API endpoint
            params: Request parameters
            result: API result to cache
        """
        # Create a cache key from the API details
        cache_key = f"{api_name}:{endpoint}:{json.dumps(params, sort_keys=True)}"
        
        # Store in the API cache channel
        cache_entry = {
            "api": api_name,
            "endpoint": endpoint,
            "params": params,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "expires": (datetime.utcnow() + timedelta(seconds=MEMORY_TTL)).isoformat()
        }
        
        self.memory_manager.set_value("api_cache", cache_key, cache_entry)
    
    def get_cached_api_result(self, api_name: str, endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
        """
        Get a cached API result if available.
        
        Args:
            api_name: Name of the API service
            endpoint: API endpoint
            params: Request parameters
            
        Returns:
            Cached result or None if not in cache or expired
        """
        # Create a cache key from the API details
        cache_key = f"{api_name}:{endpoint}:{json.dumps(params, sort_keys=True)}"
        
        # Get from the API cache channel
        cache_entry = self.memory_manager.get_value("api_cache", cache_key)
        
        if not cache_entry:
            return None
            
        # Check if entry has expired
        try:
            expires = datetime.fromisoformat(cache_entry.get("expires", ""))
            if expires < datetime.utcnow():
                # Expired entry
                return None
        except (ValueError, TypeError):
            # Invalid expiration, consider expired
            return None
            
        return cache_entry.get("result")