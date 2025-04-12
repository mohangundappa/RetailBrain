"""
State recovery utilities for the optimized implementation of Staples Brain.
This module provides functions for recovering and managing conversation state.
"""
import logging
from typing import Dict, Any, Optional, List, Union, Callable, Awaitable, TypeVar, Generic, cast

from sqlalchemy.ext.asyncio import AsyncSession

from backend.brain.optimized.state_persistence import (
    StatePersistenceManager,
    resilient_persist_state,
    resilient_create_checkpoint,
    resilient_recover_state,
    resilient_rollback_to_checkpoint,
    get_most_recent_state,
    check_db_connection,
    process_pending_operations
)

logger = logging.getLogger(__name__)

# Re-export functions from state_persistence
__all__ = [
    "StatePersistenceManager",
    "resilient_persist_state",
    "resilient_create_checkpoint",
    "resilient_recover_state",
    "resilient_rollback_to_checkpoint",
    "get_most_recent_state",
    "check_db_connection",
    "process_pending_operations"
]