"""
State recovery utilities for the optimized implementation of Staples Brain.
This module provides functions for recovering and managing conversation state.
"""
import logging
from typing import Dict, Any, Optional, List, Union, Callable, Awaitable, TypeVar, Generic, cast

from sqlalchemy.ext.asyncio import AsyncSession

from backend.orchestration.state.persistence import (
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

# StateRecoveryManager class for handling state recovery
class StateRecoveryManager:
    """
    Manager for recovering and managing conversation state.
    Provides higher-level functionality on top of state persistence.
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize with database session"""
        self.db = db
        self.persistence_manager = StatePersistenceManager(db)
    
    async def recover_latest_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Recover the latest state for a session"""
        return await get_most_recent_state(session_id, self.db)
    
    async def recover_checkpoint(self, session_id: str, checkpoint_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Recover a specific checkpoint or the latest one"""
        return await resilient_recover_state(session_id, self.db, checkpoint_name)
    
    async def rollback(self, session_id: str, checkpoint_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Roll back to a checkpoint"""
        return await resilient_rollback_to_checkpoint(session_id, self.db, checkpoint_name)

# Re-export functions from state_persistence
__all__ = [
    "StatePersistenceManager",
    "StateRecoveryManager",
    "resilient_persist_state",
    "resilient_create_checkpoint",
    "resilient_recover_state",
    "resilient_rollback_to_checkpoint",
    "get_most_recent_state",
    "check_db_connection",
    "process_pending_operations"
]