"""
API Gateway for Staples Brain.
This serves as the entry point for all API interactions with the Staples Brain system.
"""
import time
import logging
from typing import Dict, List, Any, Optional, Union

import uvicorn
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.chat import router as chat_router
from backend.dependencies import get_chat_service, get_telemetry_service
from backend.services.chat_service import ChatService
from backend.services.telemetry_service import TelemetryService

# Set up logging
logger = logging.getLogger("staples_brain")

# Create FastAPI app
app = FastAPI(
    title="Staples Brain API",
    description="API Gateway for Staples Brain",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Models
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


# Include routers
app.include_router(chat_router, prefix="/api/v1")


# API Routes
@app.get("/api/v1/health", response_model=ApiResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Check if database is healthy
        await db.execute("SELECT 1")
        
        # Additional checks could be added here (LLM service, etc.)
        
        return {
            "success": True,
            "data": {
                "status": "ok",
                "health": "healthy",
                "version": "1.0.0",
                "environment": "development",
                "database": "connected",
                "openai_api": "configured"
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "data": {
                "status": "error",
                "health": "unhealthy"
            }
        }


@app.get("/api/v1/agents", response_model=AgentListResponse)
async def list_agents(
    chat_service: ChatService = Depends(get_chat_service)
):
    """List all available agents"""
    try:
        result = await chat_service.list_agents()
        return result
        
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "data": {"agents": []}
        }


@app.get("/api/v1/telemetry/sessions")
async def get_telemetry_sessions(
    limit: int = 20,
    offset: int = 0,
    days: int = 7,
    telemetry_service: TelemetryService = Depends(get_telemetry_service)
):
    """List telemetry sessions"""
    try:
        result = await telemetry_service.get_sessions(
            days=days,
            limit=limit,
            offset=offset
        )
        return result
        
    except Exception as e:
        logger.error(f"Error getting telemetry sessions: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "sessions": []
        }


@app.get("/api/v1/telemetry/sessions/{session_id}/events")
async def get_session_events(
    session_id: str,
    telemetry_service: TelemetryService = Depends(get_telemetry_service)
):
    """Get events for a telemetry session"""
    try:
        result = await telemetry_service.get_session_events(session_id)
        return result
        
    except Exception as e:
        logger.error(f"Error getting session events: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id,
            "events": []
        }


@app.get("/api/v1/stats")
async def get_system_stats(
    days: int = 7,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get system statistics"""
    try:
        result = await chat_service.get_system_stats(days)
        return result
        
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "total_conversations": 0,
            "agent_distribution": {}
        }


# Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Middleware to add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(404)
async def custom_404_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": "Not found",
            "data": None
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "data": None
        }
    )


# Fix incomplete import
from backend.database.db import get_db