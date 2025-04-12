"""
State persistence and recovery for the LangGraph-based orchestration system.

This module provides functionality for persisting and recovering orchestration state
across requests and sessions, enabling conversation continuity and handling
interrupted or failed operations.
"""

import logging
import uuid
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, TypeVar, cast

from sqlalchemy import select, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.brain.native_graph.state_definitions import OrchestrationState
from backend.brain.native_graph.error_handling import record_error, ErrorType

logger = logging.getLogger(__name__)

# Define a type variable for the state
StateType = TypeVar('StateType', bound=Dict[str, Any])

# Key prefixes for different state types
STATE_PREFIX = "state:"
SESSION_PREFIX = "session:"
CHECKPOINT_PREFIX = "checkpoint:"

# Constants for state management
STATE_EXPIRATION_DAYS = 7  # How long to keep state in the database
MAX_CHECKPOINTS = 5  # Maximum number of checkpoints to keep per session


class StatePersistenceManager:
    """
    Manager for persisting and recovering state in the LangGraph orchestration system.
    
    This class provides methods for:
    1. Saving graph state to the database
    2. Loading state from the database
    3. Creating checkpoints at critical stages
    4. Rolling back to previous checkpoints
    5. Cleaning up expired state data
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize the state persistence manager.
        
        Args:
            db_session: SQLAlchemy async session for database access
        """
        self.db = db_session
        
    async def save_state(
        self, 
        state: StateType, 
        session_id: str,
        checkpoint_name: Optional[str] = None
    ) -> str:
        """
        Save the current state to the database.
        
        Args:
            state: The state to save
            session_id: The session ID to associate with the state
            checkpoint_name: Optional name for the checkpoint
            
        Returns:
            ID of the saved state record
        """
        try:
            # Generate a unique ID for this state
            state_id = str(uuid.uuid4())
            
            # Prepare the state record
            state_record = {
                "id": state_id,
                "session_id": session_id,
                "state_data": state,
                "checkpoint_name": checkpoint_name,
                "created_at": datetime.now().isoformat(),
                "is_checkpoint": checkpoint_name is not None
            }
            
            # Serialize the state to JSON (ensuring datetime objects are properly converted)
            serialized_state = json.dumps(state_record, default=self._serialize_for_json)
            
            # Insert state into the database
            await self.db.execute(
                text("""
                INSERT INTO orchestration_state 
                (id, session_id, state_data, checkpoint_name, created_at, is_checkpoint)
                VALUES (:id, :session_id, :state_data, :checkpoint_name, :created_at, :is_checkpoint)
                """),
                {
                    "id": state_id,
                    "session_id": session_id,
                    "state_data": serialized_state,
                    "checkpoint_name": checkpoint_name,
                    "created_at": datetime.now(),
                    "is_checkpoint": checkpoint_name is not None
                }
            )
            
            # Commit the transaction
            await self.db.commit()
            
            logger.info(f"Saved state {state_id} for session {session_id}" + 
                        (f" with checkpoint '{checkpoint_name}'" if checkpoint_name else ""))
            
            return state_id
        
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}", exc_info=True)
            # Rollback the transaction on error
            await self.db.rollback()
            raise
    
    async def load_state(self, session_id: str, state_id: Optional[str] = None) -> Optional[StateType]:
        """
        Load state from the database.
        
        Args:
            session_id: Session ID to load state for
            state_id: Optional specific state ID to load
            
        Returns:
            The loaded state, or None if not found
        """
        try:
            if state_id:
                # Load specific state by ID
                query = text("""
                SELECT state_data
                FROM orchestration_state
                WHERE id = :state_id AND session_id = :session_id
                """)
                params = {"state_id": state_id, "session_id": session_id}
            else:
                # Load the latest state for the session
                query = text("""
                SELECT state_data
                FROM orchestration_state
                WHERE session_id = :session_id
                ORDER BY created_at DESC
                LIMIT 1
                """)
                params = {"session_id": session_id}
            
            # Execute the query
            result = await self.db.execute(query, params)
            row = result.first()
            
            if not row:
                logger.warning(f"No state found for session {session_id}" + 
                             (f" and state ID {state_id}" if state_id else ""))
                return None
            
            # Parse the state data from JSON
            state_record = json.loads(row[0])
            
            # Extract and deserialize the state
            state_data = state_record.get("state_data", {})
            
            # Convert any serialized timestamps back to datetime
            state_data = self._deserialize_from_json(state_data)
            
            logger.info(f"Loaded state for session {session_id}" + 
                      (f" with ID {state_id}" if state_id else ""))
            
            return cast(StateType, state_data)
            
        except Exception as e:
            logger.error(f"Error loading state: {str(e)}", exc_info=True)
            return None
    
    async def create_checkpoint(
        self, 
        state: StateType, 
        session_id: str,
        checkpoint_name: str
    ) -> str:
        """
        Create a named checkpoint that can be rolled back to later.
        
        Args:
            state: The state to checkpoint
            session_id: The session ID to associate with the checkpoint
            checkpoint_name: Name for the checkpoint
            
        Returns:
            ID of the checkpoint
        """
        checkpoint_id = await self.save_state(
            state=state,
            session_id=session_id,
            checkpoint_name=checkpoint_name
        )
        
        # Limit the number of checkpoints per session
        await self._clean_old_checkpoints(session_id)
        
        return checkpoint_id
    
    async def rollback_to_checkpoint(
        self, 
        session_id: str,
        checkpoint_name: Optional[str] = None
    ) -> Optional[StateType]:
        """
        Roll back to a previous checkpoint.
        
        Args:
            session_id: Session ID to roll back
            checkpoint_name: Name of the checkpoint to roll back to,
                             or None for the most recent checkpoint
            
        Returns:
            The state at the checkpoint, or None if not found
        """
        try:
            # Load the checkpoint
            if checkpoint_name:
                query = text("""
                SELECT state_data
                FROM orchestration_state
                WHERE session_id = :session_id 
                AND checkpoint_name = :checkpoint_name
                AND is_checkpoint = true
                ORDER BY created_at DESC
                LIMIT 1
                """)
                params = {"session_id": session_id, "checkpoint_name": checkpoint_name}
            else:
                query = text("""
                SELECT state_data
                FROM orchestration_state
                WHERE session_id = :session_id 
                AND is_checkpoint = true
                ORDER BY created_at DESC
                LIMIT 1
                """)
                params = {"session_id": session_id}
            
            # Execute the query
            result = await self.db.execute(query, params)
            row = result.first()
            
            if not row:
                logger.warning(f"No checkpoint found for session {session_id}" + 
                             (f" with name '{checkpoint_name}'" if checkpoint_name else ""))
                return None
            
            # Parse the state data from JSON
            state_record = json.loads(row[0])
            
            # Extract and deserialize the state
            state_data = state_record.get("state_data", {})
            
            # Convert any serialized timestamps back to datetime
            state_data = self._deserialize_from_json(state_data)
            
            logger.info(f"Rolled back to checkpoint for session {session_id}" + 
                      (f" with name '{checkpoint_name}'" if checkpoint_name else ""))
            
            return cast(StateType, state_data)
            
        except Exception as e:
            logger.error(f"Error rolling back to checkpoint: {str(e)}", exc_info=True)
            return None
    
    async def list_checkpoints(self, session_id: str) -> List[Dict[str, Any]]:
        """
        List available checkpoints for a session.
        
        Args:
            session_id: Session ID to list checkpoints for
            
        Returns:
            List of checkpoint information dictionaries
        """
        try:
            query = text("""
            SELECT id, checkpoint_name, created_at
            FROM orchestration_state
            WHERE session_id = :session_id AND is_checkpoint = true
            ORDER BY created_at DESC
            """)
            
            # Execute the query
            result = await self.db.execute(query, {"session_id": session_id})
            
            # Convert rows to dictionaries
            checkpoints = []
            for row in result:
                checkpoints.append({
                    "id": row[0],
                    "name": row[1],
                    "created_at": row[2].isoformat() if isinstance(row[2], datetime) else row[2]
                })
            
            return checkpoints
            
        except Exception as e:
            logger.error(f"Error listing checkpoints: {str(e)}", exc_info=True)
            return []
    
    async def clean_expired_states(self, days: int = STATE_EXPIRATION_DAYS) -> int:
        """
        Clean up expired state records.
        
        Args:
            days: Number of days to keep state records
            
        Returns:
            Number of records deleted
        """
        try:
            # Calculate the cutoff date
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Delete expired records
            query = text("""
            DELETE FROM orchestration_state
            WHERE created_at < :cutoff_date
            """)
            
            # Execute the query
            result = await self.db.execute(query, {"cutoff_date": cutoff_date})
            
            # Get the number of deleted rows if possible
            deleted_count = result.rowcount if hasattr(result, 'rowcount') else -1
            
            # Commit the transaction
            await self.db.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired state records")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning expired states: {str(e)}", exc_info=True)
            await self.db.rollback()
            return 0
    
    async def _clean_old_checkpoints(self, session_id: str) -> None:
        """
        Clean up old checkpoints, keeping only the most recent ones.
        
        Args:
            session_id: Session ID to clean checkpoints for
        """
        try:
            # Get the IDs of checkpoints to keep
            query = text(f"""
            SELECT id FROM orchestration_state
            WHERE session_id = :session_id AND is_checkpoint = true
            ORDER BY created_at DESC
            LIMIT {MAX_CHECKPOINTS}
            """)
            
            # Execute the query
            result = await self.db.execute(query, {"session_id": session_id})
            
            # Extract the IDs to keep
            ids_to_keep = [row[0] for row in result]
            
            if not ids_to_keep:
                return
            
            # Delete checkpoints that are not in the ids_to_keep list
            delete_query = text("""
            DELETE FROM orchestration_state
            WHERE session_id = :session_id 
            AND is_checkpoint = true
            AND id NOT IN :ids_to_keep
            """)
            
            # Execute the delete query
            await self.db.execute(
                delete_query, 
                {"session_id": session_id, "ids_to_keep": tuple(ids_to_keep)}
            )
            
            # Commit the transaction
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error cleaning old checkpoints: {str(e)}", exc_info=True)
            await self.db.rollback()
    
    def _serialize_for_json(self, obj: Any) -> Any:
        """
        Serialize objects for JSON conversion.
        
        Args:
            obj: The object to serialize
            
        Returns:
            JSON-serializable representation of the object
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        
        # Add more custom serialization as needed
        
        raise TypeError(f"Type {type(obj)} not serializable")
    
    def _deserialize_from_json(self, data: Any) -> Any:
        """
        Deserialize objects from JSON.
        
        Args:
            data: The data to deserialize
            
        Returns:
            Deserialized representation of the data
        """
        if isinstance(data, dict):
            # Recursively process dictionary values
            return {k: self._deserialize_from_json(v) for k, v in data.items()}
        
        if isinstance(data, list):
            # Recursively process list items
            return [self._deserialize_from_json(item) for item in data]
        
        if isinstance(data, str) and len(data) > 20:
            # Try to parse ISO datetime strings
            try:
                if 'T' in data and ('+' in data or 'Z' in data or '-' in data[10:]):
                    # This looks like an ISO format datetime
                    return datetime.fromisoformat(data.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                # Not a datetime string
                pass
        
        return data


# Functions for use in node functions

async def persist_state(
    state: OrchestrationState, 
    session_id: str,
    db: AsyncSession,
    checkpoint_name: Optional[str] = None
) -> OrchestrationState:
    """
    Persist the current state to the database.
    
    Args:
        state: Current orchestration state
        session_id: Session identifier
        db: Database session
        checkpoint_name: Optional name for the checkpoint
        
    Returns:
        Updated orchestration state
    """
    try:
        # Make sure we have a session ID
        if not session_id:
            session_id = state.get("conversation", {}).get("session_id")
            if not session_id:
                logger.warning("No session ID provided for state persistence")
                return state
        
        # Create state persistence manager
        manager = StatePersistenceManager(db)
        
        # Save the state
        state_id = await manager.save_state(state, session_id, checkpoint_name)
        
        # Update the state with the state ID
        execution = {**state.get("execution", {})}
        execution["last_persisted_state_id"] = state_id
        execution["last_persisted_at"] = datetime.now().isoformat()
        
        # Create a new state to avoid modifying the input
        new_state = {**state}
        new_state["execution"] = execution
        
        return new_state
    
    except Exception as e:
        logger.error(f"Error persisting state: {str(e)}", exc_info=True)
        
        # Record the error but continue execution
        error_state = record_error(
            state, 
            "persist_state", 
            e,
            error_type=ErrorType.STATE_PERSISTENCE_ERROR
        )
        
        return error_state


async def recover_state(
    session_id: str,
    db: AsyncSession,
    state_id: Optional[str] = None,
    checkpoint_name: Optional[str] = None
) -> Optional[OrchestrationState]:
    """
    Recover state from the database.
    
    Args:
        session_id: Session identifier
        db: Database session
        state_id: Optional specific state ID to recover
        checkpoint_name: Optional checkpoint name to recover from
        
    Returns:
        Recovered orchestration state, or None if not found
    """
    try:
        # Create state persistence manager
        manager = StatePersistenceManager(db)
        
        if checkpoint_name:
            # Recover from a named checkpoint
            return await manager.rollback_to_checkpoint(session_id, checkpoint_name)
        else:
            # Recover the latest state or a specific state ID
            return await manager.load_state(session_id, state_id)
    
    except Exception as e:
        logger.error(f"Error recovering state: {str(e)}", exc_info=True)
        return None


async def create_state_checkpoint(
    state: OrchestrationState,
    session_id: str,
    checkpoint_name: str,
    db: AsyncSession
) -> OrchestrationState:
    """
    Create a named checkpoint for the current state.
    
    Args:
        state: Current orchestration state
        session_id: Session identifier
        checkpoint_name: Name for the checkpoint
        db: Database session
        
    Returns:
        Updated orchestration state
    """
    try:
        # Make sure we have a session ID
        if not session_id:
            session_id = state.get("conversation", {}).get("session_id")
            if not session_id:
                logger.warning("No session ID provided for checkpoint creation")
                return state
        
        # Create state persistence manager
        manager = StatePersistenceManager(db)
        
        # Create the checkpoint
        checkpoint_id = await manager.create_checkpoint(state, session_id, checkpoint_name)
        
        # Update the state with the checkpoint information
        execution = {**state.get("execution", {})}
        checkpoints = {**execution.get("checkpoints", {})}
        checkpoints[checkpoint_name] = {
            "id": checkpoint_id,
            "created_at": datetime.now().isoformat()
        }
        execution["checkpoints"] = checkpoints
        
        # Create a new state to avoid modifying the input
        new_state = {**state}
        new_state["execution"] = execution
        
        return new_state
    
    except Exception as e:
        logger.error(f"Error creating checkpoint: {str(e)}", exc_info=True)
        
        # Record the error but continue execution
        error_state = record_error(
            state, 
            "create_state_checkpoint", 
            e,
            error_type=ErrorType.STATE_PERSISTENCE_ERROR
        )
        
        return error_state


async def create_db_tables(db: AsyncSession) -> None:
    """
    Create the necessary database tables for state persistence.
    
    Args:
        db: Database session
    """
    try:
        # Execute raw SQL to create the state table if it doesn't exist
        query = """
        CREATE TABLE IF NOT EXISTS orchestration_state (
            id VARCHAR(36) PRIMARY KEY,
            session_id VARCHAR(36) NOT NULL,
            state_data JSONB NOT NULL,
            checkpoint_name VARCHAR(255) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            is_checkpoint BOOLEAN NOT NULL DEFAULT FALSE
        );
        
        -- Create indexes for efficient querying
        CREATE INDEX IF NOT EXISTS orchestration_state_session_id_idx ON orchestration_state(session_id);
        CREATE INDEX IF NOT EXISTS orchestration_state_checkpoint_idx ON orchestration_state(session_id, is_checkpoint) WHERE is_checkpoint = TRUE;
        CREATE INDEX IF NOT EXISTS orchestration_state_created_at_idx ON orchestration_state(created_at);
        """
        
        await db.execute(text(query))
        await db.commit()
        
        logger.info("Created orchestration_state table")
    
    except Exception as e:
        logger.error(f"Error creating state persistence tables: {str(e)}", exc_info=True)
        await db.rollback()
        raise