"""
API Gateway for Staples Brain.
This serves as the entry point for all API interactions with the Staples Brain system.
"""

import os
import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from services.chat_service import ChatService
from services.telemetry_service import TelemetryService
from dependencies import get_chat_service, get_telemetry_service

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api_gateway")

# Initialize FastAPI app
app = FastAPI(
    title="Staples Brain API Gateway",
    description="API Gateway for Staples Brain Services",
    version="1.0.0"
)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Pydantic Models for Request/Response ----------

class ChatRequest(BaseModel):
    """Request model for chat messages"""
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Session identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for request")

class ApiResponse(BaseModel):
    """Standard API response format"""
    success: bool = Field(..., description="Whether the request was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")
    error: Optional[str] = Field(None, description="Error message if applicable")

class AgentListResponse(BaseModel):
    """Response model for listing agents"""
    success: bool = Field(..., description="Whether the request was successful")
    data: Dict[str, List[Dict[str, Any]]] = Field(..., description="List of agents")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")
    error: Optional[str] = Field(None, description="Error message if applicable")

# ---------- API Routes ----------

@app.get("/api/v1/health", response_model=ApiResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Verify database connection
        from sqlalchemy import text
        db_healthy = False
        try:
            result = await db.execute(text("SELECT 1"))
            row = result.scalar()
            db_healthy = row == 1
        except Exception as db_error:
            logger.error(f"Database health check failed: {db_error}")
        
        # Check OpenAI API key
        openai_key_exists = "OPENAI_API_KEY" in os.environ
        
        return ApiResponse(
            success=True,
            data={
                "status": "healthy",
                "version": os.environ.get("APP_VERSION", "1.0.0"),
                "environment": os.environ.get("APP_ENV", "development"),
                "database": "connected" if db_healthy else "error",
                "openai_api": "configured" if openai_key_exists else "missing"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return ApiResponse(
            success=False,
            error=f"Health check failed: {str(e)}"
        )

@app.post("/api/v1/chat/messages", response_model=ApiResponse)
async def process_message(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Process a user message through the chat service"""
    try:
        # Process the message
        response = await chat_service.process_message(
            message=request.message,
            session_id=request.session_id,
            context=request.context
        )
        
        return ApiResponse(
            success=True,
            data=response.get("data", {}),
            metadata=response.get("metadata", {})
        )
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return ApiResponse(
            success=False,
            error=f"Error processing message: {str(e)}"
        )

@app.get("/api/v1/chat/history/{session_id}", response_model=ApiResponse)
async def get_chat_history(
    session_id: str,
    limit: int = Query(10, ge=1, le=100),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get chat history for a session"""
    try:
        history = await chat_service.get_conversation_history(
            session_id=session_id,
            limit=limit
        )
        
        return ApiResponse(
            success=True,
            data={"history": history},
            metadata={"session_id": session_id}
        )
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return ApiResponse(
            success=False,
            error=f"Error getting chat history: {str(e)}"
        )

@app.get("/api/v1/agents", response_model=AgentListResponse)
async def list_agents(
    chat_service: ChatService = Depends(get_chat_service)
):
    """List all available agents"""
    try:
        # This would normally call into a dedicated agent service
        # For now, we'll use a static list from the brain
        
        # These would come from a database query
        built_in_agents = [
            {"id": "package-tracking", "name": "Package Tracking", "description": "Track your Staples orders and packages", "is_built_in": True},
            {"id": "reset-password", "name": "Password Reset", "description": "Reset your Staples.com or account password", "is_built_in": True},
            {"id": "store-locator", "name": "Store Locator", "description": "Find Staples stores near you", "is_built_in": True},
            {"id": "product-info", "name": "Product Information", "description": "Get information about Staples products", "is_built_in": True}
        ]
        
        return AgentListResponse(
            success=True,
            data={"agents": built_in_agents}
        )
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return AgentListResponse(
            success=False,
            data={"agents": []},
            error=f"Error listing agents: {str(e)}"
        )

@app.get("/api/v1/telemetry/sessions", response_model=ApiResponse)
async def get_telemetry_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    days: int = Query(7, ge=1, le=30),
    telemetry_service: TelemetryService = Depends(get_telemetry_service)
):
    """List telemetry sessions"""
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        sessions = await telemetry_service.get_sessions(
            limit=limit,
            offset=offset,
            start_date=start_date,
            end_date=end_date
        )
        
        return ApiResponse(
            success=True,
            data={"sessions": sessions},
            metadata={
                "limit": limit,
                "offset": offset,
                "total": len(sessions),
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
        )
    except Exception as e:
        logger.error(f"Error getting telemetry sessions: {e}")
        return ApiResponse(
            success=False,
            error=f"Error getting telemetry sessions: {str(e)}"
        )

@app.get("/api/v1/telemetry/sessions/{session_id}/events", response_model=ApiResponse)
async def get_session_events(
    session_id: str,
    telemetry_service: TelemetryService = Depends(get_telemetry_service)
):
    """Get events for a telemetry session"""
    try:
        events = await telemetry_service.get_session_events(session_id=session_id)
        
        return ApiResponse(
            success=True,
            data={"events": events},
            metadata={"session_id": session_id, "event_count": len(events)}
        )
    except Exception as e:
        logger.error(f"Error getting session events: {e}")
        return ApiResponse(
            success=False,
            error=f"Error getting session events: {str(e)}"
        )

@app.get("/api/v1/stats", response_model=ApiResponse)
async def get_system_stats(
    days: int = Query(7, ge=1, le=30),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get system statistics"""
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        stats = await chat_service.get_conversation_statistics(
            start_date=start_date,
            end_date=end_date
        )
        
        return ApiResponse(
            success=True,
            data=stats,
            metadata={
                "date_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                }
            }
        )
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return ApiResponse(
            success=False,
            error=f"Error getting system stats: {str(e)}"
        )

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Middleware to add processing time to response headers"""
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Add 404 handler
@app.exception_handler(404)
async def custom_404_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"success": False, "error": "The requested URL was not found"}
    )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "An unexpected error occurred"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)