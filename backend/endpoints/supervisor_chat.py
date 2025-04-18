"""
Supervisor Chat Endpoints for Staples Brain.

This module provides API endpoints for interacting with the SupervisorBrainService,
which uses a LangGraph Supervisor for agent orchestration.
"""
import logging
from typing import Dict, List, Optional, Any, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.supervisor_brain_service import SupervisorBrainService
from backend.database.db import get_db
from backend.config.config import get_config, Config

# Configure logging first
logger = logging.getLogger(__name__)

# Remove backend.dependencies import to avoid circular imports
# We're using a temporary local function instead

# Temporary singleton instance for development
_supervisor_brain_service = None

async def get_temporary_supervisor_brain_service(
    db: AsyncSession = Depends(get_db)
) -> SupervisorBrainService:
    """
    Temporary replacement for the dependency from backend.dependencies.
    This avoids circular imports while we work on restructuring the dependencies.
    
    Args:
        db: Database session
        
    Returns:
        SupervisorBrainService instance (minimal implementation)
    """
    global _supervisor_brain_service
    
    if _supervisor_brain_service is None:
        logger.info("Creating a temporary SupervisorBrainService instance")
        config = get_config()
        
        # Create minimal version without all dependencies
        _supervisor_brain_service = SupervisorBrainService(
            db_session=db,
            config=config,
            memory_service=None,  # Will be properly initialized in future
            agent_factory=None,   # Will be properly initialized in future
            supervisor_factory=None  # Will be properly initialized in future
        )
    
    return _supervisor_brain_service

# Set up router
router = APIRouter(
    prefix="/api/v1/supervisor-chat",
    tags=["supervisor-chat"],
    responses={404: {"description": "Not found"}},
)


class SupervisorChatRequest(BaseModel):
    """Request model for supervisor chat endpoint."""
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class SupervisorChatResponse(BaseModel):
    """Response model for supervisor chat endpoint."""
    session_id: str = Field(..., description="Session identifier")
    response: str = Field(..., description="Assistant response")
    success: bool = Field(..., description="Whether the request was successful")
    agent: Dict[str, Any] = Field(..., description="Agent information")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error: Optional[str] = Field(None, description="Error message if applicable")


@router.post("/chat", response_model=SupervisorChatResponse)
async def supervisor_chat(
    request: SupervisorChatRequest,
    brain_service: SupervisorBrainService = Depends(get_temporary_supervisor_brain_service)
):
    """
    Process a chat message using the supervisor-based brain service.
    
    Args:
        request: Chat request
        brain_service: Supervisor brain service
        
    Returns:
        Chat response
    """
    return await _process_supervisor_chat_request(request, brain_service)


async def _process_supervisor_chat_request(
    request: SupervisorChatRequest,
    brain_service: SupervisorBrainService
) -> SupervisorChatResponse:
    """
    Process a chat request using the supervisor brain service.
    
    Args:
        request: Chat request
        brain_service: Supervisor brain service
        
    Returns:
        Chat response
    
    Raises:
        HTTPException: If the request processing fails
    """
    try:
        # Process the message using the supervisor brain service
        result = await brain_service.process_message(
            message=request.message,
            session_id=request.session_id,
            context=request.context
        )
        
        # Construct response
        return SupervisorChatResponse(
            session_id=result.get("session_id", request.session_id),
            response=result.get("response", ""),
            success=result.get("success", False),
            agent=result.get("agent", {"id": "", "name": "", "confidence": 0.0}),
            metadata=result.get("metadata", {}),
            error=result.get("error")
        )
    
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat request: {str(e)}"
        )