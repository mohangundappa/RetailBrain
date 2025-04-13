"""
API Gateway for Staples Brain.
This serves as the entry point for all API interactions with the Staples Brain system.
"""
import time
import logging
import os
from typing import Dict, List, Any, Optional, Union
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

import uvicorn
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# Import only the routers we need
from backend.endpoints.optimized_chat import router as optimized_chat_router
from backend.endpoints.optimized_chat import main_router as chat_router
from backend.endpoints.state_management import state_router
from backend.endpoints.routes import api_router
from backend.database.db import get_db

# Utility function to sanitize database URLs for asyncpg
def get_sanitized_db_url():
    """
    Get a database URL with the sslmode parameter removed for asyncpg compatibility.
    
    Returns:
        str: Sanitized database URL
    """
    db_url = os.environ.get("DATABASE_URL", "")
    
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
    
    return clean_url
# Direct dependency functions to avoid circular imports
async def get_chat_service_direct():
    """
    Get a ChatService instance directly.
    This is a temporary solution to avoid circular imports.
    """
    from backend.services.chat_service import ChatService
    from backend.services.optimized_brain_service import OptimizedBrainService
    from backend.config.config import get_config
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    import os
    
    # Create minimal db engine for dependency using sanitized URL
    db_url = get_sanitized_db_url()
    engine = create_async_engine(db_url)
    db = AsyncSession(engine)
    
    # Get configuration
    config = get_config()
    
    # Try to create LangGraph agent factory
    try:
        # Import from agents/models instead of brain/agents
        from backend.agents.models import LangGraphAgentFactory
        agent_factory = LangGraphAgentFactory(db)
        logger.debug("Created LangGraph agent factory for brain service (API direct)")
    except ImportError:
        logger.warning("Could not import LangGraphAgentFactory, continuing without database-driven agents")
        agent_factory = None
    
    # Create optimized brain service with database session and agent factory
    brain_service = OptimizedBrainService(
        db_session=db,
        config=config,
        agent_factory=agent_factory
    )
    
    # Initialize agents from database if possible
    if hasattr(brain_service, 'initialize') and callable(getattr(brain_service, 'initialize')):
        await brain_service.initialize()
    
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
    
    # Create minimal db engine for dependency using sanitized URL
    db_url = get_sanitized_db_url()
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


class AgentDetailModel(BaseModel):
    """Model for agent details"""
    name: str = Field(..., description="Agent name")
    id: Optional[str] = Field(None, description="Agent ID")
    type: Optional[str] = Field(None, description="Agent type")
    status: Optional[str] = Field(None, description="Agent status")
    version: Optional[int] = Field(None, description="Agent version")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    is_system: Optional[bool] = Field(None, description="Whether this is a system agent")
    source: Optional[str] = Field(None, description="Agent data source")
    db_driven: Optional[bool] = Field(None, description="Whether this agent is database-driven")
    loaded: Optional[bool] = Field(None, description="Whether this agent is loaded")
    description: Optional[str] = Field(None, description="Agent description")


class AgentListResponse(BaseModel):
    """Response model for listing agents"""
    success: bool = Field(..., description="Whether the request was successful")
    agents: Union[List[str], List[AgentDetailModel]] = Field(..., description="List of agents")
    error: Optional[str] = Field(None, description="Error message if applicable")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")


# Include only essential routers
app.include_router(chat_router, prefix=API_PREFIX)
app.include_router(state_router, prefix=API_PREFIX)
app.include_router(optimized_chat_router, prefix=API_PREFIX)
app.include_router(api_router, prefix=API_PREFIX)

# API Documentation is available at /api/v1/docs
# Root path now returns API information instead of redirecting to static files
@app.get("/")
async def root():
    """Return API information"""
    return {
        "name": "Staples Brain API",
        "version": "1.0.0",
        "description": "API for Staples Brain - Multi-agent AI orchestration platform",
        "documentation_url": "/api/v1/docs",
        "api_prefix": API_PREFIX
    }


# API Routes
# All endpoints are now routed through the optimized routers


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


# Removed test endpoints
# All agent testing is now done through optimized router endpoints

# Startup and shutdown events
@app.on_event("startup")
async def startup_db_client():
    """Initialize database on startup."""
    from sqlalchemy.ext.asyncio import AsyncEngine
    from backend.database.db import engine, Base, get_db
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
        
        # Initialize state persistence tables
        try:
            from backend.orchestration.state import create_db_tables
            # Get a database session
            db = await anext(get_db())
            # Create state persistence tables
            await create_db_tables(db)
            logger.info("State persistence tables initialized successfully")
        except ImportError:
            logger.warning("State persistence module not available, skipping initialization")
        except Exception as state_err:
            logger.warning(f"Error initializing state persistence tables: {str(state_err)}")
    except Exception as e:
        logger.error(f"Error initializing database tables: {str(e)}")
        # Don't raise the exception to allow the application to start
        # even if database initialization fails

# End of API Gateway module