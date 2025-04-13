"""
State Management API for Staples Brain.

This module provides API endpoints for managing conversation state, checkpoints,
and rollback functionality.
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.db import get_db
from backend.orchestration.state.recovery import (
    resilient_create_checkpoint,
    resilient_persist_state,
    resilient_recover_state,
    resilient_rollback_to_checkpoint,
    get_most_recent_state,
    check_db_connection,
    process_pending_operations
)
from backend.orchestration.state.state_persistence_manager import (
    StatePersistenceManager,
    ErrorType
)

logger = logging.getLogger(__name__)

# Create router
state_router = APIRouter(prefix="/state", tags=["state"])


# API Models
class CheckpointResponse(BaseModel):
    """Checkpoint information response model"""
    id: str = Field(..., description="Checkpoint ID")
    name: str = Field(..., description="Checkpoint name")
    created_at: str = Field(..., description="Checkpoint creation timestamp")


class CheckpointListResponse(BaseModel):
    """Response model for listing checkpoints"""
    success: bool = Field(True, description="Whether the request was successful")
    checkpoints: List[CheckpointResponse] = Field([], description="List of checkpoints")
    count: int = Field(0, description="Number of checkpoints")
    session_id: str = Field(..., description="Session ID")
    error: Optional[str] = Field(None, description="Error message if applicable")


class CreateCheckpointRequest(BaseModel):
    """Request model for creating a checkpoint"""
    checkpoint_name: str = Field(..., description="Name for the checkpoint")
    session_id: str = Field(..., description="Session ID to create checkpoint for")


class CreateCheckpointResponse(BaseModel):
    """Response model for creating a checkpoint"""
    success: bool = Field(True, description="Whether the request was successful")
    checkpoint_id: Optional[str] = Field(None, description="ID of the created checkpoint")
    checkpoint_name: str = Field(..., description="Name of the checkpoint")
    session_id: str = Field(..., description="Session ID")
    created_at: str = Field(..., description="Creation timestamp")
    error: Optional[str] = Field(None, description="Error message if applicable")


class RollbackRequest(BaseModel):
    """Request model for rollback to checkpoint"""
    session_id: str = Field(..., description="Session ID to roll back")
    checkpoint_name: Optional[str] = Field(None, description="Name of checkpoint to roll back to (uses latest if not specified)")


class RollbackResponse(BaseModel):
    """Response model for rollback operation"""
    success: bool = Field(True, description="Whether the rollback was successful")
    session_id: str = Field(..., description="Session ID")
    checkpoint_name: Optional[str] = Field(None, description="Name of the checkpoint rolled back to")
    rollback_time: str = Field(..., description="Timestamp of rollback operation")
    error: Optional[str] = Field(None, description="Error message if applicable")


class SessionResponse(BaseModel):
    """Response model for session information"""
    session_id: str = Field(..., description="Session ID")
    state_count: int = Field(0, description="Number of state records")
    checkpoint_count: int = Field(0, description="Number of checkpoints")
    latest_update: Optional[str] = Field(None, description="Timestamp of latest update")
    error: Optional[str] = Field(None, description="Error message if applicable")


class SessionListResponse(BaseModel):
    """Response model for listing sessions"""
    success: bool = Field(True, description="Whether the request was successful")
    sessions: List[str] = Field([], description="List of session IDs")
    count: int = Field(0, description="Number of sessions")
    error: Optional[str] = Field(None, description="Error message if applicable")


# Endpoints
@state_router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, description="Maximum number of sessions to return")
):
    """
    List active conversation sessions.
    
    Args:
        db: Database session
        limit: Maximum number of sessions to return
        
    Returns:
        List of session IDs
    """
    try:
        # Create state persistence manager
        manager = StatePersistenceManager(db)
        
        # Get active sessions from database
        query = """
        SELECT DISTINCT session_id FROM orchestration_state
        ORDER BY MAX(created_at) DESC
        LIMIT :limit
        """
        
        result = await db.execute(query, {"limit": limit})
        sessions = [row[0] for row in result]
        
        return SessionListResponse(
            success=True,
            sessions=sessions,
            count=len(sessions)
        )
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}", exc_info=True)
        return SessionListResponse(
            success=False,
            error=f"Failed to list sessions: {str(e)}"
        )


@state_router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session_info(
    session_id: str = Path(..., description="Session ID to get information for"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get information about a specific conversation session.
    
    Args:
        session_id: Session ID to get information for
        db: Database session
        
    Returns:
        Session information
    """
    try:
        # Create state persistence manager
        manager = StatePersistenceManager(db)
        
        # Get state count
        state_count_query = """
        SELECT COUNT(*) FROM orchestration_state
        WHERE session_id = :session_id
        """
        state_count_result = await db.execute(state_count_query, {"session_id": session_id})
        state_count = state_count_result.scalar_one_or_none() or 0
        
        # Get checkpoint count
        checkpoint_count_query = """
        SELECT COUNT(*) FROM orchestration_state
        WHERE session_id = :session_id AND is_checkpoint = true
        """
        checkpoint_count_result = await db.execute(checkpoint_count_query, {"session_id": session_id})
        checkpoint_count = checkpoint_count_result.scalar_one_or_none() or 0
        
        # Get latest update timestamp
        latest_update_query = """
        SELECT MAX(created_at) FROM orchestration_state
        WHERE session_id = :session_id
        """
        latest_update_result = await db.execute(latest_update_query, {"session_id": session_id})
        latest_update = latest_update_result.scalar_one_or_none()
        
        # Format the latest update timestamp
        if latest_update:
            latest_update = latest_update.isoformat() if isinstance(latest_update, datetime) else str(latest_update)
        
        return SessionResponse(
            session_id=session_id,
            state_count=state_count,
            checkpoint_count=checkpoint_count,
            latest_update=latest_update
        )
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}", exc_info=True)
        return SessionResponse(
            session_id=session_id,
            error=f"Failed to get session information: {str(e)}"
        )


@state_router.get("/checkpoints/{session_id}", response_model=CheckpointListResponse)
async def list_checkpoints(
    session_id: str = Path(..., description="Session ID to list checkpoints for"),
    db: AsyncSession = Depends(get_db)
):
    """
    List checkpoints for a session.
    
    Args:
        session_id: Session ID to list checkpoints for
        db: Database session
        
    Returns:
        List of checkpoints
    """
    try:
        # Create state persistence manager
        manager = StatePersistenceManager(db)
        
        # Get checkpoints from database
        checkpoints = await manager.list_checkpoints(session_id)
        
        # Convert to response model format
        checkpoint_responses = [
            CheckpointResponse(
                id=checkpoint["id"],
                name=checkpoint["name"],
                created_at=checkpoint["created_at"]
            )
            for checkpoint in checkpoints
        ]
        
        return CheckpointListResponse(
            success=True,
            checkpoints=checkpoint_responses,
            count=len(checkpoint_responses),
            session_id=session_id
        )
    except Exception as e:
        logger.error(f"Error listing checkpoints: {str(e)}", exc_info=True)
        return CheckpointListResponse(
            success=False,
            session_id=session_id,
            error=f"Failed to list checkpoints: {str(e)}"
        )


@state_router.post("/checkpoints", response_model=CreateCheckpointResponse)
async def create_checkpoint(
    request: CreateCheckpointRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new named checkpoint for a session.
    
    Args:
        request: Checkpoint creation request
        db: Database session
        
    Returns:
        Result of checkpoint creation
    """
    try:
        # Create state persistence manager
        manager = StatePersistenceManager(db)
        
        # First check database connectivity
        db_available = await check_db_connection(db)
        if not db_available:
            return CreateCheckpointResponse(
                success=False,
                checkpoint_name=request.checkpoint_name,
                session_id=request.session_id,
                created_at=datetime.now().isoformat(),
                error="Database connection unavailable"
            )
            
        # Recover the latest state for the session with resilient function
        state = await get_most_recent_state(request.session_id, db)
        
        if not state:
            return CreateCheckpointResponse(
                success=False,
                checkpoint_name=request.checkpoint_name,
                session_id=request.session_id,
                created_at=datetime.now().isoformat(),
                error="No state found for the session"
            )
        
        # Process any pending operations
        state = await process_pending_operations(state, request.session_id, db)
        
        # Create the checkpoint with resilient function
        updated_state = await resilient_create_checkpoint(
            state=state,
            session_id=request.session_id,
            checkpoint_name=request.checkpoint_name,
            db=db
        )
        
        # Get the checkpoint ID from the state if available
        checkpoint_id = updated_state.get("execution", {}).get("last_checkpoint_id")
        
        return CreateCheckpointResponse(
            success=True,
            checkpoint_id=checkpoint_id,
            checkpoint_name=request.checkpoint_name,
            session_id=request.session_id,
            created_at=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error creating checkpoint: {str(e)}", exc_info=True)
        return CreateCheckpointResponse(
            success=False,
            checkpoint_name=request.checkpoint_name,
            session_id=request.session_id,
            created_at=datetime.now().isoformat(),
            error=f"Failed to create checkpoint: {str(e)}"
        )


@state_router.post("/rollback", response_model=RollbackResponse)
async def rollback_to_checkpoint(
    request: RollbackRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Roll back to a previous checkpoint.
    
    Args:
        request: Rollback request
        db: Database session
        
    Returns:
        Result of rollback operation
    """
    try:
        # First check database connectivity
        db_available = await check_db_connection(db)
        if not db_available:
            return RollbackResponse(
                success=False,
                session_id=request.session_id,
                checkpoint_name=request.checkpoint_name,
                rollback_time=datetime.now().isoformat(),
                error="Database connection unavailable"
            )
        
        # Create state persistence manager (for using specific methods)
        manager = StatePersistenceManager(db)
        
        try:
            # Process any pending operations first
            current_state = await get_most_recent_state(request.session_id, db)
            if current_state:
                await process_pending_operations(current_state, request.session_id, db)
        except Exception as e:
            logger.warning(f"Error processing pending operations before rollback: {str(e)}")
        
        # Roll back to the checkpoint with resilient error handling
        state = await resilient_rollback_to_checkpoint(
            session_id=request.session_id,
            db=db,
            checkpoint_name=request.checkpoint_name
        )
        
        if not state:
            return RollbackResponse(
                success=False,
                session_id=request.session_id,
                checkpoint_name=request.checkpoint_name,
                rollback_time=datetime.now().isoformat(),
                error=f"Failed to roll back: no checkpoint found" + 
                      (f" with name '{request.checkpoint_name}'" if request.checkpoint_name else "")
            )
        
        # Return success response
        return RollbackResponse(
            success=True,
            session_id=request.session_id,
            checkpoint_name=request.checkpoint_name,
            rollback_time=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error rolling back to checkpoint: {str(e)}", exc_info=True)
        return RollbackResponse(
            success=False,
            session_id=request.session_id,
            checkpoint_name=request.checkpoint_name,
            rollback_time=datetime.now().isoformat(),
            error=f"Failed to roll back: {str(e)}"
        )