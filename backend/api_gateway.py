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
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.chat import router as chat_router
from backend.api.agent_builder_fastapi import agent_builder_router
from backend.api.circuit_breaker_fastapi import circuit_breaker_router
from backend.api.telemetry_fastapi import telemetry_router
from backend.api.routes_fastapi import api_router
from backend.database.db import get_db
from backend.dependencies import get_chat_service, get_telemetry_service
from backend.services.chat_service import ChatService
from backend.services.telemetry_service import TelemetryService

# Set up logging
logger = logging.getLogger("staples_brain")

# Import configuration
from backend.config.config import (
    APP_NAME, APP_DESCRIPTION, APP_VERSION, 
    CORS_ORIGINS, API_VERSION, API_PREFIX
)

# Create FastAPI app
app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url=f"{API_PREFIX}/docs",
    redoc_url=f"{API_PREFIX}/redoc",
    openapi_url=f"{API_PREFIX}/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
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
app.include_router(chat_router, prefix=API_PREFIX)
app.include_router(agent_builder_router, prefix=f"{API_PREFIX}/agent-builder")
app.include_router(circuit_breaker_router, prefix=f"{API_PREFIX}/circuit-breakers")
app.include_router(telemetry_router, prefix=f"{API_PREFIX}/telemetry")
app.include_router(api_router, prefix=API_PREFIX)

# Mount static directories
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Serve root path by redirecting to documentation
@app.get("/")
async def root():
    """Redirect root to static documentation"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


# API Routes
@app.get(f"{API_PREFIX}/health", response_model=ApiResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Check if database is healthy
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        
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


@app.get(f"{API_PREFIX}/agents", response_model=AgentListResponse)
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


@app.get(f"{API_PREFIX}/telemetry/sessions")
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


@app.get(f"{API_PREFIX}/telemetry/sessions/{{session_id}}/events")
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


# Startup and shutdown events
@app.on_event("startup")
async def startup_db_client():
    """Initialize database on startup."""
    from sqlalchemy.ext.asyncio import AsyncEngine
    from backend.database.db import engine, Base
    from backend.database.models import (
        Conversation, Message, TelemetrySession, 
        TelemetryEvent, CustomAgent, AgentComponent,
        ComponentConnection, ComponentTemplate, AgentTemplate
    )
    
    logger.info("Initializing database tables...")
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database tables: {str(e)}")
        # Don't raise the exception to allow the application to start
        # even if database initialization fails

# End of API Gateway module