"""
Orchestration Module for Staples Brain.

This module is responsible for the orchestration of agents within the Staples Brain system.
It provides mechanisms for agent selection, routing, and state management.
"""

import logging

# Set up logger
logger = logging.getLogger(__name__)

# Export key components - Use string literals to avoid circular imports
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

# Direct exports from module files
from backend.orchestration.agent_definition import AgentDefinition
from backend.orchestration.state import create_db_tables
from backend.orchestration.agent_factory import OptimizedAgentFactory

# These should be imported at usage time to avoid circular dependencies