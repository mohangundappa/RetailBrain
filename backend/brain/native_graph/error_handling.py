"""
Error handling and recovery module for LangGraph orchestration.

This module provides standardized error handling, classification, and recovery
functions for use within LangGraph node functions and the orchestrator.
"""

import logging
import traceback
import json
import time
from typing import Dict, Any, List, Optional, Tuple, Callable, TypeVar, Union
from datetime import datetime
from functools import wraps

from backend.brain.native_graph.state_definitions import OrchestrationState

logger = logging.getLogger(__name__)

# Define error types for better categorization
class ErrorType:
    """Error type constants for categorization."""
    # Input errors
    INVALID_INPUT = "invalid_input"
    MISSING_PARAMETER = "missing_parameter"
    
    # Processing errors
    PARSING_ERROR = "parsing_error"
    JSON_DECODE_ERROR = "json_decode_error"
    
    # Agent errors
    AGENT_NOT_FOUND = "agent_not_found"
    AGENT_EXECUTION_ERROR = "agent_execution_error"
    AGENT_TIMEOUT = "agent_timeout"
    
    # LLM errors
    LLM_API_ERROR = "llm_api_error"
    LLM_RATE_LIMIT = "llm_rate_limit"
    LLM_CONTEXT_LIMIT = "llm_context_limit"
    
    # System errors
    DATABASE_ERROR = "database_error"
    MEMORY_ERROR = "memory_error"
    ORCHESTRATION_ERROR = "orchestration_error"
    STATE_PERSISTENCE_ERROR = "state_persistence_error"
    
    # Unknown errors
    UNKNOWN = "unknown"


def classify_error(error: Exception) -> str:
    """
    Classify an exception into one of the error types.
    
    Args:
        error: The exception to classify
        
    Returns:
        Error type string
    """
    error_type = ErrorType.UNKNOWN
    error_str = str(error)
    error_class = error.__class__.__name__
    
    # Check for JSON parsing errors
    if error_class == "JSONDecodeError":
        error_type = ErrorType.JSON_DECODE_ERROR
    
    # Check for LLM API errors
    elif "openai" in error_class.lower() or "openai" in error_str.lower():
        if "rate limit" in error_str.lower():
            error_type = ErrorType.LLM_RATE_LIMIT
        elif "maximum context length" in error_str.lower():
            error_type = ErrorType.LLM_CONTEXT_LIMIT
        else:
            error_type = ErrorType.LLM_API_ERROR
    
    # Check for database errors
    elif "database" in error_str.lower() or "sql" in error_class.lower():
        error_type = ErrorType.DATABASE_ERROR
    
    # Check for state persistence errors
    elif "state" in error_str.lower() and "persist" in error_str.lower():
        error_type = ErrorType.STATE_PERSISTENCE_ERROR
    elif "orchestration_state" in error_str.lower():
        error_type = ErrorType.STATE_PERSISTENCE_ERROR
    elif "checkpoint" in error_str.lower() and ("save" in error_str.lower() or "load" in error_str.lower()):
        error_type = ErrorType.STATE_PERSISTENCE_ERROR
    
    # Check for agent errors
    elif "agent not found" in error_str.lower():
        error_type = ErrorType.AGENT_NOT_FOUND
    elif "agent" in error_str.lower() and "execution" in error_str.lower():
        error_type = ErrorType.AGENT_EXECUTION_ERROR
    elif "timeout" in error_str.lower():
        error_type = ErrorType.AGENT_TIMEOUT
    
    return error_type


def record_error(
    state: OrchestrationState,
    node_name: str,
    error: Exception,
    error_type: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None
) -> OrchestrationState:
    """
    Record an error in the execution state.
    
    Args:
        state: Current orchestration state
        node_name: Name of the node where the error occurred
        error: The exception that was raised
        error_type: Optional error type for categorization
        additional_info: Optional additional information about the error
        
    Returns:
        Updated state with error recorded
    """
    # Create a new state to avoid modifying the input
    new_state = {**state}
    
    # Determine error type if not provided
    if error_type is None:
        error_type = classify_error(error)
    
    # Extract execution state
    execution = {**new_state.get("execution", {})}
    errors = execution.get("errors", [])
    
    # Build error record
    error_record = {
        "node": node_name,
        "error": str(error),
        "error_type": error_type,
        "timestamp": datetime.now().isoformat(),
        "traceback": traceback.format_exc()
    }
    
    # Add additional info if provided
    if additional_info:
        error_record["additional_info"] = additional_info
    
    # Add error to list
    errors.append(error_record)
    execution["errors"] = errors
    
    # Update state
    new_state["execution"] = execution
    
    # Log the error for monitoring
    logger.error(
        f"Error in node {node_name}: {str(error)} (type: {error_type})",
        exc_info=True
    )
    
    return new_state


def get_error_recovery_response(
    state: OrchestrationState,
    error: Exception,
    error_type: Optional[str] = None
) -> str:
    """
    Generate an appropriate user-facing error message.
    
    Args:
        state: Current orchestration state
        error: The exception that occurred
        error_type: Optional error type for categorization
        
    Returns:
        User-friendly error message
    """
    # Determine error type if not provided
    if error_type is None:
        error_type = classify_error(error)
    
    # Get conversation context
    conversation = state.get("conversation", {})
    last_user_message = conversation.get("last_user_message", "")
    
    # Generate appropriate response based on error type
    if error_type == ErrorType.JSON_DECODE_ERROR:
        return "I'm having trouble understanding my own thoughts right now. Let me try again with your request."
    
    elif error_type == ErrorType.LLM_RATE_LIMIT:
        return "I'm experiencing a lot of traffic right now. Please try again in a moment."
    
    elif error_type == ErrorType.LLM_CONTEXT_LIMIT:
        return "This conversation is getting quite detailed. Could we focus on one aspect at a time?"
    
    elif error_type == ErrorType.LLM_API_ERROR:
        return "I'm having trouble connecting to my knowledge base. Let's try again, perhaps with a simpler request."
    
    elif error_type == ErrorType.AGENT_NOT_FOUND:
        return "I don't seem to have the right expert available for this request. Is there another way I can help you?"
    
    elif error_type == ErrorType.AGENT_EXECUTION_ERROR:
        return "I ran into an issue processing your request. Could you provide more details or try a different approach?"
    
    elif error_type == ErrorType.STATE_PERSISTENCE_ERROR:
        return "I'm having trouble saving our conversation. Your request was processed, but we might need to repeat some information if we continue."
    
    elif error_type == ErrorType.DATABASE_ERROR:
        return "I'm experiencing a technical issue with my memory. Let's continue, but I might need you to repeat information you've shared before."
    
    # Default generic error message
    return "I apologize, but I encountered an issue while processing your request. Could you try again or rephrase your question?"


def with_error_handling(node_name: str):
    """
    Decorator for node functions to add standardized error handling.
    
    Args:
        node_name: Name of the node being decorated
        
    Returns:
        Decorated function
    """
    NodeFuncType = Callable[[OrchestrationState], OrchestrationState]
    
    def decorator(func: NodeFuncType) -> NodeFuncType:
        @wraps(func)
        def wrapper(state: OrchestrationState) -> OrchestrationState:
            try:
                # Add performance tracking
                start_time = time.time()
                
                # Execute the node function
                result = func(state)
                
                # Record performance metrics
                execution_time = time.time() - start_time
                
                # Update execution metrics in the state
                execution = {**result.get("execution", {})}
                performance = execution.get("performance", {})
                performance[node_name] = execution_time
                execution["performance"] = performance
                result["execution"] = execution
                
                logger.debug(f"Node {node_name} executed in {execution_time:.4f} seconds")
                return result
                
            except Exception as e:
                # Record the error in the state
                new_state = record_error(state, node_name, e)
                
                # Get user-facing error message
                error_message = get_error_recovery_response(new_state, e)
                
                # Add agent state for error recovery
                agent_state = {**new_state.get("agent", {})}
                agent_state["special_case_detected"] = True
                agent_state["special_case_type"] = "error_recovery"
                agent_state["special_case_response"] = error_message
                new_state["agent"] = agent_state
                
                return new_state
        
        return wrapper
    
    return decorator


def parse_json_with_recovery(
    json_str: str,
    default_value: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Parse a JSON string with error recovery.
    
    Args:
        json_str: JSON string to parse
        default_value: Default value to return if parsing fails
        
    Returns:
        Parsed JSON object or default value if parsing fails
    """
    if default_value is None:
        default_value = {}
        
    # First, try direct parsing
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing error: {str(e)}")
        logger.debug(f"Raw JSON string: {json_str}")
        
    # Direct parsing failed, try recovery techniques
    
    # Look for the start of a JSON object
    try:
        # Find the first occurrence of '{'
        start_idx = json_str.find('{')
        if start_idx >= 0:
            # Find the last occurrence of '}'
            end_idx = json_str.rfind('}')
            if end_idx > start_idx:
                # Extract the substring and try parsing again
                json_extract = json_str[start_idx:end_idx+1]
                return json.loads(json_extract)
    except Exception:
        pass
    
    # Return default value if all recovery methods fail
    logger.error(f"Failed to parse JSON: {json_str}")
    return default_value


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    retry_on: List[str] = None
):
    """
    Decorator for retrying functions on specific errors.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff_factor: Factor to increase delay on each retry
        retry_on: List of error types to retry on (default: rate limits and state persistence)
        
    Returns:
        Decorated function
    """
    if retry_on is None:
        retry_on = [ErrorType.LLM_RATE_LIMIT, ErrorType.STATE_PERSISTENCE_ERROR]
        
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    error_type = classify_error(e)
                    
                    # Only retry on specified error types
                    if error_type not in retry_on:
                        raise
                    
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Maximum retries ({max_retries}) reached, giving up")
                        raise
                    
                    logger.warning(
                        f"Retry {retries}/{max_retries} after error: {str(e)} "
                        f"(type: {error_type}). Waiting {current_delay:.2f}s"
                    )
                    
                    # Wait before retrying
                    import asyncio
                    await asyncio.sleep(current_delay)
                    
                    # Increase delay for next retry
                    current_delay *= backoff_factor
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_type = classify_error(e)
                    
                    # Only retry on specified error types
                    if error_type not in retry_on:
                        raise
                    
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"Maximum retries ({max_retries}) reached, giving up")
                        raise
                    
                    logger.warning(
                        f"Retry {retries}/{max_retries} after error: {str(e)} "
                        f"(type: {error_type}). Waiting {current_delay:.2f}s"
                    )
                    
                    # Wait before retrying
                    import time
                    time.sleep(current_delay)
                    
                    # Increase delay for next retry
                    current_delay *= backoff_factor
        
        # Determine if the function is async or sync
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator