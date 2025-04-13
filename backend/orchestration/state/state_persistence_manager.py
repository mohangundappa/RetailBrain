"""
State persistence management for Staples Brain using the optimized approach.
This module provides functionality for persisting, recovering, and checkpointing conversation state.
"""
import logging
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Union, TypeVar, Generic

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Type for state objects
StateType = TypeVar('StateType', bound=Dict[str, Any])

class ErrorType(str, Enum):
    """Enumeration of error types for state operations."""
    DB_ERROR = "db_error"
    SERIALIZATION_ERROR = "serialization_error"
    DESERIALIZATION_ERROR = "deserialization_error"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class StatePersistenceManager:
    """
    Manages persistence of conversation state in the database.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the state persistence manager.
        
        Args:
            db_session: Database session for persistence operations
        """
        self.db_session = db_session
    
    async def save_state(self, state: Dict[str, Any], session_id: str, is_checkpoint: bool = False, checkpoint_name: Optional[str] = None) -> Optional[str]:
        """
        Save state to the database.
        
        Args:
            state: State to save
            session_id: Session identifier
            is_checkpoint: Whether this is a checkpoint
            checkpoint_name: Optional name for the checkpoint
            
        Returns:
            ID of the saved state record, or None if saving failed
        """
        try:
            # Generate a unique ID for this state record
            state_id = str(uuid.uuid4())
            
            # Serialize the state to JSON
            state_json = json.dumps(state)
            
            # Insert into database
            query = text("""
            INSERT INTO orchestration_state (
                id, session_id, state_data, is_checkpoint, checkpoint_name, created_at
            ) VALUES (
                :id, :session_id, :state_data, :is_checkpoint, :checkpoint_name, :created_at
            )
            """)
            
            await self.db_session.execute(
                query,
                {
                    "id": state_id,
                    "session_id": session_id,
                    "state_data": state_json,
                    "is_checkpoint": is_checkpoint,
                    "checkpoint_name": checkpoint_name,
                    "created_at": datetime.now()
                }
            )
            
            await self.db_session.commit()
            
            return state_id
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}", exc_info=True)
            await self.db_session.rollback()
            return None
    
    async def get_state(self, session_id: str, checkpoint_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get state from the database.
        
        Args:
            session_id: Session identifier
            checkpoint_name: Optional name of checkpoint to retrieve
            
        Returns:
            Retrieved state, or None if not found
        """
        try:
            if checkpoint_name:
                # Get specific checkpoint
                query = text("""
                SELECT state_data FROM orchestration_state
                WHERE session_id = :session_id AND is_checkpoint = TRUE AND checkpoint_name = :checkpoint_name
                ORDER BY created_at DESC
                LIMIT 1
                """)
                
                result = await self.db_session.execute(
                    query,
                    {
                        "session_id": session_id,
                        "checkpoint_name": checkpoint_name
                    }
                )
            else:
                # Get latest state
                query = text("""
                SELECT state_data FROM orchestration_state
                WHERE session_id = :session_id
                ORDER BY created_at DESC
                LIMIT 1
                """)
                
                result = await self.db_session.execute(
                    query,
                    {
                        "session_id": session_id
                    }
                )
            
            row = result.fetchone()
            
            if row and row[0]:
                # Deserialize JSON
                return json.loads(row[0])
            
            return None
        except Exception as e:
            logger.error(f"Error getting state: {str(e)}", exc_info=True)
            return None
    
    async def get_latest_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest checkpoint for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Latest checkpoint state, or None if not found
        """
        try:
            query = text("""
            SELECT state_data FROM orchestration_state
            WHERE session_id = :session_id AND is_checkpoint = TRUE
            ORDER BY created_at DESC
            LIMIT 1
            """)
            
            result = await self.db_session.execute(
                query,
                {
                    "session_id": session_id
                }
            )
            
            row = result.fetchone()
            
            if row and row[0]:
                # Deserialize JSON
                return json.loads(row[0])
            
            return None
        except Exception as e:
            logger.error(f"Error getting latest checkpoint: {str(e)}", exc_info=True)
            return None
    
    async def list_checkpoints(self, session_id: str) -> List[Dict[str, Any]]:
        """
        List all checkpoints for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of checkpoint information
        """
        try:
            query = text("""
            SELECT id, checkpoint_name, created_at FROM orchestration_state
            WHERE session_id = :session_id AND is_checkpoint = TRUE
            ORDER BY created_at DESC
            """)
            
            result = await self.db_session.execute(
                query,
                {
                    "session_id": session_id
                }
            )
            
            checkpoints = []
            for row in result:
                checkpoints.append({
                    "id": row[0],
                    "name": row[1] or f"Checkpoint-{row[0]}",
                    "created_at": row[2].isoformat() if isinstance(row[2], datetime) else str(row[2])
                })
            
            return checkpoints
        except Exception as e:
            logger.error(f"Error listing checkpoints: {str(e)}", exc_info=True)
            return []


async def create_db_tables(db: AsyncSession) -> bool:
    """
    Create database tables for state persistence.
    
    Args:
        db: Database session
        
    Returns:
        True if creation was successful, False otherwise
    """
    try:
        query = text("""
        CREATE TABLE IF NOT EXISTS orchestration_state (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            state_data JSONB NOT NULL,
            is_checkpoint BOOLEAN DEFAULT FALSE,
            checkpoint_name TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            
            -- Indexes for faster queries
            INDEX idx_orchestration_state_session_id (session_id),
            INDEX idx_orchestration_state_created_at (created_at),
            INDEX idx_orchestration_state_checkpoint (session_id, is_checkpoint, checkpoint_name)
        )
        """)
        
        await db.execute(query)
        await db.commit()
        
        logger.info("Created orchestration_state table")
        return True
    except Exception as e:
        logger.error(f"Error creating state tables: {str(e)}", exc_info=True)
        await db.rollback()
        return False


# Resilient functions for state operations
async def check_db_connection(db: AsyncSession) -> bool:
    """
    Check database connection.
    
    Args:
        db: Database session
        
    Returns:
        True if connection is available, False otherwise
    """
    try:
        query = text("SELECT 1")
        await db.execute(query)
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return False


async def resilient_persist_state(state: Dict[str, Any], session_id: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Persist state with resilience to failures.
    
    Args:
        state: State to persist
        session_id: Session identifier
        db: Database session
        
    Returns:
        Updated state
    """
    try:
        manager = StatePersistenceManager(db)
        state_id = await manager.save_state(state, session_id)
        
        if state_id:
            # Update state with persistence info
            result = {**state, "persistence": {"last_persisted": datetime.now().isoformat()}}
            return result
        
        # If persistence failed, mark as dirty
        result = {**state, "persistence": {"state_dirty": True}}
        return result
    except Exception as e:
        logger.error(f"Error in resilient_persist_state: {str(e)}", exc_info=True)
        result = {**state, "persistence": {"state_dirty": True, "error": str(e)}}
        return result


async def resilient_create_checkpoint(state: Dict[str, Any], session_id: str, checkpoint_name: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Create a checkpoint with resilience to failures.
    
    Args:
        state: State to checkpoint
        session_id: Session identifier
        checkpoint_name: Name for the checkpoint
        db: Database session
        
    Returns:
        Updated state
    """
    try:
        manager = StatePersistenceManager(db)
        checkpoint_id = await manager.save_state(
            state, 
            session_id, 
            is_checkpoint=True, 
            checkpoint_name=checkpoint_name
        )
        
        if checkpoint_id:
            # Update state with checkpoint info
            result = {**state, "checkpoint": {
                "last_checkpoint": checkpoint_name,
                "last_checkpoint_id": checkpoint_id,
                "checkpoint_time": datetime.now().isoformat()
            }}
            return result
        
        # If checkpoint failed, mark as pending
        result = {**state, "checkpoint": {
            "pending_checkpoint": checkpoint_name,
            "checkpoint_error": "Failed to create checkpoint"
        }}
        return result
    except Exception as e:
        logger.error(f"Error in resilient_create_checkpoint: {str(e)}", exc_info=True)
        result = {**state, "checkpoint": {
            "pending_checkpoint": checkpoint_name,
            "checkpoint_error": str(e)
        }}
        return result


async def resilient_recover_state(session_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """
    Recover latest state with resilience to failures.
    
    Args:
        session_id: Session identifier
        db: Database session
        
    Returns:
        Recovered state, or None if not found
    """
    try:
        manager = StatePersistenceManager(db)
        state = await manager.get_state(session_id)
        return state
    except Exception as e:
        logger.error(f"Error in resilient_recover_state: {str(e)}", exc_info=True)
        return None


async def resilient_rollback_to_checkpoint(session_id: str, db: AsyncSession, checkpoint_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Roll back to a checkpoint with resilience to failures.
    
    Args:
        session_id: Session identifier
        db: Database session
        checkpoint_name: Name of checkpoint to roll back to
        
    Returns:
        Rolled back state, or None if not found
    """
    try:
        manager = StatePersistenceManager(db)
        
        if checkpoint_name:
            state = await manager.get_state(session_id, checkpoint_name)
        else:
            state = await manager.get_latest_checkpoint(session_id)
        
        if state:
            # Add rollback info to state
            result = {**state, "rollback": {
                "rolled_back_from": checkpoint_name,
                "rollback_time": datetime.now().isoformat()
            }}
            
            # Persist the rolled-back state
            await resilient_persist_state(result, session_id, db)
            
            return result
        
        return None
    except Exception as e:
        logger.error(f"Error in resilient_rollback_to_checkpoint: {str(e)}", exc_info=True)
        return None


async def get_most_recent_state(session_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """
    Get the most recent state for a session.
    
    Args:
        session_id: Session identifier
        db: Database session
        
    Returns:
        Most recent state, or None if not found
    """
    try:
        manager = StatePersistenceManager(db)
        return await manager.get_state(session_id)
    except Exception as e:
        logger.error(f"Error in get_most_recent_state: {str(e)}", exc_info=True)
        return None


async def process_pending_operations(state: Dict[str, Any], session_id: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Process any pending operations in the state.
    
    Args:
        state: Current state
        session_id: Session identifier
        db: Database session
        
    Returns:
        Updated state
    """
    result = {**state}
    
    # Check for pending persistence
    if state.get("persistence", {}).get("state_dirty", False):
        try:
            manager = StatePersistenceManager(db)
            state_id = await manager.save_state(state, session_id)
            
            if state_id:
                # Clear dirty flag
                result["persistence"] = {
                    "last_persisted": datetime.now().isoformat(),
                    "state_dirty": False
                }
        except Exception as e:
            logger.error(f"Error processing pending persistence: {str(e)}", exc_info=True)
    
    # Check for pending checkpoints
    pending_checkpoint = state.get("checkpoint", {}).get("pending_checkpoint")
    if pending_checkpoint:
        try:
            manager = StatePersistenceManager(db)
            checkpoint_id = await manager.save_state(
                state, 
                session_id, 
                is_checkpoint=True, 
                checkpoint_name=pending_checkpoint
            )
            
            if checkpoint_id:
                # Clear pending checkpoint
                result["checkpoint"] = {
                    "last_checkpoint": pending_checkpoint,
                    "last_checkpoint_id": checkpoint_id,
                    "checkpoint_time": datetime.now().isoformat(),
                    "pending_checkpoint": None
                }
        except Exception as e:
            logger.error(f"Error processing pending checkpoint: {str(e)}", exc_info=True)
    
    return result