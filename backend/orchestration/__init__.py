"""
Orchestration Module for Staples Brain.

This module is responsible for the orchestration of agents within the Staples Brain system.
It provides mechanisms for agent selection, routing, and state management.
"""

import logging

# Set up logger
logger = logging.getLogger(__name__)

# Direct exports from module files
from backend.orchestration.agent_definition import (
    AgentDefinition
)

from backend.orchestration.router import (
    OptimizedAgentRouter
)

from backend.orchestration.factory import (
    OptimizedAgentFactory
)

from backend.orchestration.state import (
    create_db_tables
)

# Export key components
__all__ = [
    # Agent definition
    'AgentDefinition',
    
    # Router
    'OptimizedAgentRouter',
    
    # Factory
    'OptimizedAgentFactory',
    
    # State persistence
    'create_db_tables',
]