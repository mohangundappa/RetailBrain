"""
Dependencies for FastAPI API Gateway.
This module provides dependency injection for services used throughout the API.
"""
import logging
from typing import AsyncGenerator, Dict, Type, Callable, Optional
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.db import get_db
from backend.services.chat_service import ChatService
from backend.services.telemetry_service import TelemetryService
# LangGraphBrainService was removed in favor of GraphBrainService
from backend.services.graph_brain_service import GraphBrainService
from backend.config.config import get_config, Config
from backend.repositories.agent_repository import AgentRepository

# Set up logging
logger = logging.getLogger("staples_brain")

# Service factory for better testability
_service_factory: Dict[str, Callable] = {
    "brain_service": GraphBrainService,  # Use the native Graph brain service
    "graph_brain_service": GraphBrainService,
    "chat_service": ChatService,
    "telemetry_service": TelemetryService
}

# Singleton instance of brain service
_brain_service = None


def set_service_factory(service_name: str, factory_func: Callable) -> None:
    """
    Replace a service factory function for testing purposes.
    
    Args:
        service_name: Name of the service to replace
        factory_func: Factory function that creates the service
    """
    global _service_factory
    if service_name not in _service_factory:
        raise ValueError(f"Unknown service name: {service_name}")
    _service_factory[service_name] = factory_func


@lru_cache()
def get_app_config() -> Config:
    """
    Get application configuration with caching.
    
    Returns:
        Config instance
    """
    return get_config()


async def get_brain_service(
    db: AsyncSession = Depends(get_db),
    config: Config = Depends(get_app_config)
) -> GraphBrainService:
    """
    Get or create a brain service instance.
    Uses a singleton pattern to ensure only one instance exists.
    
    Args:
        db: Database session
        config: Application configuration
        
    Returns:
        BrainService instance
    
    Raises:
        HTTPException: If the brain service cannot be initialized
    """
    global _brain_service
    
    try:
        if _brain_service is None:
            logger.info("Initializing BrainService")
            factory = _service_factory["brain_service"]
            
            # Create LangGraph agent factory
            try:
                from backend.brain.agents.langgraph_factory import LangGraphAgentFactory
                agent_factory = LangGraphAgentFactory(db)
                logger.debug("Created LangGraph agent factory for brain service")
            except ImportError:
                logger.warning("Could not import LangGraphAgentFactory, continuing without database-driven agents")
                agent_factory = None
            
            # Initialize brain service with database session and agent factory
            _brain_service = factory(
                db_session=db,
                config=config,
                agent_factory=agent_factory
            )
            
            # Initialize agents from database if possible
            if hasattr(_brain_service, 'initialize') and callable(getattr(_brain_service, 'initialize')):
                await _brain_service.initialize()
            
            logger.info("BrainService initialization complete")
        
        return _brain_service
    except Exception as e:
        logger.error(f"Failed to initialize BrainService: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Brain service initialization failed"
        )


async def get_telemetry_service(
    db: AsyncSession = Depends(get_db),
    config: Config = Depends(get_app_config)
) -> AsyncGenerator[TelemetryService, None]:
    """
    Get a telemetry service instance.
    
    Args:
        db: Database session
        config: Application configuration
        
    Yields:
        TelemetryService instance
    
    Raises:
        HTTPException: If the telemetry service cannot be initialized
    """
    try:
        factory = _service_factory["telemetry_service"]
        service = factory(db)
        
        yield service
        
        # Clean up resources if needed - currently just logging
        logger.debug("Cleaning up telemetry service resources")
    except Exception as e:
        logger.error(f"Error in telemetry service: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Telemetry service error"
        )


async def get_chat_service(
    db: AsyncSession = Depends(get_db),
    brain_service: GraphBrainService = Depends(get_brain_service),
    telemetry_service: TelemetryService = Depends(get_telemetry_service),
    config: Config = Depends(get_app_config)
) -> AsyncGenerator[ChatService, None]:
    """
    Get a chat service instance.
    
    Args:
        db: Database session
        brain_service: Brain service instance
        telemetry_service: Telemetry service instance
        config: Application configuration
        
    Yields:
        ChatService instance
    
    Raises:
        HTTPException: If the chat service cannot be initialized
    """
    try:
        factory = _service_factory["chat_service"]
        service = factory(
            db=db,
            brain_service=brain_service,
            telemetry_service=telemetry_service
        )
        
        yield service
        
        # Clean up resources if needed - currently just logging
        logger.debug("Cleaning up chat service resources")
    except Exception as e:
        logger.error(f"Error in chat service: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat service error"
        )


async def get_agent_repository(
    db: AsyncSession = Depends(get_db)
) -> AsyncGenerator[AgentRepository, None]:
    """
    Get an agent repository instance.
    
    Args:
        db: Database session
        
    Yields:
        AgentRepository instance
    
    Raises:
        HTTPException: If the agent repository cannot be initialized
    """
    try:
        repo = AgentRepository(db)
        yield repo
    except Exception as e:
        logger.error(f"Error in agent repository: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent repository error"
        )