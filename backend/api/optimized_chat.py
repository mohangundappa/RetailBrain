"""
API routes for chat functionality.
This module provides FastAPI routes for using the brain service with optimized agent selection.
"""
import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.services.optimized_brain_service import OptimizedBrainService
from backend.services.optimized_dependencies import get_optimized_brain_service

logger = logging.getLogger(__name__)

# Create API router
# We have two routers:
# 1. A router with the /optimized prefix for backward compatibility
# 2. A main router with no prefix for the standard API
router = APIRouter(prefix="/optimized", tags=["optimized"])
main_router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat"""
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ChatResponse(BaseModel):
    """Response model for chat"""
    success: bool = Field(..., description="Whether the request was successful")
    response: str = Field(..., description="Agent response")
    agent: Optional[str] = Field(None, description="Name of the agent that handled the request")
    agent_id: Optional[str] = Field(None, description="ID of the agent that handled the request")
    confidence: Optional[float] = Field(None, description="Confidence of the agent selection")
    entities: Optional[Dict[str, Any]] = Field(None, description="Extracted entities")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error: Optional[str] = Field(None, description="Error message if unsuccessful")

# Alias for backward compatibility
OptimizedChatRequest = ChatRequest
OptimizedChatResponse = ChatResponse


# Handle chat messages using a shared function for consistency
async def _process_chat_request(
    request: ChatRequest,
    brain_service: OptimizedBrainService
) -> ChatResponse:
    """
    Process a chat request using the optimized brain service.
    This is a shared implementation used by both the standard and optimized endpoints.
    
    Args:
        request: Chat request
        brain_service: Optimized brain service
        
    Returns:
        Chat response
    """
    logger.info(f"Chat request: {request.message} (session: {request.session_id})")
    
    # Process the message
    result = await brain_service.process_message(
        message=request.message,
        session_id=request.session_id,
        context=request.context
    )
    
    # Construct response
    response = ChatResponse(
        success=result.get("success", False),
        response=result.get("response", "No response generated"),
        agent=result.get("agent") or result.get("agent_name"),
        agent_id=result.get("agent_id"),
        confidence=result.get("confidence") or result.get("selection_confidence"),
        entities=result.get("entities"),
        metadata={
            "selection_time": result.get("selection_time"),
            "execution_time": result.get("execution_time")
        },
        error=result.get("error")
    )
    
    return response

# Standard API endpoint (no prefix)
@main_router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    brain_service: OptimizedBrainService = Depends(get_optimized_brain_service)
):
    """
    Process a chat message using the optimized brain service.
    This is the main production API endpoint for chat.
    
    Args:
        request: Chat request
        brain_service: Optimized brain service
        
    Returns:
        Chat response
    """
    return await _process_chat_request(request, brain_service)

# Legacy API endpoint (with /optimized prefix) for backward compatibility
@router.post("/chat", response_model=OptimizedChatResponse)
async def optimized_chat(
    request: OptimizedChatRequest,
    brain_service: OptimizedBrainService = Depends(get_optimized_brain_service)
):
    """
    Process a chat message using the optimized brain service.
    This endpoint is maintained for backward compatibility.
    
    Args:
        request: Chat request
        brain_service: Optimized brain service
        
    Returns:
        Chat response
    """
    return await _process_chat_request(request, brain_service)


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


# Model for agent list response 
class AgentListResponseModel(BaseModel):
    """Response model for listing agents"""
    success: bool = Field(..., description="Whether the request was successful")
    agents: List[Dict[str, Any]] = Field(..., description="List of agent details")
    error: Optional[str] = Field(None, description="Error message if applicable")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


@router.get("/agents", response_model=AgentListResponseModel)
@main_router.get("/agents", response_model=AgentListResponseModel)
async def list_agents(
    brain_service: OptimizedBrainService = Depends(get_optimized_brain_service)
):
    """
    List all available agents from the optimized brain service.
    This endpoint provides a more detailed view of agents than the legacy endpoint.
    
    Returns:
        Dictionary with agent information
    """
    logger.info("Getting optimized agent list")
    
    try:
        # Get agents directly from the optimized brain service
        result = await brain_service.list_agents()
        
        # Make sure we have the expected structure
        if not result.get("success"):
            return {
                "success": False,
                "agents": [],
                "error": result.get("error", "Unknown error"),
                "metadata": {"source": "optimized_brain_service"}
            }
            
        return {
            "success": True,
            "agents": result.get("agents", []),
            "metadata": {"source": "optimized_brain_service", "count": len(result.get("agents", []))}
        }
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}", exc_info=True)
        return {
            "success": False,
            "agents": [],
            "error": str(e),
            "metadata": {"source": "optimized_brain_service"}
        }


# Model for system stats response
class SystemStatsResponseModel(BaseModel):
    """Response model for system statistics"""
    success: bool = Field(..., description="Whether the request was successful")
    total_agents: int = Field(..., description="Total number of agents")
    agent_types: Dict[str, int] = Field(..., description="Agents per type")
    total_conversations: int = Field(..., description="Total number of conversations")
    agent_distribution: Dict[str, Any] = Field(..., description="Agent distribution in conversations")
    timeframe_days: int = Field(..., description="Timeframe in days")
    error: Optional[str] = Field(None, description="Error message if applicable")
    optimized_implementation: bool = Field(True, description="Using optimized implementation")


@router.get("/stats", response_model=SystemStatsResponseModel)
@main_router.get("/stats", response_model=SystemStatsResponseModel)
async def get_system_stats(
    days: int = 7,
    brain_service: OptimizedBrainService = Depends(get_optimized_brain_service)
):
    """
    Get system statistics from the optimized brain service.
    
    Args:
        days: Number of days to look back (default: 7)
        brain_service: Optimized brain service
        
    Returns:
        Dictionary with system statistics
    """
    logger.info(f"Getting system stats for {days} days")
    
    try:
        # Get stats directly from the optimized brain service
        result = await brain_service.get_system_stats(days)
        
        # Return the result directly
        return result
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "total_agents": 0,
            "agent_types": {},
            "total_conversations": 0,
            "agent_distribution": {},
            "timeframe_days": days,
            "optimized_implementation": True
        }