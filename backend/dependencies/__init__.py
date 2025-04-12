"""
Dependencies package for Staples Brain.
"""
# Import the agent repository dependency from our module
from backend.dependencies.agent_dependencies import get_agent_repository

# Import essential dependencies from the main dependencies.py file
from backend.dependencies import get_brain_service, get_telemetry_service, get_chat_service

# Note: These imports are to expose the functions at the package level
# We have to be careful with circular imports, which is why we're importing
# them from the module where they're defined