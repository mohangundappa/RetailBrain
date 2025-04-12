"""
API routes for testing database-driven agent chat functionality.
"""
import logging
import uuid
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.config import API_PREFIX
from backend.database.db import get_db
from backend.dependencies import get_brain_service, get_agent_repository
from backend.services.hybrid_brain_service import HybridBrainService
from backend.utils.api_utils import create_success_response, create_error_response

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix=f"{API_PREFIX}/db-agents",
    tags=["Database Agents"]
)


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context information")
    agent_name: Optional[str] = Field(None, description="Specific agent to use")


class ChatResponse(BaseModel):
    """Chat response model"""
    success: bool = Field(..., description="Whether the request was successful")
    response: str = Field(..., description="Agent response")
    agent: Optional[str] = Field(None, description="Agent that generated the response")
    confidence: Optional[float] = Field(None, description="Confidence score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")
    error: Optional[str] = Field(None, description="Error message if applicable")


@router.get("/list", response_model=Dict[str, Any])
async def list_db_agents(
    brain_service: HybridBrainService = Depends(get_brain_service),
    repo = Depends(get_agent_repository)
):
    """List all database-driven agents"""
    try:
        # Use repository to fetch agents from database
        agents = await repo.get_all_active_agents()
        
        # Format agent information
        formatted_agents = []
        for agent in agents:
            formatted_agents.append({
                "id": str(agent.id),
                "name": agent.name,
                "agent_type": agent.agent_type,
                "description": agent.description,
                "status": agent.status,
                "created_at": agent.created_at.isoformat() if agent.created_at else None,
                "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
            })
        
        return create_success_response(
            data={"agents": formatted_agents},
            metadata={
                "count": len(formatted_agents),
                "db_driven": True
            }
        )
    except Exception as e:
        logger.error(f"Error listing database agents: {str(e)}", exc_info=True)
        return create_error_response(
            error_message=f"Error listing database agents: {str(e)}",
            log_error=True
        )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_db_agent(
    request: ChatRequest,
    brain_service: HybridBrainService = Depends(get_brain_service)
):
    """
    Chat with a database-driven agent.
    
    This endpoint processes a user message and returns a response from the selected agent.
    If no agent is specified, it will try to route to the appropriate agent based on the message content.
    """
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Get reply from brain service
        result = await brain_service.process_request(
            message=request.message,
            session_id=session_id,
            context=request.context or {},
            agent_name=request.agent_name
        )
        
        # Extract response and metadata
        response = result.get("response", "I'm sorry, I wasn't able to generate a response.")
        agent = result.get("agent", "unknown")
        confidence = result.get("confidence", 0.0)
        metadata = result.get("metadata", {})
        
        # Add session ID to metadata if not present
        if "session_id" not in metadata:
            metadata["session_id"] = session_id
        
        return ChatResponse(
            success=True,
            response=response,
            agent=agent,
            confidence=confidence,
            metadata=metadata,
            error=None
        )
    except Exception as e:
        logger.error(f"Error in database agent chat: {str(e)}", exc_info=True)
        return ChatResponse(
            success=False,
            response="I apologize, but I encountered an error while processing your request.",
            agent="error_handler",
            confidence=0.0,
            metadata={"session_id": request.session_id or str(uuid.uuid4())},
            error=str(e)
        )


@router.get("/test/{agent_name}", response_model=ChatResponse)
async def test_specific_agent(
    agent_name: str,
    test_message: Optional[str] = "Hello, can you help me?",
    brain_service: HybridBrainService = Depends(get_brain_service)
):
    """
    Test a specific database-driven agent with a simple message.
    
    This endpoint is useful for verifying that a particular agent is working correctly.
    """
    try:
        # Generate a test session ID
        session_id = f"test-{str(uuid.uuid4())}"
        
        # Get reply from brain service
        result = await brain_service.process_request(
            message=test_message,
            session_id=session_id,
            context={"test_mode": True},
            agent_name=agent_name
        )
        
        # Extract response and metadata
        response = result.get("response", "I'm sorry, I wasn't able to generate a response.")
        agent = result.get("agent", "unknown")
        confidence = result.get("confidence", 0.0)
        metadata = result.get("metadata", {})
        
        # Add session ID to metadata if not present
        if "session_id" not in metadata:
            metadata["session_id"] = session_id
        
        return ChatResponse(
            success=True,
            response=response,
            agent=agent,
            confidence=confidence,
            metadata=metadata,
            error=None
        )
    except Exception as e:
        logger.error(f"Error testing agent {agent_name}: {str(e)}", exc_info=True)
        return ChatResponse(
            success=False,
            response=f"Error testing agent {agent_name}",
            agent="error_handler",
            confidence=0.0,
            metadata={"session_id": session_id},
            error=str(e)
        )