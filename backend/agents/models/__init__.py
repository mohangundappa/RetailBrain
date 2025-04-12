"""
Agent models module for Staples Brain.

This module provides the components for agent model definitions, interfaces, and implementations.
It is the replacement for the framework module.

This module re-exports all the components from the framework module to allow for a
gradual migration from backend.agents.framework to backend.agents.models.
"""

# Re-export all components from framework module for backward compatibility
from backend.agents.framework.base import *

# Re-export langgraph framework components
try:
    from backend.agents.framework.langgraph import (
        LangGraphAgent,
        LangGraphAgentFactory,
        LangGraphOrchestrator
    )
except ImportError:
    # LangGraph components may not be available, so provide graceful fallback
    pass