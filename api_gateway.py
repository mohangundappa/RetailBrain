"""
API Gateway for Staples Brain.
This serves as the entry point for all API interactions with the Staples Brain system.
"""

import os
import uuid
import logging
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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

# ---------- Service Dependencies ----------

async def get_brain_service():
    """
    Dependency for the brain service
    To be implemented with proper service initialization
    """
    # For now, this is a placeholder
    # Will be replaced with actual service initialization
    from services.brain_service import BrainService
    try:
        return BrainService()
    except Exception as e:
        logger.error(f"Failed to initialize brain service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Brain service unavailable"
        )

# ---------- API Routes ----------

@app.get("/api/v1/health", response_model=ApiResponse)
async def health_check():
    """Health check endpoint"""
    try:
        return ApiResponse(
            success=True,
            data={
                "status": "healthy",
                "version": os.environ.get("APP_VERSION", "1.0.0"),
                "environment": os.environ.get("APP_ENV", "development")
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
    brain_service=Depends(get_brain_service)
):
    """Process a user message through the brain"""
    try:
        # Generate session_id if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Process the message
        response = await brain_service.process_message(
            message=request.message,
            session_id=session_id,
            context=request.context
        )
        
        return ApiResponse(
            success=True,
            data=response.get("data", {}),
            metadata={
                "session_id": session_id,
                **response.get("metadata", {})
            }
        )
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return ApiResponse(
            success=False,
            error=f"Error processing message: {str(e)}"
        )

@app.get("/api/v1/agents", response_model=AgentListResponse)
async def list_agents(brain_service=Depends(get_brain_service)):
    """List all available agents"""
    try:
        agents = await brain_service.list_agents()
        return AgentListResponse(
            success=True,
            data={"agents": agents}
        )
    except Exception as e:
        logger.error(f"Error listing agents: {e}")
        return AgentListResponse(
            success=False,
            data={"agents": []},
            error=f"Error listing agents: {str(e)}"
        )

@app.get("/api/v1/telemetry/sessions", response_model=ApiResponse)
async def get_telemetry_sessions(brain_service=Depends(get_brain_service)):
    """List all telemetry sessions"""
    try:
        sessions = await brain_service.get_telemetry_sessions()
        return ApiResponse(
            success=True,
            data={"sessions": sessions}
        )
    except Exception as e:
        logger.error(f"Error getting telemetry sessions: {e}")
        return ApiResponse(
            success=False,
            error=f"Error getting telemetry sessions: {str(e)}"
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