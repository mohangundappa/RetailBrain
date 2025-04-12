"""
Utility functions for API handling.
"""
import logging
from typing import Any, Dict, Optional, List, Union

# Set up logging
logger = logging.getLogger("staples_brain")

def create_success_response(
    data: Optional[Union[Dict[str, Any], List[Any]]] = None, 
    metadata: Optional[Dict[str, Any]] = None,
    agents: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    Create a standardized success response.
    
    Args:
        data: The response data
        metadata: Optional metadata
        agents: Optional list of agents for agent endpoints
        
    Returns:
        A standardized success response dictionary
    """
    response = {
        "success": True,
        "error": None
    }
    
    # Include metadata if provided
    if metadata:
        response["metadata"] = metadata
        
    # If agents specified, include agents list (for agent endpoints)
    if agents is not None:
        response["agents"] = agents
    # Otherwise include data
    elif data is not None:
        response["data"] = data
    else:
        response["data"] = {}
        
    return response

def create_error_response(
    error_message: str,
    data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    log_error: bool = True
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        error_message: The error message
        data: Optional data to include
        metadata: Optional metadata
        log_error: Whether to log the error
        
    Returns:
        A standardized error response dictionary
    """
    if log_error:
        logger.error(error_message)
        
    return {
        "success": False,
        "error": error_message,
        "data": data or {},
        "metadata": metadata
    }

def create_versioned_response(
    data: Dict[str, Any],
    version: str,
    deprecation_status: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a response with version information.
    
    Args:
        data: The response data
        version: API version
        deprecation_status: Optional deprecation status
        
    Returns:
        A response with version information included
    """
    response = create_success_response(data=data)
    
    if not response.get("metadata"):
        response["metadata"] = {}
        
    response["metadata"]["version"] = version
    
    if deprecation_status:
        response["metadata"]["deprecation"] = deprecation_status
        
    return response