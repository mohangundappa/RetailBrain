"""
API endpoints for chat processing.
This module provides endpoints for processing chat messages and returning telemetry data.
"""
import logging
import uuid
from flask import Blueprint, jsonify, request, current_app

logger = logging.getLogger(__name__)

# Create blueprint
chat_blueprint = Blueprint('chat', __name__)


@chat_blueprint.route('/api/process-request', methods=['POST'])
def process_chat_request():
    """
    Process a chat request and return the response with optional telemetry session ID.
    
    Expects JSON with:
    - user_input: The user's message
    - session_id: (Optional) Existing session ID
    - generate_session_id: (Optional) Boolean to generate a new telemetry session ID
    
    Returns:
        JSON response with bot's answer and session ID for telemetry
    """
    try:
        # Parse request data
        data = request.json
        user_input = data.get('user_input')
        session_id = data.get('session_id')
        generate_session_id = data.get('generate_session_id', False)
        
        if not user_input:
            return jsonify({"error": "Missing required parameter: user_input"}), 400
            
        # Create a session ID if requested or if none provided
        if generate_session_id or not session_id:
            session_id = str(uuid.uuid4())
        
        # Get context from memory if available
        brain = current_app.staples_brain
        context = brain.memory.get_context(session_id) if brain.memory else None
        
        # Process request through main processing function
        # This adds all the telemetry automatically
        result = current_app.process_request(user_input=user_input, session_id=session_id, context=context)
        
        # Extract the response text
        response_text = result.get('response', "I'm sorry, I'm having trouble processing your request right now.")
        
        # Return response with session ID for telemetry tracking
        return jsonify({
            "success": True,
            "response": response_text,
            "session_id": session_id
        })
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "An error occurred processing your request",
            "details": str(e),
            "response": "I'm sorry, but I encountered an error processing your request. Please try again."
        }), 500