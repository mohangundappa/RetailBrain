"""
Configuration module for the mem0 memory system.

This module defines configuration settings and utilities
for the memory system, including Redis connection parameters,
expiration policies, and feature flags.
"""

import os
from typing import Dict, Any, Optional

class MemoryConfig:
    """Configuration settings for the mem0 memory system."""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize memory configuration.
        
        Args:
            config_dict: Optional dictionary with configuration values
        """
        self.config = config_dict or {}
        
        # Redis connection settings
        # Use fakeredis:// by default for development, this doesn't require a real Redis server
        self.redis_url = self.get_env_or_default("REDIS_URL", "fakeredis://mem0:0")
        
        # Memory expiration settings (in seconds)
        self.working_memory_ttl = int(self.get_env_or_default("WORKING_MEMORY_TTL", "300"))  # 5 minutes
        self.short_term_memory_ttl = int(self.get_env_or_default("SHORT_TERM_MEMORY_TTL", "3600"))  # 1 hour
        self.long_term_memory_ttl = self.get_env_or_default("LONG_TERM_MEMORY_TTL", None)  # None = no expiration
        
        # Feature flags
        self.use_database_storage = self.get_env_or_default("USE_DATABASE_STORAGE", "true").lower() == "true"
        self.use_vector_search = self.get_env_or_default("USE_VECTOR_SEARCH", "false").lower() == "true"
        
        # Database settings
        self.db_chunk_size = int(self.get_env_or_default("DB_CHUNK_SIZE", "100"))
        
        # Key prefix for Redis
        self.redis_prefix = self.get_env_or_default("REDIS_PREFIX", "mem0")
    
    def get_env_or_default(self, key: str, default: Any) -> Any:
        """
        Get a configuration value from environment variables or config dict,
        with a fallback default value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found
            
        Returns:
            Configuration value
        """
        # Check environment variables first
        env_value = os.environ.get(key)
        if env_value is not None:
            return env_value
            
        # Then check config dict
        if key in self.config:
            return self.config[key]
            
        # Fallback to default
        return default
    
    def update(self, key: str, value: Any) -> None:
        """
        Update a configuration value.
        
        Args:
            key: Configuration key
            value: New value
        """
        self.config[key] = value
        
        # Update instance attribute if it exists
        if hasattr(self, key.lower()):
            setattr(self, key.lower(), value)
    
    def as_dict(self) -> Dict[str, Any]:
        """
        Get the configuration as a dictionary.
        
        Returns:
            Dictionary with configuration values
        """
        return {
            "redis_url": self.redis_url,
            "working_memory_ttl": self.working_memory_ttl,
            "short_term_memory_ttl": self.short_term_memory_ttl,
            "long_term_memory_ttl": self.long_term_memory_ttl,
            "use_database_storage": self.use_database_storage,
            "use_vector_search": self.use_vector_search,
            "db_chunk_size": self.db_chunk_size,
            "redis_prefix": self.redis_prefix
        }