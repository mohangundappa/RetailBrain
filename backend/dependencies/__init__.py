"""
Dependencies package for Staples Brain.
"""
# Re-export dependencies from the main module without circular imports
from backend.dependencies.agent_dependencies import get_agent_repository

# Import app config here, as it has minimal dependencies
from backend.config.config import get_config, Config
from functools import lru_cache

@lru_cache()
def get_app_config() -> Config:
    """
    Get application configuration with caching.
    
    Returns:
        Config instance
    """
    return get_config()

# Note: We don't import get_brain_service, get_telemetry_service, and get_chat_service
# directly to avoid circular imports. These will be imported where needed.