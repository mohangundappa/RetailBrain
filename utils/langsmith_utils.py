"""
LangSmith integration utilities for Staples Brain observability.

This module provides utilities for integrating with LangSmith for tracing,
monitoring, and evaluating LLM-based applications.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from functools import wraps
from datetime import datetime

from langsmith import Client
from langchain_core.tracers import LangChainTracer

logger = logging.getLogger("staples_brain")

# Check if LangSmith API key is available
LANGSMITH_API_KEY = os.environ.get("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.environ.get("LANGSMITH_PROJECT", "staples-brain")
langsmith_enabled = LANGSMITH_API_KEY is not None

# Global LangSmith client
_langsmith_client = None
_langchain_tracer = None

def get_langsmith_client() -> Optional[Client]:
    """Get or create a LangSmith client."""
    global _langsmith_client
    
    if not langsmith_enabled:
        return None
    
    if _langsmith_client is None:
        try:
            _langsmith_client = Client(api_key=LANGSMITH_API_KEY)
            logger.info("LangSmith client initialized")
        except Exception as e:
            logger.error(f"Error initializing LangSmith client: {str(e)}")
            return None
    
    return _langsmith_client

def get_langchain_tracer() -> Optional[LangChainTracer]:
    """Get or create a LangChain tracer."""
    global _langchain_tracer
    
    if not langsmith_enabled:
        return None
    
    if _langchain_tracer is None:
        try:
            client = get_langsmith_client()
            if client:
                _langchain_tracer = LangChainTracer(
                    project_name=LANGSMITH_PROJECT,
                    client=client
                )
                logger.info(f"LangChain tracer initialized for project: {LANGSMITH_PROJECT}")
            else:
                return None
        except Exception as e:
            logger.error(f"Error initializing LangChain tracer: {str(e)}")
            return None
    
    return _langchain_tracer

def log_to_langsmith(
    run_type: str,
    name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Callable:
    """
    Decorator to log function execution to LangSmith.
    
    Args:
        run_type: The type of run (e.g., "llm", "chain", "tool")
        name: Name for the run
        tags: List of tags for the run
        metadata: Additional metadata for the run
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not langsmith_enabled:
                return func(*args, **kwargs)
            
            client = get_langsmith_client()
            if not client:
                return func(*args, **kwargs)
            
            # Prepare run metadata
            run_name = name or func.__name__
            run_tags = tags or []
            run_metadata = metadata or {}
            
            # Add timestamp to metadata
            run_metadata["timestamp"] = datetime.utcnow().isoformat()
            
            # Start the run
            try:
                with client.with_run(run_type=run_type, name=run_name, tags=run_tags, metadata=run_metadata) as run:
                    # Call the function
                    start_time = datetime.utcnow()
                    try:
                        result = func(*args, **kwargs)
                        
                        # Log the result
                        if isinstance(result, dict):
                            run.update_outputs({k: str(v) for k, v in result.items()})
                        else:
                            run.update_outputs({"result": str(result)})
                        
                        # Mark as successful
                        run.metadata["success"] = True
                        
                        return result
                    except Exception as e:
                        # Log the error
                        run.update_outputs({"error": str(e)})
                        run.metadata["success"] = False
                        run.metadata["error_type"] = type(e).__name__
                        
                        # Re-raise the exception
                        raise
                    finally:
                        # Log execution time
                        end_time = datetime.utcnow()
                        run.metadata["execution_time_ms"] = (end_time - start_time).total_seconds() * 1000
            except Exception as e:
                logger.error(f"Error logging to LangSmith: {str(e)}")
                # Fall back to just calling the function
                return func(*args, **kwargs)
        
        return wrapper
    
    return decorator

def track_conversation(
    session_id: str,
    user_input: str,
    agent_response: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Track a conversation in LangSmith.
    
    Args:
        session_id: The session ID for the conversation
        user_input: The user's input
        agent_response: The agent's response
        metadata: Additional metadata for the conversation
        
    Returns:
        The LangSmith run ID if tracking was successful, None otherwise
    """
    if not langsmith_enabled:
        return None
    
    client = get_langsmith_client()
    if not client:
        return None
    
    try:
        # Prepare metadata
        run_metadata = metadata or {}
        run_metadata["session_id"] = session_id
        run_metadata["timestamp"] = datetime.utcnow().isoformat()
        
        # Create a run
        run = client.create_run(
            run_type="conversation",
            name=f"Conversation {session_id}",
            inputs={"user_input": user_input},
            outputs={"agent_response": agent_response},
            tags=["conversation", "staples-brain"],
            metadata=run_metadata,
            project_name=LANGSMITH_PROJECT
        )
        
        return run.id
    except Exception as e:
        logger.error(f"Error tracking conversation in LangSmith: {str(e)}")
        return None

def track_agent_execution(
    agent_name: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Track an agent execution in LangSmith.
    
    Args:
        agent_name: The name of the agent
        inputs: The inputs to the agent
        outputs: The outputs from the agent
        metadata: Additional metadata for the execution
        
    Returns:
        The LangSmith run ID if tracking was successful, None otherwise
    """
    if not langsmith_enabled:
        return None
    
    client = get_langsmith_client()
    if not client:
        return None
    
    try:
        # Prepare metadata
        run_metadata = metadata or {}
        run_metadata["agent"] = agent_name
        run_metadata["timestamp"] = datetime.utcnow().isoformat()
        
        # Create a run
        run = client.create_run(
            run_type="agent",
            name=f"{agent_name} Execution",
            inputs={k: str(v) for k, v in inputs.items()},
            outputs={k: str(v) for k, v in outputs.items()},
            tags=["agent", "staples-brain", agent_name],
            metadata=run_metadata,
            project_name=LANGSMITH_PROJECT
        )
        
        return run.id
    except Exception as e:
        logger.error(f"Error tracking agent execution in LangSmith: {str(e)}")
        return None

def track_llm_call(
    model: str,
    prompt: str,
    response: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Track an LLM call in LangSmith.
    
    Args:
        model: The name of the model
        prompt: The prompt sent to the model
        response: The response from the model
        metadata: Additional metadata for the call
        
    Returns:
        The LangSmith run ID if tracking was successful, None otherwise
    """
    if not langsmith_enabled:
        return None
    
    client = get_langsmith_client()
    if not client:
        return None
    
    try:
        # Prepare metadata
        run_metadata = metadata or {}
        run_metadata["model"] = model
        run_metadata["timestamp"] = datetime.utcnow().isoformat()
        
        # Create a run
        run = client.create_run(
            run_type="llm",
            name=f"{model} Call",
            inputs={"prompt": prompt},
            outputs={"response": response},
            tags=["llm", "staples-brain", model],
            metadata=run_metadata,
            project_name=LANGSMITH_PROJECT
        )
        
        return run.id
    except Exception as e:
        logger.error(f"Error tracking LLM call in LangSmith: {str(e)}")
        return None

# Initialize LangSmith client if possible
if langsmith_enabled:
    get_langsmith_client()
    get_langchain_tracer()
else:
    logger.warning("LangSmith integration disabled: LANGSMITH_API_KEY not found")