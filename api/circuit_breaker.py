"""
Circuit breaker API endpoints.

This module provides API endpoints for monitoring and managing circuit breakers.
"""

import logging
from typing import Dict, Any, List
from flask import Blueprint, jsonify, request

from utils.circuit_breaker import circuit_breaker_registry

logger = logging.getLogger(__name__)

# Create a blueprint for circuit breaker endpoints
circuit_breaker_api = Blueprint('circuit_breaker_api', __name__)


@circuit_breaker_api.route('/api/circuit-breakers', methods=['GET'])
def get_all_circuit_breakers() -> Dict[str, Any]:
    """
    Get the status of all circuit breakers.
    
    Returns:
        JSON response with circuit breaker states.
    """
    circuit_states = circuit_breaker_registry.get_all_circuit_states()
    return jsonify({
        "success": True,
        "circuit_breakers": circuit_states
    })


@circuit_breaker_api.route('/api/circuit-breakers/<name>', methods=['GET'])
def get_circuit_breaker(name: str) -> Dict[str, Any]:
    """
    Get the status of a specific circuit breaker.
    
    Args:
        name: Name of the circuit breaker to get.
        
    Returns:
        JSON response with circuit breaker state.
    """
    circuit_breaker = circuit_breaker_registry.get(name)
    if not circuit_breaker:
        return jsonify({
            "success": False,
            "error": f"Circuit breaker '{name}' not found"
        }), 404
        
    circuit_state = circuit_breaker.get_state()
    return jsonify({
        "success": True,
        "circuit_breaker": circuit_state
    })


@circuit_breaker_api.route('/api/circuit-breakers/<name>/reset', methods=['POST'])
def reset_circuit_breaker(name: str) -> Dict[str, Any]:
    """
    Reset a circuit breaker to closed state.
    
    Args:
        name: Name of the circuit breaker to reset.
        
    Returns:
        JSON response with reset status.
    """
    success = circuit_breaker_registry.reset(name)
    if not success:
        return jsonify({
            "success": False,
            "error": f"Circuit breaker '{name}' not found"
        }), 404
        
    return jsonify({
        "success": True,
        "message": f"Circuit breaker '{name}' reset successfully"
    })