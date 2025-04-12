"""
API endpoints for circuit breaker monitoring and management.

This module provides API endpoints to monitor the state of circuit breakers
and perform management actions like reset.
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Path, Depends

from backend.utils.circuit_breaker import get_circuit_status, reset_circuit, reset_all_circuits

logger = logging.getLogger(__name__)

# Create API response models
class CircuitStatus(BaseModel):
    """Model for circuit breaker status response."""
    name: str
    state: str
    failure_count: int
    success_count: int
    last_failure_time: Optional[str] = None
    recovery_timeout: int

class CircuitStatusResponse(BaseModel):
    """Model for response containing all circuit statuses."""
    circuits: List[CircuitStatus]

class CircuitResetRequest(BaseModel):
    """Model for circuit reset request."""
    name: str

class CircuitResetResponse(BaseModel):
    """Model for circuit reset response."""
    success: bool
    message: str

class AllCircuitsResetResponse(BaseModel):
    """Model for response when resetting all circuits."""
    success: bool
    count: int
    message: str

# Create the router
router = APIRouter(
    prefix="/circuit-management",
    tags=["circuit-management"]
)

@router.get("/status", response_model=CircuitStatusResponse)
async def get_all_circuit_status():
    """
    Get the status of all circuit breakers in the system.
    
    Returns:
        CircuitStatusResponse: List of circuit breaker status objects
    """
    try:
        status = get_circuit_status()
        circuits = []
        
        for name, details in status.items():
            circuits.append(CircuitStatus(
                name=name,
                state=details['state'],
                failure_count=details['failure_count'],
                success_count=details['success_count'],
                last_failure_time=details['last_failure_time'],
                recovery_timeout=details['recovery_timeout']
            ))
            
        return CircuitStatusResponse(circuits=circuits)
    
    except Exception as e:
        logger.error(f"Error getting circuit status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting circuit status: {str(e)}"
        )

@router.post("/reset", response_model=CircuitResetResponse)
async def reset_single_circuit(request: CircuitResetRequest):
    """
    Reset a specific circuit breaker to its initial state.
    
    Args:
        request (CircuitResetRequest): Request containing the circuit name
        
    Returns:
        CircuitResetResponse: Result of the reset operation
        
    Raises:
        HTTPException: If the circuit doesn't exist or there's an error
    """
    try:
        success = reset_circuit(request.name)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Circuit breaker '{request.name}' not found"
            )
            
        logger.info(f"Circuit breaker '{request.name}' reset successfully")
        
        return CircuitResetResponse(
            success=True,
            message=f"Circuit breaker '{request.name}' reset successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(f"Error resetting circuit '{request.name}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting circuit: {str(e)}"
        )

@router.post("/reset-all", response_model=AllCircuitsResetResponse)
async def reset_all_circuit_breakers():
    """
    Reset all circuit breakers to their initial state.
    
    Returns:
        AllCircuitsResetResponse: Result of the reset operation
    """
    try:
        # Get the count before resetting
        status = get_circuit_status()
        count = len(status)
        
        # Reset all circuits
        reset_all_circuits()
        
        logger.info(f"All {count} circuit breakers reset successfully")
        
        return AllCircuitsResetResponse(
            success=True,
            count=count,
            message=f"All {count} circuit breakers reset successfully"
        )
        
    except Exception as e:
        logger.error(f"Error resetting all circuits: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting all circuits: {str(e)}"
        )