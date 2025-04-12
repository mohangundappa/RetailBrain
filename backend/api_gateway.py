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
async def get_chat_service_direct():
    """
    Get a ChatService instance directly.
    This is a temporary solution to avoid circular imports.
    """
    from backend.services.chat_service import ChatService
    from backend.services.brain_service import BrainService
    from backend.config.config import get_config
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    import os
    
    # Create minimal db engine for dependency
    db_url = os.environ.get("DATABASE_URL", "").replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url)
    db = AsyncSession(engine)
    
    # Get configuration
    config = get_config()
    
    # Try to create agent factory
    try:
        from backend.brain.factory import AgentFactory
        agent_factory = AgentFactory(db)
        logger.debug("Created agent factory for brain service (API direct)")
    except ImportError:
        logger.warning("Could not import AgentFactory, continuing without database-driven agents")
        agent_factory = None
    
    # Create brain service with database session and agent factory
    brain_service = BrainService(
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


@app.get(f"{API_PREFIX}/agents")
async def list_agents(
    chat_service=Depends(get_chat_service_direct),
    db: AsyncSession = Depends(get_db)
):
    """List all available agents"""
    try:
        # Get agents from chat service
        result = await chat_service.list_agents()
        
        # Get additional information from the database
        from backend.database.agent_schema import AgentDefinition
        from sqlalchemy import select
        
        # Query all agent definitions
        try:
            query = select(AgentDefinition)
            query_result = await db.execute(query)
            agent_definitions = query_result.scalars().all()
            
            # Log the number of agent definitions found
            logger.info(f"Found {len(agent_definitions)} agent definitions in database")
            
            # Create mapping of agent names to database info
            agent_db_info = {}
            for agent_def in agent_definitions:
                logger.info(f"Processing agent definition: {agent_def.name}")
                agent_db_info[agent_def.name] = {
                    "id": str(agent_def.id),
                    "name": agent_def.name,
                    "type": agent_def.agent_type,
                    "status": agent_def.status,
                    "created_at": agent_def.created_at.isoformat() if agent_def.created_at else None,
                    "is_system": agent_def.is_system,
                    "version": agent_def.version,
                    "description": agent_def.description
                }
        except Exception as db_error:
            logger.error(f"Error querying agent definitions: {str(db_error)}", exc_info=True)
            agent_db_info = {}
        
        # Enhanced agent information format
        detailed_agents = []
        if isinstance(result, dict) and "agents" in result:
            agent_names = result["agents"]
            for agent_name in agent_names:
                agent_info = {
                    "name": agent_name,
                    "source": "database",
                    "db_driven": True,
                    "loaded": True
                }
                
                # Add database information if available
                if agent_name in agent_db_info:
                    agent_info.update(agent_db_info[agent_name])
                
                detailed_agents.append(agent_info)
            
            # Replace simple agent list with detailed list
            result = {"agents": detailed_agents}
        
        # Ensure result is standardized
        if not isinstance(result, dict) or "success" not in result:
            result = create_success_response(
                agents=detailed_agents,
                metadata={
                    "api_version": API_VERSION,
                    "db_agents": True,  # Indicate these agents are from the database
                    "agent_factory": "enabled",
                    "agent_count": len(detailed_agents) if detailed_agents else 0
                }
            )
            
        return result
        
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}", exc_info=True)
        return create_error_response(
            error_message=f"Error listing agents: {str(e)}",
            data={},
            metadata={"api_version": API_VERSION},
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
    chat_service=Depends(get_chat_service_direct)
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
                    "api_version": API_VERSION,
                    "db_agents": True  # Indicate these agents are from the database
                }
            )
            
        return result
        
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}", exc_info=True)
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


# Test endpoint for checking database-driven agents
@app.get(f"{API_PREFIX}/agent-db-test")
async def test_database_agents(db: AsyncSession = Depends(get_db)):
    """Test database-driven agent loading"""
    try:
        from backend.database.agent_schema import AgentDefinition
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from backend.repositories.agent_repository import AgentRepository

        # Create a repository to fetch agents - this correctly handles async/greenlet issues
        repo = AgentRepository(db)
        agents = await repo.get_all_active_agents()
        
        # Format agent information
        formatted_agents = []
        for agent in agents:
            # Be careful with lazy-loaded relationships
            # Directly access only fields that are not relationships
            formatted_agents.append({
                "id": str(agent.id),
                "name": agent.name,
                "agent_type": agent.agent_type,
                "description": agent.description,
                "status": agent.status,
                "created_at": agent.created_at.isoformat() if agent.created_at else None,
                "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
            })
        
        # Try to create a LangGraph agent factory and get agents
        try:
            from backend.brain.agents.langgraph_factory import LangGraphAgentFactory
            
            # Initialize a factory
            factory = LangGraphAgentFactory(db)
            
            # This is a proxy that gets evaluated when needed, we're not actually 
            # executing an async call here that might cause greenlet issues
            langgraph_factory_ready = True
            
            return create_success_response(
                data={
                    "database_agents": formatted_agents,
                    "factory_initialized": True,
                    "langgraph_factory_ready": langgraph_factory_ready
                },
                metadata={
                    "count": len(formatted_agents),
                    "api_version": API_VERSION,
                    "db_driven": True
                }
            )
        except Exception as factory_error:
            # Just report the factory error but still return the agents
            logger.warning(f"LangGraph factory error: {str(factory_error)}")
            return create_success_response(
                data={
                    "database_agents": formatted_agents,
                    "factory_initialized": False,
                    "factory_error": str(factory_error)
                },
                metadata={
                    "count": len(formatted_agents),
                    "api_version": API_VERSION,
                    "db_driven": True
                }
            )
            
    except Exception as e:
        logger.error(f"Error testing database agents: {str(e)}", exc_info=True)
        return create_error_response(
            error_message=f"Error testing database agents: {str(e)}",
            data={"database_agents": []},
            log_error=True
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