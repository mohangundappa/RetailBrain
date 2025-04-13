"""
DEPRECATED: This module has been replaced by LangGraph-based agent routing.

This file is kept as a stub for backward compatibility but contains no implementation.
All agent routing functionality has been moved to backend/agents/framework/langgraph/.
"""

import logging
logger = logging.getLogger(__name__)

# This class is maintained as a stub for backward compatibility
class OptimizedAgentRouter:
    """
    DEPRECATED: This class has been replaced by LangGraph-based routing.
    
    This is a stub maintained for backward compatibility only.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize the stub router."""
        logger.warning("OptimizedAgentRouter is deprecated and should not be used")
        
    def route(self, *args, **kwargs):
        """Stub implementation of the route method."""
        logger.error("OptimizedAgentRouter.route() called but this method is deprecated")
        return None, 0.0