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
# Direct dependency functions to avoid circular imports
def get_chat_service_direct():
    """
    Get a ChatService instance directly.
    This is a temporary solution to avoid circular imports.
    """
    from backend.services.chat_service import ChatService
    from backend.services.brain_service import BrainService
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    import os
    
    # Create minimal db engine for dependency
    db_url = os.environ.get("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    db = AsyncSession(engine)
    
    # Create minimal brain service for dependency
    brain_service = BrainService()
    
    # Return properly initialized ChatService
    return ChatService(db=db, brain_service=brain_service)

def get_telemetry_service_direct():
    """
    Get a TelemetryService instance directly.
    This is a temporary solution to avoid circular imports.
    """
    from backend.services.telemetry_service import TelemetryService
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    import os
    
    # Create minimal db engine for dependency
    db_url = os.environ.get("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    db = AsyncSession(engine)
    
    # Return properly initialized TelemetryService
    return TelemetryService(db=db)
from backend.services.chat_service import ChatService
from backend.services.telemetry_service import TelemetryService

# Set up logging
logger = logging.getLogger("staples_brain")

# Import configuration
from backend.config.config import (
    APP_NAME, APP_DESCRIPTION, APP_VERSION, APP_ENV,
    CORS_ORIGINS, API_VERSION, API_PREFIX, API_VERSIONS
)
from backend.utils.api_utils import create_success_response, create_error_response

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
        
        return create_success_response(
            data={
                "status": "ok",
                "health": "healthy",
                "version": APP_VERSION,
                "environment": APP_ENV,
                "database": "connected",
                "openai_api": "configured"
            },
            metadata={
                "api_version": API_VERSION,
                "deprecation": API_VERSIONS.get(API_VERSION, {})
            }
        )
        
    except Exception as e:
        return create_error_response(
            error_message=f"Health check failed: {str(e)}",
            data={
                "status": "error",
                "health": "unhealthy"
            },
            log_error=True
        )


@app.get(f"{API_PREFIX}/agents", response_model=AgentListResponse)
async def list_agents(
    chat_service: ChatService = Depends(get_chat_service_direct)
):
    """List all available agents"""
    try:
        result = await chat_service.list_agents()
        
        # Ensure result is standardized
        if not isinstance(result, dict) or "success" not in result:
            result = create_success_response(
                data=result,
                metadata={
                    "api_version": API_VERSION
                }
            )
            
        return result
        
    except Exception as e:
        return create_error_response(
            error_message=f"Error listing agents: {str(e)}",
            data={"agents": []},
            log_error=True
        )


@app.get(f"{API_PREFIX}/telemetry/sessions")
async def get_telemetry_sessions(
    limit: int = 20,
    offset: int = 0,
    days: int = 7,
    telemetry_service: TelemetryService = Depends(get_telemetry_service_direct)
):
    """List telemetry sessions"""
    try:
        result = await telemetry_service.get_sessions(
            days=days,
            limit=limit,
            offset=offset
        )
        
        # Check if result is already in standard format
        if not isinstance(result, dict) or "success" not in result:
            result = create_success_response(
                data={"sessions": result} if result else {"sessions": []},
                metadata={
                    "count": len(result) if result else 0,
                    "limit": limit,
                    "offset": offset,
                    "days": days,
                    "api_version": API_VERSION
                }
            )
            
        return result
        
    except Exception as e:
        return create_error_response(
            error_message=f"Error getting telemetry sessions: {str(e)}",
            data={"sessions": []},
            metadata={
                "limit": limit,
                "offset": offset,
                "days": days
            },
            log_error=True
        )


@app.get(f"{API_PREFIX}/telemetry/sessions/{{session_id}}/events")
async def get_session_events(
    session_id: str,
    telemetry_service: TelemetryService = Depends(get_telemetry_service_direct)
):
    """Get events for a telemetry session"""
    try:
        result = await telemetry_service.get_session_events(session_id)
        
        # Check if result is already in standard format
        if not isinstance(result, dict) or "success" not in result:
            result = create_success_response(
                data={
                    "session_id": session_id,
                    "events": result if result else []
                },
                metadata={
                    "count": len(result) if result else 0,
                    "api_version": API_VERSION
                }
            )
            
        return result
        
    except Exception as e:
        return create_error_response(
            error_message=f"Error getting session events: {str(e)}",
            data={
                "session_id": session_id,
                "events": []
            },
            log_error=True
        )


@app.get(f"{API_PREFIX}/stats")
async def get_system_stats(
    days: int = 7,
    chat_service: ChatService = Depends(get_chat_service_direct)
):
    """Get system statistics"""
    try:
        result = await chat_service.get_system_stats(days)
        
        # Check if result is already in standard format
        if not isinstance(result, dict) or "success" not in result:
            result = create_success_response(
                data=result if result else {
                    "total_conversations": 0,
                    "agent_distribution": {}
                },
                metadata={
                    "days": days,
                    "api_version": API_VERSION
                }
            )
            
        return result
        
    except Exception as e:
        return create_error_response(
            error_message=f"Error getting system stats: {str(e)}",
            data={
                "total_conversations": 0,
                "agent_distribution": {}
            },
            metadata={
                "days": days
            },
            log_error=True
        )


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
        content=create_error_response(
            error_message="Not found",
            data={"path": request.url.path},
            metadata={"request_id": request.headers.get("X-Request-ID", "")},
            log_error=False
        )
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=create_error_response(
            error_message=str(exc),
            data={"path": request.url.path},
            metadata={
                "request_id": request.headers.get("X-Request-ID", ""),
                "api_version": API_VERSION
            },
            log_error=False  # Already logged above
        )
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