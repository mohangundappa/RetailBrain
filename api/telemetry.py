"""
API endpoints for telemetry data.
This module provides access to the orchestration telemetry for monitoring and debugging.
"""
import logging
from flask import Blueprint, jsonify, request
from typing import Dict, Any, List, Optional

from brain.telemetry import telemetry_system

logger = logging.getLogger(__name__)

# Create blueprint
telemetry_blueprint = Blueprint('telemetry', __name__)


@telemetry_blueprint.route('/api/telemetry/sessions', methods=['GET'])
def get_sessions():
    """
    Get recent telemetry sessions.
    
    Returns:
        JSON response with session IDs
    """
    limit = request.args.get('limit', 5, type=int)
    sessions = telemetry_system.get_latest_sessions(limit)
    
    return jsonify({
        "success": True,
        "sessions": sessions
    })


@telemetry_blueprint.route('/api/telemetry/sessions/<session_id>', methods=['GET'])
def get_session_events(session_id):
    """
    Get events for a specific session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        JSON response with events
    """
    events = telemetry_system.get_session_events(session_id)
    
    return jsonify({
        "success": True,
        "session_id": session_id,
        "event_count": len(events),
        "events": events
    })


@telemetry_blueprint.route('/api/telemetry/sessions/<session_id>', methods=['DELETE'])
def clear_session(session_id):
    """
    Clear events for a specific session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        JSON confirmation
    """
    telemetry_system.clear_session(session_id)
    
    return jsonify({
        "success": True,
        "message": f"Cleared telemetry for session {session_id}"
    })


@telemetry_blueprint.route('/api/telemetry/sessions', methods=['DELETE'])
def clear_all_sessions():
    """
    Clear all telemetry sessions.
    
    Returns:
        JSON confirmation
    """
    telemetry_system.clear_all_sessions()
    
    return jsonify({
        "success": True,
        "message": "Cleared all telemetry sessions"
    })