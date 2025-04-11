"""
LangSmith utilities for Staples Brain.

This module provides functions for integrating LangSmith with the Staples Brain services
for enhanced observability, tracing, and debugging of LLM interactions.
"""
import os
import logging
import inspect
import time
import traceback
from typing import Dict, Any, List, Optional, Union, Callable
from functools import wraps
from datetime import datetime

# Import LangSmith
from langsmith import Client
from langsmith.run_helpers import traceable
from langsmith.schemas import Run, RunTypeEnum

def init_langsmith():
    """
    Initialize LangSmith for telemetry.
    This function checks for the LANGSMITH_API_KEY environment variable and
    initializes LangSmith client if available.
    """
    api_key = os.environ.get("LANGSMITH_API_KEY")
    if api_key:
        logger = logging.getLogger("staples_brain")
        logger.info("LangSmith API key found, enabling telemetry")
        try:
            # Just create a client to verify the API key works
            client = Client()
            logger.info("LangSmith initialized successfully")
            return client
        except Exception as e:
            logger.warning(f"Failed to initialize LangSmith: {str(e)}")
    return None

logger = logging.getLogger(__name__)

# Internal logging functions to avoid circular imports
def _log_api_call(system: str, endpoint: str, duration_ms: float = 0, status_code: int = 200):
    """
    Internal function to log API calls without relying on observability module.
    This prevents circular imports.
    """
    logger.info(f"API call to {system}/{endpoint} completed with status {status_code} in {duration_ms:.2f}ms")

def _log_error(error_type: str, message: str, traceback_str: Optional[str] = None):
    """
    Internal function to log errors without relying on observability module.
    This prevents circular imports.
    """
    logger.error(f"{error_type}: {message}")
    if traceback_str:
        logger.debug(f"Traceback: {traceback_str}")

# Initialize langsmith client
try:
    LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.environ.get("LANGSMITH_PROJECT", "staples_brain")
    
    langsmith_client = Client(api_key=LANGSMITH_API_KEY) if LANGSMITH_API_KEY else None
    
    if langsmith_client:
        logger.info("LangSmith client initialized")
    else:
        logger.warning("LangSmith client not initialized: Missing LANGSMITH_API_KEY")
        
except Exception as e:
    logger.error(f"Error initializing LangSmith client: {str(e)}")
    langsmith_client = None


def langsmith_trace(run_type: str = "chain", name: Optional[str] = None, 
                    project_name: Optional[str] = None, tags: Optional[List[str]] = None):
    """
    Decorator for tracing function execution with LangSmith.
    
    Args:
        run_type: Type of run to record (chain, llm, tool)
        name: Name for the run
        project_name: Project name for the run
        tags: Tags to add to the run
        
    Returns:
        Decorator function
    """
    def decorator(func):
        if not langsmith_client:
            # If LangSmith is not available, just return the original function
            return func
            
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = name or func.__name__
            project = project_name or LANGSMITH_PROJECT
            
            # Extract caller information for better tracing
            caller_frame = inspect.currentframe().f_back
            caller_info = ""
            if caller_frame:
                caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}"
            
            # Create metadata
            metadata = {
                "function": func.__name__,
                "module": func.__module__,
                "caller": caller_info,
                "args": str(args),
                "kwargs": str(kwargs),
            }
            
            # Create run tags
            run_tags = tags or []
            run_tags.extend(["staples_brain", "core_service", run_type])
            
            # Trace the function execution
            try:
                with langsmith_client.as_run(
                    name=func_name,
                    run_type=run_type,
                    project_name=project,
                    metadata=metadata,
                    tags=run_tags,
                ):
                    start_time = time.time()
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Record this as an API call for internal metrics
                    _log_api_call(
                        system="langsmith",
                        endpoint=func_name,
                        duration_ms=duration * 1000,
                        status_code=200
                    )
                    
                    return result
                    
            except Exception as e:
                # Record error
                error_message = f"Error in {func_name}: {str(e)}"
                logger.error(error_message)
                _log_error("langsmith_trace", error_message, traceback.format_exc())
                
                # Re-raise the exception
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = name or func.__name__
            project = project_name or LANGSMITH_PROJECT
            
            # Extract caller information for better tracing
            caller_frame = inspect.currentframe().f_back
            caller_info = ""
            if caller_frame:
                caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}"
            
            # Create metadata
            metadata = {
                "function": func.__name__,
                "module": func.__module__,
                "caller": caller_info,
                "args": str(args),
                "kwargs": str(kwargs),
            }
            
            # Create run tags
            run_tags = tags or []
            run_tags.extend(["staples_brain", "core_service", run_type])
            
            # Trace the function execution
            try:
                with langsmith_client.as_run(
                    name=func_name,
                    run_type=run_type,
                    project_name=project,
                    metadata=metadata,
                    tags=run_tags,
                ):
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Record this as an API call for internal metrics
                    _log_api_call(
                        system="langsmith",
                        endpoint=func_name,
                        duration_ms=duration * 1000,
                        status_code=200
                    )
                    
                    return result
                    
            except Exception as e:
                # Record error
                error_message = f"Error in {func_name}: {str(e)}"
                logger.error(error_message)
                _log_error("langsmith_trace", error_message, traceback.format_exc())
                
                # Re-raise the exception
                raise
        
        # Use the async wrapper if the function is async, otherwise use the sync wrapper
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


def create_langsmith_run(name: str, inputs: Dict[str, Any], run_type: str = "chain",
                        project_name: Optional[str] = None, 
                        tags: Optional[List[str]] = None) -> Optional[Run]:
    """
    Create a LangSmith run manually.
    
    Args:
        name: Name for the run
        inputs: Input data for the run
        run_type: Type of run to record (chain, llm, tool)
        project_name: Project name for the run
        tags: Tags to add to the run
        
    Returns:
        Run object if successful, None otherwise
    """
    if not langsmith_client:
        return None
        
    try:
        # Create run
        run = langsmith_client.create_run(
            name=name,
            inputs=inputs,
            run_type=RunTypeEnum(run_type),
            project_name=project_name or LANGSMITH_PROJECT,
            tags=tags or ["staples_brain", "manual", run_type],
        )
        
        return run
        
    except Exception as e:
        logger.error(f"Error creating LangSmith run: {str(e)}")
        return None


def update_langsmith_run(run_id: str, outputs: Dict[str, Any], 
                       error: Optional[str] = None) -> bool:
    """
    Update a LangSmith run with outputs or error information.
    
    Args:
        run_id: ID of the run to update
        outputs: Output data to add to the run
        error: Error message, if any
        
    Returns:
        True if update was successful, False otherwise
    """
    if not langsmith_client:
        return False
        
    try:
        # End the run
        if error:
            # End with error
            langsmith_client.update_run(
                run_id=run_id,
                outputs=outputs,
                error=error,
            )
        else:
            # End successfully
            langsmith_client.update_run(
                run_id=run_id,
                outputs=outputs,
            )
            
        return True
        
    except Exception as e:
        logger.error(f"Error updating LangSmith run: {str(e)}")
        return False


def feedback_langsmith_run(run_id: str, key: str, value: Union[str, int, float, bool],
                         comment: Optional[str] = None) -> bool:
    """
    Add feedback to a LangSmith run.
    
    Args:
        run_id: ID of the run to update
        key: Feedback key (e.g., "accuracy", "helpfulness")
        value: Feedback value
        comment: Optional comment
        
    Returns:
        True if feedback was added successfully, False otherwise
    """
    if not langsmith_client:
        return False
        
    try:
        # Add feedback
        langsmith_client.create_feedback(
            run_id=run_id,
            key=key,
            value=value,
            comment=comment,
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding feedback to LangSmith run: {str(e)}")
        return False


def get_langsmith_trace_url(run_id: str) -> Optional[str]:
    """
    Get the URL for a LangSmith run.
    
    Args:
        run_id: ID of the run
        
    Returns:
        URL to the run in the LangSmith UI, or None if not available
    """
    if not langsmith_client:
        return None
        
    try:
        # Get the API base URL from the client
        api_url = langsmith_client.api_url
        
        # Convert API base URL to UI URL
        ui_url = api_url.replace("api.", "")
        
        # Construct run URL
        run_url = f"{ui_url}/run/{run_id}"
        
        return run_url
        
    except Exception as e:
        logger.error(f"Error generating LangSmith trace URL: {str(e)}")
        return None


# Functions that can be used by observability.py to get LangSmith client and tracer
def get_langsmith_client():
    """
    Get the LangSmith client instance.
    
    Returns:
        LangSmith client if available, None otherwise
    """
    return langsmith_client


def get_langchain_tracer():
    """
    Get a LangChain tracer configured for the project.
    
    Returns:
        LangChain tracer if available, None otherwise
    """
    if not langsmith_client:
        return None
        
    try:
        from langchain.callbacks.tracers import LangChainTracer
        
        tracer = LangChainTracer(
            project_name=LANGSMITH_PROJECT,
            client=langsmith_client,
        )
        
        return tracer
        
    except Exception as e:
        logger.error(f"Error creating LangChain tracer: {str(e)}")
        return None