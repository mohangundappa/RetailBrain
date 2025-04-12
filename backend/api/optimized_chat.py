"""
API routes for optimized chat functionality.
This module provides FastAPI routes for using the optimized brain service.
"""
import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.services.optimized_brain_service import OptimizedBrainService
from backend.services.optimized_dependencies import get_optimized_brain_service

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/optimized", tags=["optimized"])


class OptimizedChatRequest(BaseModel):
    """Request model for optimized chat"""
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class OptimizedChatResponse(BaseModel):
    """Response model for optimized chat"""
    success: bool = Field(..., description="Whether the request was successful")
    response: str = Field(..., description="Agent response")
    agent: Optional[str] = Field(None, description="Name of the agent that handled the request")
    agent_id: Optional[str] = Field(None, description="ID of the agent that handled the request")
    confidence: Optional[float] = Field(None, description="Confidence of the agent selection")
    entities: Optional[Dict[str, Any]] = Field(None, description="Extracted entities")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error: Optional[str] = Field(None, description="Error message if unsuccessful")


@router.post("/chat", response_model=OptimizedChatResponse)
async def optimized_chat(
    request: OptimizedChatRequest,
    brain_service: OptimizedBrainService = Depends(get_optimized_brain_service)
):
    """
    Process a chat message using the optimized brain service.
    
    Args:
        request: Chat request
        brain_service: Optimized brain service
        
    Returns:
        Chat response
    """
    logger.info(f"Optimized chat request: {request.message} (session: {request.session_id})")
    
    result = await brain_service.process_message(
        message=request.message,
        session_id=request.session_id,
        context=request.context
    )
    
    # Construct response - now handling both agent and agent_name fields
    # as we're in a transition period between the old and new implementations
    response = OptimizedChatResponse(
        success=result.get("success", False),
        response=result.get("response", "No response generated" if not result.get("response") else result.get("response")),
        agent=result.get("agent") or result.get("agent_name"),
        agent_id=result.get("agent_id"),
        confidence=result.get("confidence") or result.get("selection_confidence"),
        entities=result.get("entities"),
        metadata={
            "selection_time": result.get("selection_time"),
            "optimized_selection": True,
            "execution_time": result.get("execution_time")
        },
        error=result.get("error")
    )
    
    return response


class DirectAgentRequest(BaseModel):
    """Request model for direct agent execution"""
    agent_id: str = Field(..., description="ID of the agent to execute")
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


@router.post("/execute-agent", response_model=OptimizedChatResponse)
async def execute_agent(
    request: DirectAgentRequest,
    brain_service: OptimizedBrainService = Depends(get_optimized_brain_service)
):
    """
    Execute a specific agent directly.
    
    Args:
        request: Agent execution request
        brain_service: Optimized brain service
        
    Returns:
        Execution response
    """
    logger.info(f"Direct agent execution: {request.agent_id} (message: {request.message})")
    
    result = await brain_service.execute_agent(
        agent_id=request.agent_id,
        message=request.message,
        session_id=request.session_id,
        context=request.context
    )
    
    # Construct response - now handling both agent and agent_name fields
    # as we're in a transition period between the old and new implementations
    response = OptimizedChatResponse(
        success=result.get("success", False),
        response=result.get("response", "No response generated" if not result.get("response") else result.get("response")),
        agent=result.get("agent") or result.get("agent_name"),
        agent_id=request.agent_id,  # Use the requested agent ID
        confidence=1.0,  # Direct execution, so confidence is 1.0
        entities=result.get("entities"),
        metadata={
            "direct_execution": True,
            "execution_time": result.get("execution_time")
        },
        error=result.get("error")
    )
    
    return response