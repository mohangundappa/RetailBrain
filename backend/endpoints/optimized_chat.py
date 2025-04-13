"""
DEPRECATED: This module has been replaced by graph_chat.py.

This file is kept as a stub for backward compatibility but contains minimal implementation.
All chat endpoint functionality has been moved to backend/endpoints/graph_chat.py.
"""

import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.endpoints.graph_chat import GraphChatRequest, GraphChatResponse
from backend.services.graph_dependencies import get_graph_brain_service

logger = logging.getLogger(__name__)

# Create API router
# This is kept for backward compatibility but will forward to graph_chat endpoints
router = APIRouter(tags=["chat"])


class ChatRequest(GraphChatRequest):
    """Request model for chat (backward compatibility)"""
    pass


class ChatResponse(GraphChatResponse):
    """Response model for chat (backward compatibility)"""
    pass


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    graph_brain_service = Depends(get_graph_brain_service)
):
    """
    Process a chat message using the graph-based brain service.
    
    This endpoint is maintained for backward compatibility and forwards
    requests to the graph-based implementation.
    
    Args:
        request: Chat request
        graph_brain_service: Graph brain service
        
    Returns:
        Chat response
    """
    logger.warning("Deprecated /chat endpoint called, forwarding to graph-based implementation")
    
    # Forward to graph-based implementation
    from backend.endpoints.graph_chat import _process_graph_chat_request
    return await _process_graph_chat_request(request, graph_brain_service)