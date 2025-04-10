import logging
import json
import importlib
import uuid
import asyncio
from flask import Blueprint, request, jsonify, current_app
from api.agent_builder import agent_builder_bp

logger = logging.getLogger(__name__)

# Create API blueprint
api_bp = Blueprint("api", __name__, url_prefix="/api")

# Register the agent builder blueprint
api_bp.register_blueprint(agent_builder_bp, url_prefix="/builder")

# Store brain instance
_brain = None

def get_brain():
    """
    Get or initialize the Staples Brain instance.
    
    Returns:
        StaplesBrain instance
    """
    global _brain
    if _brain is None:
        # Import here to avoid circular imports
        from brain.staples_brain import initialize_staples_brain
        _brain = initialize_staples_brain()
    return _brain

@api_bp.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status
    """
    try:
        brain = get_brain()
        agent_names = brain.get_agent_names()
        return jsonify({
            "status": "healthy",
            "message": "Staples Brain is running",
            "version": "1.0.0",
            "agents": agent_names
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return jsonify({
            "status": "unhealthy",
            "message": f"Error: {str(e)}"
        }), 500

@api_bp.route("/process", methods=["POST"])
def process_request():
    """
    Process a user request.
    
    Returns:
        Agent response
    """
    try:
        data = request.json
        
        if not data or "input" not in data:
            return jsonify({
                "success": False,
                "error": "Missing required field: input"
            }), 400
        
        user_input = data["input"]
        session_id = data.get("session_id")
        context = data.get("context", {})
        
        # Add session_id to context if provided
        if session_id:
            if not context:
                context = {}
            context["session_id"] = session_id
        
        # Get brain instance
        brain = get_brain()
        
        # Process request (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(brain.process_request(user_input, context))
        loop.close()
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "response": "An error occurred while processing your request"
        }), 500

@api_bp.route("/agents", methods=["GET"])
def list_agents():
    """
    List all available agents.
    
    Returns:
        List of agents
    """
    try:
        brain = get_brain()
        agent_names = brain.get_agent_names()
        
        return jsonify({
            "success": True,
            "agents": agent_names
        })
        
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
        
@api_bp.route("/generate-entity-definitions", methods=["POST"])
def generate_entity_definitions():
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
        data = request.json
        
        if not data or not data.get("entities"):
            return jsonify({
                "success": False,
                "error": "No entities provided"
            }), 400
            
        entities = data.get("entities", [])
        
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
        result = {
            "success": True,
            "setup_code": setup_code,
            "entity_count": len(entities),
            "doc": "Insert this setup_entity_definitions method into your agent class and call it from the __init__ method."
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error generating entity definitions: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@api_bp.route("/track-package", methods=["POST"])
def track_package():
    """
    Track a package directly (shortcut for package tracking agent).
    
    Returns:
        Tracking information
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Missing request body"
            }), 400
        
        # Handle both direct tracking number or natural language query
        tracking_number = data.get("tracking_number")
        query = data.get("query")
        
        if not tracking_number and not query:
            return jsonify({
                "success": False,
                "error": "Missing required field: tracking_number or query"
            }), 400
        
        brain = get_brain()
        
        # Find package tracking agent
        package_agent = brain.get_agent_by_name("Package Tracking Agent")
        
        if not package_agent:
            return jsonify({
                "success": False,
                "error": "Package tracking agent not available"
            }), 500
        
        # Construct input and context
        user_input = query if query else f"Track my package with tracking number {tracking_number}"
        context = {
            "agent_name": "Package Tracking Agent",
            "tracking_number": tracking_number
        }
        
        # Process request (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(package_agent.process(user_input, context))
        loop.close()
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error tracking package: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "response": "An error occurred while tracking your package"
        }), 500

@api_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """
    Reset password directly (shortcut for reset password agent).
    
    Returns:
        Password reset information
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Missing request body"
            }), 400
        
        # Handle both structured data or natural language query
        email = data.get("email")
        username = data.get("username")
        query = data.get("query")
        
        if not email and not username and not query:
            return jsonify({
                "success": False,
                "error": "Missing required field: email, username, or query"
            }), 400
        
        brain = get_brain()
        
        # Find reset password agent
        reset_agent = brain.get_agent_by_name("Reset Password Agent")
        
        if not reset_agent:
            return jsonify({
                "success": False,
                "error": "Reset password agent not available"
            }), 500
        
        # Construct input and context
        if query:
            user_input = query
        else:
            user_input = f"Reset password for "
            if email:
                user_input += f"email {email}"
            elif username:
                user_input += f"username {username}"
        
        context = {
            "agent_name": "Reset Password Agent",
            "email": email,
            "username": username
        }
        
        # Process request (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(reset_agent.process(user_input, context))
        loop.close()
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "response": "An error occurred while processing your password reset request"
        }), 500
        
@api_bp.route("/mock/reset-password", methods=["POST"])
def mock_reset_password():
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
        data = request.json
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "Missing request body"
            }), 400
        
        email = data.get("email")
        username = data.get("username")
        
        if not email and not username:
            return jsonify({
                "status": "error",
                "message": "Email or username required"
            }), 400
        
        # Log the request
        logger.info(f"Mock password reset requested for: {email or username}")
        
        # Return success response
        return jsonify({
            "status": "success",
            "message": "We have sent an email with instructions to reset your password.",
            "reset_link_sent": True,
            "instructions": [
                "Check your email inbox for a password reset link.",
                "Click the link in the email to set a new password.",
                "If you don't see the email, check your spam or junk folder."
            ]
        })
        
    except Exception as e:
        logger.error(f"Error in mock reset password endpoint: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Error processing request: {str(e)}"
        }), 500

@api_bp.route("/chat", methods=["POST"])
def chat():
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
        data = request.json
        
        if not data or not data.get("message"):
            return jsonify({
                "success": False,
                "error": "Missing required field: message"
            }), 400
        
        message = data.get("message")
        session_id = data.get("session_id", str(uuid.uuid4()))
        agent_id = data.get("agent_id")  # Optional explicit agent selection
        
        # Get brain instance
        brain = get_brain()
        
        # Create context with session info
        context = {
            "session_id": session_id
        }
        
        # If agent_id is specified, add it to context for direct routing
        if agent_id:
            context["agent_id"] = agent_id
            
        # Process request (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(brain.process_request(message, context))
        loop.close()
        
        return jsonify({
            "success": True,
            "response": response.get("response", "I'm sorry, I couldn't process your request."),
            "agent": response.get("agent", "Unknown"),
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e),
            "response": "Sorry, I encountered an error. Please try again later."
        }), 500
