import logging
import json
from flask import Blueprint, request, jsonify, current_app
from brain.staples_brain import initialize_staples_brain
from api.agent_builder import agent_builder_bp
import asyncio

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
        context = data.get("context", {})
        
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
