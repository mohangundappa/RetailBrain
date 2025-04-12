"""
API package initialization.

This module has been refactored into backend.endpoints.
This file remains for backward compatibility, redirecting imports to the new location.
"""

# Forward imports from new endpoints module
from backend.endpoints.optimized_chat import router as optimized_chat_router
from backend.endpoints.optimized_chat import main_router as chat_router
from backend.endpoints.state_management import state_router
