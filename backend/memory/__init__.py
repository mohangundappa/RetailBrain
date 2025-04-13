"""
Memory package for Staples Brain.

This module provides the mem0 memory system, a high-performance memory
implementation for agent conversations and context management.
"""

from backend.memory.mem0 import Mem0, MemoryEntry, MemoryType, MemoryScope
from backend.memory.schema import MemoryEntryModel, MemoryIndexModel, MemoryContextModel
from backend.memory.config import MemoryConfig
from backend.memory.factory import get_mem0, get_mem0_sync, reset_mem0
from backend.memory.test_mem0 import run_mem0_test

__all__ = [
    # Core classes
    'Mem0',
    'MemoryEntry',
    'MemoryType',
    'MemoryScope',
    'MemoryConfig',
    
    # Database models
    'MemoryEntryModel',
    'MemoryIndexModel',
    'MemoryContextModel',
    
    # Factory functions
    'get_mem0',
    'get_mem0_sync',
    'reset_mem0',
    
    # Testing
    'run_mem0_test',
]