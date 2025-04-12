"""
Endpoints module for Staples Brain.

This module provides the API endpoints for the Staples Brain application.
It is the replacement for the api module.

This module re-exports all the components from the api module to allow for a
gradual migration from backend.api to backend.endpoints.
"""

# Import all routers from the api module
try:
    from backend.api.optimized_chat import router as optimized_chat_router
    from backend.api.optimized_chat import main_router as chat_router
    from backend.api.state_management import state_router
    from backend.api.telemetry_fastapi import telemetry_router
except ImportError:
    # One or more routers may not be available, so provide graceful fallback
    pass