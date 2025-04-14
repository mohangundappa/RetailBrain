"""
Routes for Chat and Observability API endpoints.
"""
import logging
from typing import Dict, List, Optional, Any, Union

from fastapi import APIRouter, Depends, HTTPException

from backend.services.context_enhanced_chat_service import ContextEnhancedChatService
from backend.endpoints.chat.models import (
    ChatRequest, ChatResponse, ObservabilityResponse, ConversationsResponse
)

# Set up logging
logger = logging.getLogger(__name__)

# Create router - no prefix since it's applied in api_gateway.py
router = APIRouter(tags=["Chat"])

# Create service instance
chat_service = ContextEnhancedChatService()


@router.post("", response_model=ChatResponse)
async def process_chat_message(request: ChatRequest) -> ChatResponse:
    """
    Process a chat message and return a response.
    
    Args:
        request: The chat request containing message and optional context
        
    Returns:
        Chat response with assistant message
    """
    try:
        response_data, _ = await chat_service.process_chat(request)
        
        return ChatResponse(
            success=True,
            data=response_data,
            metadata={
                "processing_time_ms": 500,  # Mock processing time
                "context_used": bool(request.context)
            }
        )
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        return ChatResponse(
            success=False,
            error=f"Failed to process message: {str(e)}"
        )


@router.get("/observability/{conversation_id}", response_model=ObservabilityResponse)
async def get_observability_data(conversation_id: str) -> ObservabilityResponse:
    """
    Get observability data for a conversation.
    
    Args:
        conversation_id: The conversation ID
        
    Returns:
        Observability data for the conversation
    """
    try:
        obs_data = await chat_service.get_observability_data(conversation_id)
        
        if "error" in obs_data:
            return ObservabilityResponse(
                success=False,
                error=obs_data["error"]
            )
        
        return ObservabilityResponse(
            success=True,
            data=obs_data
        )
    except Exception as e:
        logger.error(f"Error getting observability data: {str(e)}", exc_info=True)
        return ObservabilityResponse(
            success=False,
            error=f"Failed to get observability data: {str(e)}"
        )


@router.get("/conversations", response_model=ConversationsResponse)
async def get_conversations() -> ConversationsResponse:
    """
    Get a list of all conversations.
    
    Returns:
        List of conversation summaries
    """
    try:
        conversations = await chat_service.get_conversations()
        
        return ConversationsResponse(
            success=True,
            data=conversations
        )
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}", exc_info=True)
        return ConversationsResponse(
            success=False,
            data=[],
            error=f"Failed to get conversations: {str(e)}"
        )


@router.get("/conversations/{conversation_id}", response_model=ChatResponse)
async def get_conversation_history(conversation_id: str) -> ChatResponse:
    """
    Get the full history for a specific conversation.
    
    Args:
        conversation_id: The conversation ID
        
    Returns:
        Conversation data including messages
    """
    try:
        conversation = await chat_service.get_conversation_history(conversation_id)
        
        if "error" in conversation:
            return ChatResponse(
                success=False,
                error=conversation["error"]
            )
        
        return ChatResponse(
            success=True,
            data=conversation
        )
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}", exc_info=True)
        return ChatResponse(
            success=False,
            error=f"Failed to get conversation history: {str(e)}"
        )