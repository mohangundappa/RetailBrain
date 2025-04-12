"""
Chat API endpoints for the Staples Brain.
"""
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.services.chat_service import ChatService

# Create a direct dependency function to get ChatService instance
# This avoids circular imports with the dependencies module
def get_chat_service_direct():
    """
    Get a ChatService instance directly.
    This is a temporary solution to avoid circular imports.
    Creates a new database session with auto-commit mode.
    """
    from backend.services.chat_service import ChatService
    from backend.services.langgraph_brain_service import LangGraphBrainService
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from backend.repositories.conversation_repository import ConversationRepository
    import os
    
    # Create minimal db engine for dependency
    db_url = os.environ.get("DATABASE_URL", "")
    
    # Parse the DB URL to handle sslmode parameter (which asyncpg doesn't accept directly)
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    # Parse URL
    parsed_url = urlparse(db_url)
    
    # Parse query parameters
    query_params = parse_qs(parsed_url.query)
    
    # Remove sslmode parameter from query as asyncpg doesn't accept it
    if 'sslmode' in query_params:
        del query_params['sslmode']
        
    # Rebuild query string
    query_string = urlencode(query_params, doseq=True)
    
    # Rebuild URL without sslmode parameter
    parts = list(parsed_url)
    parts[4] = query_string  # Replace query part
    clean_url = urlunparse(parts)
    
    # Convert to asyncpg if needed
    if not clean_url.startswith("postgresql+asyncpg://"):
        clean_url = clean_url.replace("postgresql://", "postgresql+asyncpg://")
    
    # Create engine with pool recycling and pre-ping
    engine = create_async_engine(
        clean_url,
        pool_recycle=300,
        pool_pre_ping=True,
        echo=False,
    )
    
    # Create session maker with standard settings
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession
    )
    
    # Create session
    db = session_factory()
    
    # Create minimal brain service
    from backend.config.config import get_config
    config = get_config()
    brain_service = LangGraphBrainService(db_session=db, config=config)
    
    # Return properly initialized ChatService with the session
    return ChatService(db=db, brain_service=brain_service)

# Set up router
router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    responses={404: {"description": "Not found"}},
)


# API Models
class MessageRequest(BaseModel):
    """Message request model"""
    content: str = Field(..., description="Message content")
    session_id: Optional[str] = Field(None, description="Session ID for tracking conversation")
    user_id: Optional[str] = Field(None, description="Optional user ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class MessageResponse(BaseModel):
    """Message response model"""
    success: bool = Field(..., description="Whether the request was successful")
    message_id: str = Field(..., description="ID of the message")
    content: str = Field(..., description="Response message content")
    session_id: str = Field(..., description="Session ID for tracking conversation")
    agent_type: Optional[str] = Field(None, description="Type of agent that handled the message")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")
    error: Optional[str] = Field(None, description="Error message if applicable")


class SessionResponse(BaseModel):
    """Session response model"""
    success: bool = Field(..., description="Whether the request was successful")
    sessions: List[Dict[str, Any]] = Field(..., description="List of sessions")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")
    error: Optional[str] = Field(None, description="Error message if applicable")


class MessageListResponse(BaseModel):
    """Message list response model"""
    success: bool = Field(..., description="Whether the request was successful")
    messages: List[Dict[str, Any]] = Field(..., description="List of messages in the session")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")
    error: Optional[str] = Field(None, description="Error message if applicable")


# Endpoints
@router.post("/messages", response_model=MessageResponse)
async def send_message(
    request: MessageRequest,
    chat_service: ChatService = Depends(get_chat_service_direct)
):
    """
    Send a message to the Staples Brain and get a response.
    
    Args:
        request: Message request containing content and optional metadata
        chat_service: Chat service dependency
        
    Returns:
        MessageResponse: Response from Staples Brain
    """
    try:
        result = await chat_service.process_message(
            message=request.content,
            session_id=request.session_id,
            context={
                "user_id": request.user_id, 
                "metadata": request.metadata or {}
            }
        )
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing message: {str(e)}"
        )


@router.get("/sessions", response_model=SessionResponse)
async def list_sessions(
    limit: int = 20,
    offset: int = 0,
    chat_service: ChatService = Depends(get_chat_service_direct)
):
    """
    List all active sessions.
    
    Args:
        limit: Maximum number of sessions to return
        offset: Offset for pagination
        chat_service: Chat service dependency
        
    Returns:
        SessionResponse: List of sessions
    """
    try:
        result = await chat_service.list_sessions(limit=limit, offset=offset)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing sessions: {str(e)}"
        )


@router.get("/sessions/{session_id}/messages", response_model=MessageListResponse)
async def get_session_messages(
    session_id: str,
    limit: int = 50,
    chat_service: ChatService = Depends(get_chat_service_direct)
):
    """
    Get all messages for a session.
    
    Args:
        session_id: Session ID
        limit: Maximum number of messages to return
        chat_service: Chat service dependency
        
    Returns:
        MessageListResponse: List of messages in the session
    """
    try:
        result = await chat_service.get_session_messages(
            session_id=session_id,
            limit=limit
        )
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting session messages: {str(e)}"
        )