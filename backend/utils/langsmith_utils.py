"""
LangSmith telemetry utilities for Staples Brain.
"""
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("staples_brain")

def init_langsmith() -> bool:
    """
    Initialize LangSmith telemetry if API key is available.
    
    Returns:
        Whether LangSmith was initialized
    """
    try:
        api_key = os.environ.get("LANGSMITH_API_KEY")
        if not api_key:
            logger.info("LANGSMITH_API_KEY not found, telemetry disabled")
            return False
        
        # Set environment variables for LangSmith
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        os.environ["LANGCHAIN_PROJECT"] = os.environ.get("LANGCHAIN_PROJECT", "staples-brain")
        
        # Import LangSmith client and check connection
        from langchain.callbacks.tracers.langchain import LangChainTracer
        tracer = LangChainTracer(project_name=os.environ["LANGCHAIN_PROJECT"])
        
        logger.info("LangSmith client initialized")
        return True
        
    except Exception as e:
        logger.warning(f"Error initializing LangSmith: {str(e)}")
        return False


def create_langsmith_tags(
    session_id: Optional[str] = None, 
    agent_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, str]:
    """
    Create tags for LangSmith tracing.
    
    Args:
        session_id: Optional session identifier
        agent_name: Optional agent name
        metadata: Optional additional metadata
        
    Returns:
        Dictionary of tags for LangSmith
    """
    tags = {}
    
    if session_id:
        tags["session_id"] = session_id
    
    if agent_name:
        tags["agent"] = agent_name
    
    # Add environment tag
    env = os.environ.get("ENVIRONMENT", "development")
    tags["environment"] = env
    
    # Add any additional metadata as tags
    if metadata:
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                tags[key] = str(value)
    
    return tags