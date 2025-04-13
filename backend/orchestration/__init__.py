"""
Orchestration Module for Staples Brain LangGraph Implementation.

This module is responsible for the orchestration of agents within the Staples Brain system
using the LangGraph framework for conversation state management.
"""

import logging

# Set up logger
logger = logging.getLogger(__name__)

# Export key components - Use string literals to avoid circular imports
__all__ = [
    # State persistence
    'create_db_tables',
]

# Direct exports from module files
from backend.orchestration.state import create_db_tables

# These should be imported at usage time to avoid circular dependencies