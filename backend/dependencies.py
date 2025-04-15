"""
Dependencies for FastAPI API Gateway.
This module provides dependency injection for services used throughout the API.
"""
import logging
from typing import AsyncGenerator, Dict, Type, Callable, Optional, Any
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.db import get_db
from backend.services.chat_service import ChatService
from backend.services.telemetry_service import TelemetryService
# Now using OptimizedBrainService as the primary brain service
from backend.services.optimized_brain_service import OptimizedBrainService
from backend.config.config import get_config, Config
from backend.repositories.agent_repository import AgentRepository
# Import mem0 memory system
from backend.memory.factory import get_memory_service as create_memory_service
from backend.memory.config import MemoryConfig
# Import agent builder service
from backend.services.agent_builder_service import AgentBuilderService

# Set up logging
logger = logging.getLogger("staples_brain")

# Service factory for better testability
_service_factory: Dict[str, Callable] = {
    "brain_service": OptimizedBrainService,  # Use the optimized brain service
    "graph_brain_service": OptimizedBrainService,  # For backward compatibility
    "chat_service": ChatService,
    "telemetry_service": TelemetryService,
    "agent_builder_service": AgentBuilderService  # Initialize directly
}

# Singleton instances
_brain_service = None
_memory_service = None
_agent_builder_service = None


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


async def get_memory_service_instance() -> Any:
    """Wrapper function to call the async memory service dependency."""
    memory_service = await get_memory_service()
    return memory_service


async def get_brain_service(
    db: AsyncSession = Depends(get_db),
    config: Config = Depends(get_app_config),
    memory_service: Any = Depends(get_memory_service_instance)
) -> OptimizedBrainService:
    """
    Get or create a brain service instance with memory integration.
    Uses a singleton pattern to ensure only one instance exists.
    
    Args:
        db: Database session
        config: Application configuration
        memory_service: Memory service instance (mem0)
        
    Returns:
        OptimizedBrainService instance
    
    Raises:
        HTTPException: If the brain service cannot be initialized
    """
    global _brain_service
    
    try:
        if _brain_service is None:
            logger.info("Initializing OptimizedBrainService with memory integration")
            factory = _service_factory["brain_service"]
            
            # Create LangGraph agent factory
            try:
                # Use existing framework module
                from backend.agents.framework.langgraph import LangGraphAgentFactory
                agent_factory = LangGraphAgentFactory(db)
                logger.debug("Created LangGraph agent factory for brain service")
            except ImportError:
                logger.warning("Could not import LangGraphAgentFactory, continuing without database-driven agents")
                agent_factory = None
            
            # Initialize brain service with database session, memory service and agent factory
            _brain_service = factory(
                db_session=db,
                config=config,
                memory_service=memory_service,
                agent_factory=agent_factory
            )
            
            # Initialize agents from database if possible
            if hasattr(_brain_service, 'initialize') and callable(getattr(_brain_service, 'initialize')):
                await _brain_service.initialize()
            
            logger.info("OptimizedBrainService initialization complete with memory integration")
        
        return _brain_service
    except Exception as e:
        logger.error(f"Failed to initialize OptimizedBrainService: {str(e)}", exc_info=True)
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
    brain_service: OptimizedBrainService = Depends(get_brain_service),
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


async def get_memory_service(
    db: AsyncSession = Depends(get_db),
    config: Config = Depends(get_app_config)
) -> Any:
    """
    Get or create a memory service instance.
    Uses a singleton pattern to ensure only one instance exists.
    
    Args:
        db: Database session
        config: Application configuration
        
    Returns:
        mem0 Memory service instance
    
    Raises:
        HTTPException: If the memory service cannot be initialized
    """
    global _memory_service
    
    try:
        if _memory_service is None:
            logger.info("Initializing memory service (mem0)")
            
            # Create memory config with default settings
            # Using fakeredis in development and getting database URL from connection details
            memory_config = MemoryConfig(
                use_fakeredis=True,  # Use fakeredis for development and testing
                db_url=str(db.bind.url)  # Get database URL from current session
            )
            
            # Initialize memory service
            _memory_service = await create_memory_service(memory_config)
            logger.info("Memory service (mem0) initialization complete")
            
        return _memory_service
    except Exception as e:
        logger.error(f"Failed to initialize memory service: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Memory service initialization failed"
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


async def get_agent_builder_service(
    db: AsyncSession = Depends(get_db),
    brain_service: OptimizedBrainService = Depends(get_brain_service)
) -> AgentBuilderService:
    """
    Get or create an agent builder service instance.
    
    Args:
        db: Database session
        brain_service: Brain service instance
        
    Returns:
        AgentBuilderService instance
    
    Raises:
        HTTPException: If the agent builder service cannot be initialized
    """
    global _agent_builder_service
    
    try:
        if _agent_builder_service is None:
            logger.info("Initializing AgentBuilderService")
            factory = _service_factory["agent_builder_service"]
            
            # Initialize agent builder service with database session and brain service
            _agent_builder_service = factory(
                db_session=db,
                brain_service=brain_service
            )
            
            logger.info("AgentBuilderService initialization complete")
        
        return _agent_builder_service
    except Exception as e:
        logger.error(f"Failed to initialize AgentBuilderService: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent builder service initialization failed"
        )