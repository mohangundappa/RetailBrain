"""
API endpoints for chat processing.
This module provides endpoints for processing chat messages and returning telemetry data.
"""
import logging
import uuid
import asyncio
from flask import Blueprint, jsonify, request, current_app

# Import the telemetry system directly for consistency
from brain.restructured.telemetry import telemetry_system, collector as telemetry_collector

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
            
        # Create explicit telemetry entry for this request
        telemetry_collector.track_request_received(session_id, user_input)
        
        # Get context from memory if available
        brain = current_app.staples_brain
        # Safely check for memory attribute and get context
        context = None
        try:
            if hasattr(brain, 'memory') and brain.memory:
                context = brain.memory.get_context(session_id)
        except Exception as e:
            logger.warning(f"Could not retrieve memory context: {e}")
        
        # Process request using the Staples Brain directly
        result = {}
        try:
            # Process with orchestrator directly, which handles telemetry internally
            brain = current_app.staples_brain
            response_text = "I'm sorry, I couldn't process your request properly."
            
            if brain:
                # This will use the orchestrator with telemetry
                # Try to use process_request, which is the correct method name
                import asyncio
                # Set the session_id if exists in brain.process_request signature
                try:
                    import inspect
                    # Check if session_id is accepted in process_request
                    sig = inspect.signature(brain.process_request)
                    if 'session_id' in sig.parameters:
                        response = asyncio.run(brain.process_request(user_input, session_id=session_id, context=context))
                    else:
                        # If not, just pass the user input and context
                        response = asyncio.run(brain.process_request(user_input, context=context))
                except Exception as e:
                    logger.warning(f"Error inspecting brain.process_request: {e}")
                    # Fall back to just the basic parameters
                    response = asyncio.run(brain.process_request(user_input, context=context))
                response_text = response.get('response', response_text)
                selected_agent = response.get('selected_agent')
                confidence = response.get('confidence')
                result = {
                    "response": response_text,
                    "agent": selected_agent,
                    "confidence": confidence
                }
                
                # Add extra telemetry events in case the brain didn't track them
                if selected_agent:
                    # Track the agent selection with the right parameters
                    telemetry_collector.track_agent_selection(
                        session_id=session_id, 
                        agent_name=selected_agent, 
                        confidence=confidence or 0.5, 
                        selection_method="manual_tracking_from_chat_api", 
                        parent_id=None
                    )
                
                # Track response generation with the right parameters
                telemetry_collector.track_response_generation(
                    session_id=session_id, 
                    agent_name=selected_agent or "unknown",
                    success=True, 
                    response_type="text", 
                    processing_time=0.5, 
                    parent_id=None
                )
            else:
                # Fallback response if brain is not available
                result = {"response": "I'm having trouble accessing my brain right now."}
                
        except Exception as e:
            logger.error(f"Error processing with brain: {e}", exc_info=True)
            result = {"response": "I'm having trouble processing your request right now."}
        
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