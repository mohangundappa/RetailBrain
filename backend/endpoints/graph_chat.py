"""
API routes for graph-based chat functionality.

This module provides FastAPI routes for the LangGraph-based brain service
with database-driven agent configurations.
"""
import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.services.graph_brain_service import GraphBrainService
from backend.services.graph_dependencies import get_graph_brain_service

logger = logging.getLogger(__name__)

# Create API router for graph chat
router = APIRouter(tags=["graph_chat"])


class GraphChatRequest(BaseModel):
    """Request model for graph chat"""
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ResponseContent(BaseModel):
    """Content model for response"""
    message: str = Field(..., description="Response message text")
    type: str = Field("text", description="Response content type")


class GraphChatResponse(BaseModel):
    """Response model for graph chat"""
    success: bool = Field(..., description="Whether the request was successful")
    response: ResponseContent = Field(..., description="Response content")
    conversation_id: Optional[str] = Field(None, description="ID of the conversation")
    external_conversation_id: Optional[str] = Field(None, description="External ID of the conversation")
    observability_trace_id: Optional[str] = Field(None, description="Observability trace ID")
    error: Optional[str] = Field(None, description="Error message if applicable")


async def _process_graph_chat_request(
    request: GraphChatRequest,
    brain_service: GraphBrainService
) -> GraphChatResponse:
    """
    Process a chat request using the LangGraph brain service.
    
    Args:
        request: Chat request
        brain_service: Graph brain service
        
    Returns:
        Chat response
    """
    logger.info(f"Graph chat request: {request.message} (session: {request.session_id})")
    
    # Process the message
    result = await brain_service.process_message(
        message=request.message,
        session_id=request.session_id,
        context=request.context
    )
    
    # Construct response using standardized format
    response = GraphChatResponse(
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


@router.post("/chat", response_model=GraphChatResponse)
async def graph_chat(
    request: GraphChatRequest,
    brain_service: GraphBrainService = Depends(get_graph_brain_service)
):
    """
    Process a chat message using the LangGraph-based brain service.
    
    Args:
        request: Chat request
        brain_service: Graph brain service
        
    Returns:
        Chat response
    """
    return await _process_graph_chat_request(request, brain_service)


class DirectAgentRequest(BaseModel):
    """Request model for direct agent execution"""
    agent_id: str = Field(..., description="ID of the agent to execute")
    message: str = Field(..., description="User message")
    session_id: str = Field(..., description="Session ID")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


@router.post("/execute-agent", response_model=GraphChatResponse)
async def execute_agent(
    request: DirectAgentRequest,
    brain_service: GraphBrainService = Depends(get_graph_brain_service)
):
    """
    Execute a specific agent directly.
    
    Args:
        request: Agent execution request
        brain_service: Graph brain service
        
    Returns:
        Execution response
    """
    logger.info(f"Direct agent execution: {request.agent_id}, message: {request.message}")
    
    # Get context or initialize empty
    context = request.context or {}
    
    # Add agent ID to the context for direct routing
    context["direct_agent_id"] = request.agent_id
    context["bypass_router"] = True
    
    # Process with brain service
    result = await brain_service.process_message(
        message=request.message,
        session_id=request.session_id,
        context=context
    )
    
    # Construct response
    response = GraphChatResponse(
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