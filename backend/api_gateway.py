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
from backend.endpoints.state_management import state_router
from backend.endpoints.routes import api_router
from backend.endpoints.graph_chat import router as graph_chat_router  # LangGraph-based chat functionality
from backend.endpoints.chat.routes import router as chat_router  # Standard chat functionality
from backend.endpoints.agent_builder import agent_builder_router  # Agent Builder functionality
from backend.endpoints.workflow_driven_agents import workflow_router  # Workflow-driven agents functionality
from backend.endpoints.agent_workflow import agent_workflow_router  # Agent workflow information functionality
from backend.endpoints.supervisor_chat import router as supervisor_chat_router  # LangGraph Supervisor-based chat
from backend.database.db import get_db

# Utility function to sanitize database URLs for asyncpg
def get_sanitized_db_url(for_async=False):
    """
    Get a database URL with the sslmode parameter removed for asyncpg compatibility.
    
    Args:
        for_async: If True, the URL will be formatted for asyncpg.
        
    Returns:
        str: Sanitized database URL
    """
    db_url = os.environ.get("DATABASE_URL", "")
    
    # Handle asyncpg driver if needed
    if for_async and db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')
    
    # Parse URL
    parsed_url = urlparse(db_url)
    
    # Parse query parameters
    query_params = parse_qs(parsed_url.query)
    
    # Remove sslmode parameter from query as asyncpg doesn't accept it
    if 'sslmode' in query_params and (for_async or 'asyncpg' in db_url):
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
    from backend.services.graph_brain_service import GraphBrainService
    from backend.config.config import get_config
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from backend.memory.factory import get_mem0
    import os
    
    # Create minimal db engine for dependency using sanitized URL
    db_url = get_sanitized_db_url()
    engine = create_async_engine(db_url)
    db = AsyncSession(engine)
    
    # Get configuration
    config = get_config()
    
    # Get memory service (mem0)
    memory_service = await get_mem0("default")
    
    # Try to create LangGraph agent factory
    try:
        from backend.agents.framework.langgraph.langgraph_factory import LangGraphAgentFactory
        agent_factory = LangGraphAgentFactory(db)
        logger.debug("Created LangGraph agent factory for brain service (API direct)")
    except ImportError:
        logger.warning("Could not import LangGraphAgentFactory, continuing without database-driven agents")
        agent_factory = None
    
    # Create graph brain service with database session and agent factory
    brain_service = GraphBrainService(
        db_session=db,
        config=config,
        memory_service=memory_service,
        agent_factory=agent_factory
    )
    
    # Initialize agents from database if possible
    if hasattr(brain_service, 'initialize') and callable(getattr(brain_service, 'initialize')):
        await brain_service.initialize()
    
    # Return properly initialized ChatService
    return ChatService(db_session=db, brain_service=brain_service)

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
    return TelemetryService(db_session=db)
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
app.include_router(state_router, prefix=API_PREFIX)
app.include_router(api_router, prefix=API_PREFIX)
app.include_router(graph_chat_router, prefix=API_PREFIX)  # LangGraph-based chat functionality
app.include_router(chat_router, prefix=f"{API_PREFIX}/chat")  # Standard chat functionality
app.include_router(agent_builder_router, prefix=API_PREFIX)  # Agent Builder functionality
app.include_router(workflow_router, prefix=API_PREFIX)  # Workflow-driven agents functionality
app.include_router(agent_workflow_router, prefix=API_PREFIX)  # Agent workflow information
app.include_router(supervisor_chat_router, prefix=API_PREFIX)  # LangGraph Supervisor-based chat

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

# We'll add our frontend path handling to the existing 404 handler below


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
            
        # Preload the brain service to ensure agents are loaded at startup
        try:
            # Import individual functions directly from modules
            from backend.config.config import get_config
            from backend.memory.factory import get_mem0
            from backend.services.graph_brain_service import GraphBrainService
            from backend.services.supervisor_brain_service import SupervisorBrainService
            from backend.agents.framework.langgraph.langgraph_factory import LangGraphAgentFactory
            from backend.agents.framework.langgraph.langgraph_supervisor_factory import LangGraphSupervisorFactory
            
            # Get configuration
            config = get_config()
            
            # Get memory service (mem0)
            memory_service = await get_mem0("default")
            
            # Initialize the brain service directly
            db = await anext(get_db())
            
            # Create agent factory for LangGraph
            agent_factory = LangGraphAgentFactory(db)
            
            # Create the brain service instance directly
            brain_service = GraphBrainService(
                db_session=db,
                config=config,
                memory_service=memory_service,
                agent_factory=agent_factory
            )
            
            # Initialize the brain service
            await brain_service.initialize()
            
            # Preload agents from database 
            # (This step is already handled by the GraphBrainService.initialize() method above)
            logger.info("Agents successfully pre-loaded during brain service initialization")
            
            # Create supervisor factory for LangGraph
            supervisor_factory = LangGraphSupervisorFactory(db)
            
            # Create and initialize the supervisor brain service
            supervisor_brain_service = SupervisorBrainService(
                db_session=db,
                config=config,
                memory_service=memory_service,
                agent_factory=agent_factory,
                supervisor_factory=supervisor_factory
            )
            
            # Initialize the supervisor brain service
            supervisor_success = await supervisor_brain_service.initialize()
            if supervisor_success:
                logger.info("Supervisor brain service initialized successfully")
            else:
                logger.warning("Supervisor brain service initialization returned false")
                
        except Exception as brain_err:
            logger.warning(f"Error pre-loading brain service: {str(brain_err)}", exc_info=True)
            
    except Exception as e:
        logger.error(f"Error initializing database tables: {str(e)}")
        # Don't raise the exception to allow the application to start
        # even if database initialization fails

# End of API Gateway module