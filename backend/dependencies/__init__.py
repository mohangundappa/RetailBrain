"""
Dependencies package for Staples Brain.
"""
# Only import the agent repository dependency from our module
from backend.dependencies.agent_dependencies import get_agent_repository

# Direct imports from the main dependencies.py file
# We'll reference these from the main file directly in the API files
# to prevent circular imports