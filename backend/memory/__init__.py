"""
Memory package for Staples Brain.

This module provides the mem0 memory system, a high-performance memory
implementation for agent conversations and context management.
"""

from backend.memory.mem0 import Mem0, MemoryEntry, MemoryType
from backend.memory.schema import MemoryEntryModel, MemoryIndexModel, MemoryContextModel

__all__ = [
    'Mem0',
    'MemoryEntry',
    'MemoryType',
    'MemoryEntryModel',
    'MemoryIndexModel',
    'MemoryContextModel',
]