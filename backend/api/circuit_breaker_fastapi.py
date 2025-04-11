"""
Circuit breaker API endpoints.

This module provides API endpoints for monitoring and managing circuit breakers.

FastAPI version - migrated from Flask
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from utils.circuit_breaker import circuit_breaker_registry

logger = logging.getLogger(__name__)

# Define API response models
class CircuitBreakerResponse(BaseModel):
    """Response model for circuit breaker endpoints"""
    success: bool
    circuit_breaker: Optional[Dict[str, Any]] = None
    circuit_breakers: Optional[List[Dict[str, Any]]] = None
    message: Optional[str] = None
    error: Optional[str] = None

# Create a router for circuit breaker endpoints
circuit_breaker_router = APIRouter(prefix="/circuit-breakers", tags=["circuit-breakers"])


@circuit_breaker_router.get("/", response_model=CircuitBreakerResponse)
async def get_all_circuit_breakers():
    """
    Get the status of all circuit breakers.
    
    Returns:
        JSON response with circuit breaker states.
    """
    circuit_states = circuit_breaker_registry.get_all_circuit_states()
    return {
        "success": True,
        "circuit_breakers": circuit_states
    }


@circuit_breaker_router.get("/{name}", response_model=CircuitBreakerResponse)
async def get_circuit_breaker(name: str = Path(..., description="Name of the circuit breaker to get")):
    """
    Get the status of a specific circuit breaker.
    
    Args:
        name: Name of the circuit breaker to get.
        
    Returns:
        JSON response with circuit breaker state.
    """
    circuit_breaker = circuit_breaker_registry.get(name)
    if not circuit_breaker:
        raise HTTPException(
            status_code=404, 
            detail=f"Circuit breaker '{name}' not found"
        )
        
    circuit_state = circuit_breaker.get_state()
    return {
        "success": True,
        "circuit_breaker": circuit_state
    }


@circuit_breaker_router.post("/{name}/reset", response_model=CircuitBreakerResponse)
async def reset_circuit_breaker(name: str = Path(..., description="Name of the circuit breaker to reset")):
    """
    Reset a circuit breaker to closed state.
    
    Args:
        name: Name of the circuit breaker to reset.
        
    Returns:
        JSON response with reset status.
    """
    success = circuit_breaker_registry.reset(name)
    if not success:
        raise HTTPException(
            status_code=404, 
            detail=f"Circuit breaker '{name}' not found"
        )
        
    return {
        "success": True,
        "message": f"Circuit breaker '{name}' reset successfully"
    }