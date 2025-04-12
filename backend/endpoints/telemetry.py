"""
API endpoints for telemetry data.
This module provides access to the orchestration telemetry for monitoring and debugging.

FastAPI version - migrated from Flask
"""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

from backend.orchestration.telemetry import telemetry_system

logger = logging.getLogger(__name__)

# Define API response models
class TelemetrySessionResponse(BaseModel):
    """Response model for telemetry session endpoints"""
    success: bool
    sessions: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None
    event_count: Optional[int] = None
    events: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None

# Create router
telemetry_router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@telemetry_router.get("/sessions", response_model=TelemetrySessionResponse)
async def get_sessions(limit: int = Query(5, description="Maximum number of sessions to return")):
    """
    Get recent telemetry sessions.
    
    Args:
        limit: Maximum number of sessions to return
        
    Returns:
        JSON response with session IDs
    """
    sessions = telemetry_system.get_latest_sessions(limit)
    
    return {
        "success": True,
        "sessions": sessions
    }


@telemetry_router.get("/sessions/{session_id}", response_model=TelemetrySessionResponse)
async def get_session_events(session_id: str):
    """
    Get events for a specific session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        JSON response with events
    """
    events = telemetry_system.get_session_events(session_id)
    
    return {
        "success": True,
        "session_id": session_id,
        "event_count": len(events),
        "events": events
    }


@telemetry_router.delete("/sessions/{session_id}", response_model=TelemetrySessionResponse)
async def clear_session(session_id: str):
    """
    Clear events for a specific session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        JSON confirmation
    """
    telemetry_system.clear_session(session_id)
    
    return {
        "success": True,
        "message": f"Cleared telemetry for session {session_id}"
    }


@telemetry_router.delete("/sessions", response_model=TelemetrySessionResponse)
async def clear_all_sessions():
    """
    Clear all telemetry sessions.
    
    Returns:
        JSON confirmation
    """
    telemetry_system.clear_all_sessions()
    
    return {
        "success": True,
        "message": "Cleared all telemetry sessions"
    }