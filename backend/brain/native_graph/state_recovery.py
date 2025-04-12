"""
State recovery and retry mechanisms for Staples Brain.

This module provides enhanced error handling and retry logic for state persistence
operations to ensure robustness in the face of database connectivity issues or
temporary failures.
"""
import logging
import asyncio
import time
import random
from typing import Any, Dict, Optional, Callable, TypeVar, Awaitable, List
from datetime import datetime

from backend.brain.native_graph.error_handling import ErrorType, record_error
from backend.brain.native_graph.state_definitions import OrchestrationState

logger = logging.getLogger(__name__)

# Define type variables for generic functions
T = TypeVar('T')
StateType = Dict[str, Any]

# Configuration for retry behavior
MAX_RETRIES = 3
BASE_DELAY = 0.5  # Base delay in seconds
MAX_DELAY = 5.0   # Maximum delay in seconds
JITTER = 0.2      # Random jitter factor to add to delay


async def with_retry(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY,
    max_delay: float = MAX_DELAY,
    jitter: float = JITTER,
    **kwargs: Any
) -> T:
    """
    Execute an async function with exponential backoff retry logic.
    
    Args:
        func: Async function to execute
        *args: Positional arguments to pass to func
        retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Random jitter factor to add to delay
        **kwargs: Keyword arguments to pass to func
        
    Returns:
        Result of the function execution
        
    Raises:
        Exception: If all retry attempts fail
    """
    attempt = 0
    last_exception = None
    
    while attempt <= retries:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            attempt += 1
            last_exception = e
            
            if attempt > retries:
                logger.error(f"All {retries} retry attempts failed: {str(e)}", exc_info=True)
                raise
            
            # Calculate exponential backoff with jitter
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            jitter_amount = random.uniform(-jitter * delay, jitter * delay)
            delay = max(0, delay + jitter_amount)
            
            logger.warning(
                f"Operation failed (attempt {attempt}/{retries}), "
                f"retrying in {delay:.2f} seconds: {str(e)}"
            )
            
            await asyncio.sleep(delay)
    
    # This should never be reached due to the if attempt > retries check above,
    # but we include it to satisfy type checking
    if last_exception:
        raise last_exception
    return await func(*args, **kwargs)


async def resilient_persist_state(
    state: OrchestrationState,
    session_id: str,
    db,
    checkpoint_name: Optional[str] = None
) -> OrchestrationState:
    """
    Persist state with retry logic and graceful degradation.
    
    Args:
        state: Current orchestration state
        session_id: Session identifier
        db: Database session
        checkpoint_name: Optional name for the checkpoint
        
    Returns:
        Updated orchestration state
    """
    from backend.brain.native_graph.state_persistence import persist_state
    
    try:
        # Attempt to persist state with retry logic
        return await with_retry(
            persist_state,
            state=state,
            session_id=session_id,
            db=db,
            checkpoint_name=checkpoint_name
        )
    except Exception as e:
        logger.error(f"Failed to persist state after retries: {str(e)}", exc_info=True)
        
        # Record the error but continue execution with graceful degradation
        error_state = record_error(
            state, 
            "resilient_persist_state", 
            e,
            error_type=ErrorType.STATE_PERSISTENCE_ERROR
        )
        
        # Add information about the failed persistence
        execution = error_state.get("execution", {})
        persistence_errors = execution.get("persistence_errors", [])
        persistence_errors.append({
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "session_id": session_id
        })
        execution["persistence_errors"] = persistence_errors
        error_state["execution"] = execution
        
        # Mark state as dirty (needs to be persisted when connection is restored)
        error_state["execution"]["state_dirty"] = True
        
        return error_state


async def resilient_recover_state(
    session_id: str,
    db,
    state_id: Optional[str] = None,
    checkpoint_name: Optional[str] = None
) -> Optional[OrchestrationState]:
    """
    Recover state with retry logic and graceful degradation.
    
    Args:
        session_id: Session identifier
        db: Database session
        state_id: Optional specific state ID to recover
        checkpoint_name: Optional checkpoint name to recover from
        
    Returns:
        Recovered orchestration state, or None if not found
    """
    from backend.brain.native_graph.state_persistence import recover_state
    
    try:
        # Attempt to recover state with retry logic
        return await with_retry(
            recover_state,
            session_id=session_id,
            db=db,
            state_id=state_id,
            checkpoint_name=checkpoint_name
        )
    except Exception as e:
        logger.error(f"Failed to recover state after retries: {str(e)}", exc_info=True)
        
        # In case of failure, return None and let the caller create a new state
        return None


async def resilient_create_checkpoint(
    state: OrchestrationState,
    session_id: str,
    checkpoint_name: str,
    db
) -> OrchestrationState:
    """
    Create a checkpoint with retry logic and graceful degradation.
    
    Args:
        state: Current orchestration state
        session_id: Session identifier
        checkpoint_name: Name for the checkpoint
        db: Database session
        
    Returns:
        Updated orchestration state
    """
    from backend.brain.native_graph.state_persistence import create_state_checkpoint
    
    try:
        # Attempt to create checkpoint with retry logic
        return await with_retry(
            create_state_checkpoint,
            state=state,
            session_id=session_id,
            checkpoint_name=checkpoint_name,
            db=db
        )
    except Exception as e:
        logger.error(f"Failed to create checkpoint after retries: {str(e)}", exc_info=True)
        
        # Record the error but continue execution with graceful degradation
        error_state = record_error(
            state, 
            "resilient_create_checkpoint", 
            e,
            error_type=ErrorType.STATE_PERSISTENCE_ERROR
        )
        
        # Add information about the failed checkpoint creation
        execution = error_state.get("execution", {})
        checkpoint_errors = execution.get("checkpoint_errors", [])
        checkpoint_errors.append({
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "session_id": session_id,
            "checkpoint_name": checkpoint_name
        })
        execution["checkpoint_errors"] = checkpoint_errors
        error_state["execution"] = execution
        
        # Queue the checkpoint for later creation when connection is restored
        pending_checkpoints = error_state.get("execution", {}).get("pending_checkpoints", [])
        pending_checkpoints.append({
            "checkpoint_name": checkpoint_name,
            "requested_at": datetime.now().isoformat()
        })
        error_state["execution"]["pending_checkpoints"] = pending_checkpoints
        
        return error_state


async def process_pending_operations(
    state: OrchestrationState,
    session_id: str,
    db
) -> OrchestrationState:
    """
    Process any pending persistence operations that failed previously.
    
    Args:
        state: Current orchestration state
        session_id: Session identifier
        db: Database session
        
    Returns:
        Updated orchestration state
    """
    updated_state = state.copy()
    execution = updated_state.get("execution", {})
    
    # Check if state is dirty and needs to be persisted
    if execution.get("state_dirty", False):
        # First check if DB connection is available
        db_available = await check_db_connection(db)
        if not db_available:
            logger.warning("Database connection unavailable, skipping pending state persistence")
        else:
            try:
                logger.info(f"Processing pending state persistence for session {session_id}")
                from backend.brain.native_graph.state_persistence import persist_state
                
                # Attempt to persist the state with single retry
                try:
                    await persist_state(updated_state, session_id, db)
                    
                    # Mark state as clean
                    execution["state_dirty"] = False
                    updated_state["execution"] = execution
                    
                    logger.info(f"Successfully processed pending state persistence for session {session_id}")
                except Exception as first_error:
                    # One retry after a short delay
                    logger.warning(f"First attempt to process pending state failed: {str(first_error)}, retrying once...")
                    await asyncio.sleep(0.5)
                    await persist_state(updated_state, session_id, db)
                    
                    # Mark state as clean if second attempt succeeds
                    execution["state_dirty"] = False
                    updated_state["execution"] = execution
                    
                    logger.info(f"Successfully processed pending state persistence on retry for session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to process pending state persistence: {str(e)}", exc_info=True)
    
    # Process any pending checkpoints
    pending_checkpoints = execution.get("pending_checkpoints", [])
    if pending_checkpoints:
        # First check if DB connection is available
        db_available = await check_db_connection(db)
        if not db_available:
            logger.warning("Database connection unavailable, skipping pending checkpoints")
        else:
            remaining_checkpoints = []
            
            for checkpoint in pending_checkpoints:
                checkpoint_name = checkpoint.get("checkpoint_name")
                if not checkpoint_name:
                    continue
                    
                try:
                    logger.info(f"Processing pending checkpoint '{checkpoint_name}' for session {session_id}")
                    from backend.brain.native_graph.state_persistence import create_state_checkpoint
                    
                    # Attempt to create the checkpoint with single retry
                    try:
                        await create_state_checkpoint(updated_state, session_id, checkpoint_name, db)
                        logger.info(f"Successfully processed pending checkpoint '{checkpoint_name}' for session {session_id}")
                    except Exception as first_error:
                        # One retry after a short delay
                        logger.warning(f"First attempt to process checkpoint failed: {str(first_error)}, retrying once...")
                        await asyncio.sleep(0.5)
                        await create_state_checkpoint(updated_state, session_id, checkpoint_name, db)
                        logger.info(f"Successfully processed pending checkpoint '{checkpoint_name}' on retry for session {session_id}")
                except Exception as e:
                    logger.warning(f"Failed to process pending checkpoint '{checkpoint_name}': {str(e)}", exc_info=True)
                    # Add retry count or last attempt timestamp to help with cleanup later
                    checkpoint["last_attempt"] = datetime.now().isoformat()
                    checkpoint["retry_count"] = checkpoint.get("retry_count", 0) + 1
                    remaining_checkpoints.append(checkpoint)
            
            # Update pending checkpoints list
            execution["pending_checkpoints"] = remaining_checkpoints
            updated_state["execution"] = execution
    
    return updated_state


async def check_db_connection(db) -> bool:
    """
    Check if the database connection is working.
    
    Args:
        db: Database session
        
    Returns:
        True if connection is working, False otherwise
    """
    try:
        # Try a simple query to check if the connection works
        query = "SELECT 1"
        await db.execute(query)
        return True
    except Exception as e:
        logger.warning(f"Database connection check failed: {str(e)}")
        return False


async def resilient_rollback_to_checkpoint(
    session_id: str,
    db,
    checkpoint_name: Optional[str] = None
) -> Optional[OrchestrationState]:
    """
    Roll back to a checkpoint with retry logic and graceful degradation.
    
    Args:
        session_id: Session identifier
        db: Database session
        checkpoint_name: Optional checkpoint name to roll back to
        
    Returns:
        Rolled back orchestration state, or None if not found or errors occur
    """
    from backend.brain.native_graph.state_persistence import StatePersistenceManager
    
    try:
        # Create a manager instance
        manager = StatePersistenceManager(db)
        
        # Attempt to roll back with retry logic
        return await with_retry(
            manager.rollback_to_checkpoint,
            session_id=session_id,
            checkpoint_name=checkpoint_name
        )
    except Exception as e:
        logger.error(f"Failed to roll back to checkpoint after retries: {str(e)}", exc_info=True)
        # In case of failure, return None
        return None


async def get_most_recent_state(
    session_id: str,
    db,
    max_retries: int = 2
) -> Optional[OrchestrationState]:
    """
    Get the most recent state for a session, handling possible errors.
    
    Args:
        session_id: Session identifier
        db: Database session
        max_retries: Maximum number of retry attempts
        
    Returns:
        Most recent state or None if not found or errors occur
    """
    # First check if DB connection is working
    is_connected = await check_db_connection(db)
    if not is_connected:
        logger.warning(f"Database connection unavailable, cannot retrieve state for session {session_id}")
        return None
    
    # Try to recover state with retry logic
    return await resilient_recover_state(session_id, db)