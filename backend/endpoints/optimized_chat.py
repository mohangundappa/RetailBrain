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
# Single, clean router for chat functionality
router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat"""
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ResponseContent(BaseModel):
    """Content model for response"""
    message: str = Field(..., description="Response message text")
    type: str = Field("text", description="Type of response (text, rich, etc.)")

class ChatResponse(BaseModel):
    """Response model for chat"""
    success: bool = Field(..., description="Whether the request was successful")
    response: ResponseContent = Field(..., description="Agent response content")
    conversation_id: str = Field("", description="Internal conversation ID")
    external_conversation_id: str = Field("", description="External conversation ID for integration")
    observability_trace_id: str = Field("", description="Trace ID for observability")
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
    
    # Construct response using new format
    response = ChatResponse(
        success=result.get("success", False),
        response=ResponseContent(
            message=result.get("response", "No response generated"),
            type="text"
        ),
        conversation_id=result.get("conversation_id", ""),
        external_conversation_id=result.get("external_conversation_id", ""),
        observability_trace_id=result.get("trace_id", ""),
        error=result.get("error")
    )
    
    return response

# Clean API endpoint for chat
@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    brain_service: OptimizedBrainService = Depends(get_optimized_brain_service)
):
    """
    Process a chat message using the optimized brain service.
    This is the clean API endpoint for chat functionality.
    
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
    
    # Construct response using new format
    response = OptimizedChatResponse(
        success=result.get("success", False),
        response=ResponseContent(
            message=result.get("response", "No response generated" if not result.get("response") else result.get("response")),
            type="text"
        ),
        conversation_id=result.get("conversation_id", ""),
        external_conversation_id=result.get("external_conversation_id", ""),
        observability_trace_id=result.get("trace_id", ""),
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