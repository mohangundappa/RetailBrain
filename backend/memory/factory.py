"""
Factory module for mem0 memory system.

This module provides factory functions for creating and accessing
mem0 memory instances throughout the application.
"""

import logging
from typing import Dict, Optional, Any

from backend.memory.mem0 import Mem0
from backend.memory.config import MemoryConfig
from backend.memory.database import get_db_session

logger = logging.getLogger(__name__)

# Global dictionary to store mem0 instances by name
_mem0_instances: Dict[str, Mem0] = {}


async def get_mem0(name: str = "default", config: Optional[MemoryConfig] = None) -> Mem0:
    """
    Get or create a mem0 instance by name.
    
    This function returns an existing mem0 instance if one exists with the given name,
    or creates a new one if not.
    
    Args:
        name: The name of the mem0 instance
        config: Optional memory configuration
        
    Returns:
        Mem0 instance
    """
    global _mem0_instances
    
    # Return existing instance if available
    if name in _mem0_instances:
        return _mem0_instances[name]
    
    # Create configuration if not provided
    config = config or MemoryConfig()
    
    # Get database session
    db_session = await get_db_session() if config.use_database_storage else None
    
    # Create new instance
    mem0 = Mem0(memory_config=config, db_session=db_session)
    _mem0_instances[name] = mem0
    
    logger.info(f"Created new mem0 instance: {name}")
    return mem0


def get_mem0_sync(name: str = "default", config: Optional[MemoryConfig] = None) -> Mem0:
    """
    Get or create a mem0 instance by name (synchronous version).
    
    This function returns an existing mem0 instance if one exists with the given name,
    or creates a new one without database support if not.
    
    Args:
        name: The name of the mem0 instance
        config: Optional memory configuration
        
    Returns:
        Mem0 instance
    """
    global _mem0_instances
    
    # Return existing instance if available
    if name in _mem0_instances:
        return _mem0_instances[name]
    
    # Create configuration if not provided
    config = config or MemoryConfig()
    
    # For synchronous access, we don't use database
    config.use_database_storage = False
    
    # Create new instance
    mem0 = Mem0(memory_config=config, db_session=None)
    _mem0_instances[name] = mem0
    
    logger.info(f"Created new synchronous mem0 instance: {name}")
    return mem0


def reset_mem0(name: Optional[str] = None) -> None:
    """
    Reset mem0 instances.
    
    If a name is provided, only that instance is removed.
    If no name is provided, all instances are removed.
    
    Args:
        name: Optional name of the instance to reset
    """
    global _mem0_instances
    
    if name is not None:
        if name in _mem0_instances:
            del _mem0_instances[name]
            logger.info(f"Reset mem0 instance: {name}")
    else:
        _mem0_instances = {}
        logger.info("Reset all mem0 instances")