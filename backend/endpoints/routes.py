"""
Main API routes for Staples Brain.

This module provides the primary API endpoints for interacting with the Staples Brain system.

FastAPI version - migrated from Flask
"""
import logging
import json
import importlib
import uuid
import asyncio
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Create API router
api_router = APIRouter(tags=["api"])

# Store brain instance
_brain = None

async def get_brain_async():
    """
    Get or initialize the GraphBrainService instance asynchronously.
    
    Returns:
        GraphBrainService instance
    """
    from backend.services.graph_dependencies import get_graph_brain_service_direct
    return await get_graph_brain_service_direct()

# Global brain instance
_brain = None

def get_brain():
    """
    Get or initialize the GraphBrainService instance.
    This is a synchronous wrapper around get_brain_async for backward compatibility.
    
    Returns:
        GraphBrainService instance
    """
    global _brain
    # If the brain is already initialized, return it
    if _brain is not None:
        return _brain
        
    # If we're in an async context, we can't initialize here
    # Return None and let the caller handle it
    logger.warning("Brain not yet initialized and cannot initialize in sync context")
    return None

# Define API models
class HealthResponse(BaseModel):
    status: str
    message: str
    version: str
    agents: List[str]

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    response: Optional[str] = None

class SuccessResponse(BaseModel):
    success: bool = True
    response: Optional[str] = None
    agent: Optional[str] = None
    session_id: Optional[str] = None

class ProcessRequest(BaseModel):
    input: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = {}

class PackageTrackingRequest(BaseModel):
    tracking_number: Optional[str] = None
    query: Optional[str] = None
    
class PasswordResetRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    query: Optional[str] = None
    
class MockPasswordResetRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    account_type: Optional[str] = None

class MockPasswordResetResponse(BaseModel):
    status: str
    message: str
    reset_link_sent: Optional[bool] = None
    instructions: Optional[List[str]] = None

class EntityDefinitionRequest(BaseModel):
    entities: List[Dict[str, Any]]

class EntityDefinitionResponse(BaseModel):
    success: bool
    setup_code: Optional[str] = None
    entity_count: Optional[int] = None
    doc: Optional[str] = None
    error: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    agent_id: Optional[str] = None

class AgentListResponse(BaseModel):
    success: bool
    agents: List[str]
    error: Optional[str] = None

@api_router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    try:
        # Get brain instance asynchronously
        global _brain
        if _brain is None:
            _brain = await get_brain_async()
        
        agent_names = await _brain.list_agents()
        return {
            "status": "healthy",
            "message": "Orchestration Engine is running",
            "version": "1.0.0",
            "agents": agent_names
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )

@api_router.post("/process", response_model=Union[SuccessResponse, ErrorResponse])
async def process_request(data: ProcessRequest):
    """
    Process a user request.
    
    Returns:
        Agent response
    """
    try:
        user_input = data.input
        session_id = data.session_id
        context = data.context or {}
        
        # Add session_id to context if provided
        if session_id:
            context["session_id"] = session_id
        
        # Get brain instance asynchronously
        global _brain
        if _brain is None:
            _brain = await get_brain_async()
        
        # Process request
        response = await _brain.process_request(
            message=user_input, 
            session_id=session_id, 
            context=context
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "response": "An error occurred while processing your request"
        }

@api_router.get("/agents", response_model=AgentListResponse)
async def list_agents():
    """
    List all available agents.
    
    Returns:
        List of agents
    """
    try:
        # Get brain instance asynchronously
        global _brain
        if _brain is None:
            _brain = await get_brain_async()
            
        agent_names = await _brain.list_agents()
        
        return {
            "success": True,
            "agents": agent_names
        }
        
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
        
@api_router.post("/generate-entity-definitions", response_model=EntityDefinitionResponse)
async def generate_entity_definitions(data: EntityDefinitionRequest):
    """
    Generate entity definitions for the entity collection framework.
    
    This endpoint takes entity information and generates the code for
    setting up entity definitions and validation in the BaseAgent framework.
    
    Request body:
    {
        "entities": [
            {
                "name": "order_number",
                "required": true,
                "validation_pattern": "^[A-Za-z0-9]{2,}-?[A-Za-z0-9]{2,}$",
                "error_message": "Order numbers typically contain letters and numbers",
                "description": "Your Staples order number",
                "examples": ["OD1234567", "STB-987654"],
                "alternate_names": ["order id", "confirmation number"]
            }
        ]
    }
    
    Returns:
        JSON with generated code and configuration
    """
    try:
        entities = data.entities
        
        if not entities:
            return {
                "success": False,
                "error": "No entities provided"
            }
            
        # Generate entity definition code
        setup_code = "def setup_entity_definitions(self) -> None:\n"
        setup_code += "    \"\"\"\n"
        setup_code += "    Set up entity definitions for extraction with validation patterns and examples.\n"
        setup_code += "    \"\"\"\n"
        
        entity_definitions = []
        
        for entity in entities:
            name = entity.get("name", "unknown")
            required = entity.get("required", True)
            validation_pattern = entity.get("validation_pattern", ".*")
            error_message = entity.get("error_message", f"Please provide a valid {name}")
            description = entity.get("description", f"The {name} for this transaction")
            examples = entity.get("examples", [])
            alternate_names = entity.get("alternate_names", [])
            
            # Format the entity definition
            entity_def = f"    # Define {name} entity\n"
            entity_def += f"    {name}_entity = EntityDefinition(\n"
            entity_def += f"        name=\"{name}\",\n"
            entity_def += f"        required={str(required)},\n"
            entity_def += f"        validation_pattern=r'{validation_pattern}',\n"
            entity_def += f"        error_message=\"{error_message}\",\n"
            entity_def += f"        description=\"{description}\",\n"
            
            # Format examples list
            examples_str = ", ".join([f'"{ex}"' for ex in examples])
            entity_def += f"        examples=[{examples_str}],\n"
            
            # Format alternate names list
            alternate_names_str = ", ".join([f'"{name}"' for name in alternate_names])
            entity_def += f"        alternate_names=[{alternate_names_str}]\n"
            entity_def += "    )\n"
            
            entity_definitions.append(entity_def)
        
        # Add all entity definitions to the setup code
        setup_code += "\n".join(entity_definitions)
        
        # Add the setup_entity_collection call
        entity_vars = [f"{entity.get('name', 'unknown')}_entity" for entity in entities]
        entity_vars_str = ", ".join(entity_vars)
        setup_code += f"\n    # Set up entity collection with these entities\n"
        setup_code += f"    self.setup_entity_collection([{entity_vars_str}])\n"
        
        # Create the response
        return {
            "success": True,
            "setup_code": setup_code,
            "entity_count": len(entities),
            "doc": "Insert this setup_entity_definitions method into your agent class and call it from the __init__ method."
        }
        
    except Exception as e:
        logger.error(f"Error generating entity definitions: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

@api_router.post("/track-package", response_model=Union[SuccessResponse, ErrorResponse])
async def track_package(data: PackageTrackingRequest):
    """
    Track a package directly (shortcut for package tracking agent).
    
    This endpoint provides direct access to the package tracking functionality
    without going through the general chat interface. It can either accept
    a tracking number directly or a natural language query about tracking.
    
    Returns:
        Tracking information
    """
    try:
        # Handle both direct tracking number or natural language query
        tracking_number = data.tracking_number
        query = data.query
        
        if not tracking_number and not query:
            return {
                "success": False,
                "error": "Missing required field: tracking_number or query"
            }
        
        # Get brain instance asynchronously
        global _brain
        if _brain is None:
            _brain = await get_brain_async()
        
        # Create session ID - needed for conversation history
        session_id = str(uuid.uuid4())
        
        # Construct message and context
        message = query if query else f"Track my package with tracking number {tracking_number}"
        
        # Create mock response if the brain service is not fully initialized
        if not _brain or not hasattr(_brain, 'process_request'):
            logger.warning("Brain service not fully initialized, returning mock response")
            return {
                "success": True,
                "response": "I'm currently unable to track packages due to system maintenance. Please try again later.",
                "agent": "Package Tracking Agent",
                "session_id": session_id
            }
        
        try:
            # Process request with direct routing to the Package Tracking Agent via context
            response = await _brain.process_request(
                message=message, 
                session_id=session_id,
                context={
                    "agent_id": "f3056c69-a490-4336-8721-31912669a48d",  # Package Tracking Agent ID
                    "tracking_number": tracking_number,
                    "session_id": session_id,
                    "direct_routing": True  # Signal that this is a direct routing request
                }
            )
            
            return {
                "success": True,
                "response": response.get("response", "I'm sorry, I couldn't track that package."),
                "agent": "Package Tracking Agent",
                "session_id": session_id
            }
        except Exception as inner_e:
            logger.error(f"Error in brain.process_request: {str(inner_e)}", exc_info=True)
            # Fallback to a direct response without going through the agent
            return {
                "success": True,
                "response": "I'm sorry, our package tracking system is experiencing technical difficulties. Please try again later.",
                "agent": "Package Tracking Agent",
                "session_id": session_id
            }
        
    except Exception as e:
        logger.error(f"Error tracking package: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "response": "An error occurred while tracking your package"
        }

@api_router.post("/reset-password", response_model=Union[SuccessResponse, ErrorResponse])
async def reset_password(data: PasswordResetRequest):
    """
    Reset password directly (shortcut for reset password agent).
    
    This endpoint provides direct access to the password reset functionality
    without going through the general chat interface. It can accept an email,
    username, or a natural language query about resetting passwords.
    
    Returns:
        Password reset information
    """
    try:
        # Handle both structured data or natural language query
        email = data.email
        username = data.username
        query = data.query
        
        if not email and not username and not query:
            return {
                "success": False,
                "error": "Missing required field: email, username, or query"
            }
        
        # Get brain instance asynchronously
        global _brain
        if _brain is None:
            _brain = await get_brain_async()
        
        # Create session ID
        session_id = str(uuid.uuid4())
        
        # Construct message
        if query:
            message = query
        else:
            message = f"Reset password for "
            if email:
                message += f"email {email}"
            elif username:
                message += f"username {username}"
        
        # Create mock response if the brain service is not fully initialized
        if not _brain or not hasattr(_brain, 'process_request'):
            logger.warning("Brain service not fully initialized, returning mock response")
            return {
                "success": True,
                "response": "I'm currently unable to process password reset requests due to system maintenance. Please try again later.",
                "agent": "Reset Password Agent",
                "session_id": session_id
            }
        
        try:
            # Create context with forced agent routing
            context = {
                "agent_id": "9b65b143-699d-425f-84bf-e92f4634b972",  # Reset Password Agent ID
                "email": email,
                "username": username,
                "session_id": session_id,
                "direct_routing": True  # Signal that this is a direct routing request
            }
            
            # Process request with direct routing to the Reset Password Agent
            response = await _brain.process_request(
                message=message,
                session_id=session_id,
                context=context
            )
            
            return {
                "success": True,
                "response": response.get("response", "I'm sorry, I couldn't process your password reset request."),
                "agent": "Reset Password Agent",
                "session_id": session_id
            }
        except Exception as inner_e:
            logger.error(f"Error in brain.process_request: {str(inner_e)}", exc_info=True)
            # Fallback to a direct response without going through the agent
            return {
                "success": True,
                "response": "I'm sorry, our password reset system is experiencing technical difficulties. Please try again later.",
                "agent": "Reset Password Agent",
                "session_id": session_id
            }
        
        
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "response": "An error occurred while processing your password reset request"
        }
        
@api_router.post("/mock/reset-password", response_model=MockPasswordResetResponse)
async def mock_reset_password(data: MockPasswordResetRequest):
    """
    Mock endpoint for password reset API.
    
    This endpoint simulates a password reset request to an external API.
    It accepts an email and returns a success message.
    
    Request body:
    {
        "email": "user@example.com",
        "username": "optional-username",
        "account_type": "optional-account-type"
    }
    
    Returns:
        Mock password reset response
    """
    try:
        email = data.email
        username = data.username
        
        if not email and not username:
            return {
                "status": "error",
                "message": "Email or username required"
            }
        
        # Log the request
        logger.info(f"Mock password reset requested for: {email or username}")
        
        # Return success response
        return {
            "status": "success",
            "message": "We have sent an email with instructions to reset your password.",
            "reset_link_sent": True,
            "instructions": [
                "Check your email inbox for a password reset link.",
                "Click the link in the email to set a new password.",
                "If you don't see the email, check your spam or junk folder."
            ]
        }
        
    except Exception as e:
        logger.error(f"Error in mock reset password endpoint: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Error processing request: {str(e)}"
        }

@api_router.post("/chat", response_model=Union[SuccessResponse, ErrorResponse])
async def chat(data: ChatRequest):
    """
    Chat with Staples Brain using a unified interface.
    
    This endpoint handles chat messages and routes them to the appropriate agent
    based on intent detection or explicit agent selection.
    
    Request body:
    {
        "message": "I need to track my order",
        "session_id": "unique-session-id-123",
        "agent_id": "optional-explicit-agent-id"
    }
    
    Returns:
        Chat response from the appropriate agent
    """
    try:
        message = data.message
        session_id = data.session_id or str(uuid.uuid4())
        agent_id = data.agent_id  # Optional explicit agent selection
        
        # Get brain instance asynchronously
        global _brain
        if _brain is None:
            _brain = await get_brain_async()
        
        # Create mock response if the brain service is not fully initialized
        if not _brain or not hasattr(_brain, 'process_request'):
            logger.warning("Brain service not fully initialized, returning fallback response")
            return {
                "success": True,
                "response": "I'm currently initializing my systems. Please try again in a moment.",
                "agent": "General Conversation Agent",
                "session_id": session_id
            }
        
        try:
            # Create context with session info
            context = {
                "session_id": session_id
            }
            
            # If agent_id is specified, add it to context for direct routing
            if agent_id:
                context["agent_id"] = agent_id
                
            # Process request with the GraphBrainService
            response = await _brain.process_request(
                message=message, 
                session_id=session_id, 
                context=context
            )
            
            # Handle various response formats
            if isinstance(response, dict):
                return {
                    "success": True,
                    "response": response.get("response", "I'm sorry, I couldn't process your request."),
                    "agent": response.get("agent", "Unknown"),
                    "session_id": session_id
                }
            elif isinstance(response, str):
                # Handle case where response is just a string
                return {
                    "success": True,
                    "response": response,
                    "agent": "General Conversation Agent",
                    "session_id": session_id
                }
            else:
                # Unknown response format
                logger.warning(f"Unexpected response format from brain: {type(response)}")
                return {
                    "success": True,
                    "response": "I processed your request but encountered an issue with my response format.",
                    "agent": "General Conversation Agent",
                    "session_id": session_id
                }
                
        except Exception as inner_e:
            logger.error(f"Error in brain.process_request: {str(inner_e)}", exc_info=True)
            
            # Try to determine if there's a specific agent that might have failed
            agent_name = "General Conversation Agent"
            if agent_id and _brain and hasattr(_brain, '_agents') and _brain._agents:
                for agent_key, agent in _brain._agents.items():
                    if agent_key == agent_id and hasattr(agent, 'name'):
                        agent_name = agent.name
                        break
            
            # Provide a more helpful error message
            return {
                "success": True,
                "response": "I apologize, but I'm experiencing a technical issue with processing your request. Our team has been notified.",
                "agent": agent_name,
                "session_id": session_id
            }
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "response": "Sorry, I encountered an error. Please try again later."
        }