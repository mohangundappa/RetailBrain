"""
Dependencies for GraphBrainService.

This module provides dependency injection for the graph-based brain service
and related components.
"""
import logging
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.db import get_db
from backend.config.config import get_config, Config
from backend.memory.factory import get_mem0
from backend.agents.framework.langgraph.langgraph_factory import LangGraphAgentFactory
from backend.services.graph_brain_service import GraphBrainService

# Set up logging
logger = logging.getLogger(__name__)

# Singleton instances for services
_graph_brain_service = None


async def get_graph_brain_service(
    db: AsyncSession = Depends(get_db),
    config: Config = Depends(get_config)
) -> AsyncGenerator[GraphBrainService, None]:
    """
    Get or create a graph brain service instance with memory integration.
    
    Args:
        db: Database session
        config: Application configuration
        
    Yields:
        GraphBrainService instance
    
    Raises:
        HTTPException: If the brain service cannot be initialized
    """
    global _graph_brain_service
    
    try:
        if _graph_brain_service is None:
            logger.info("Initializing GraphBrainService with memory integration")
            
            # Create memory service
            memory_service = await get_mem0("graph_brain")
            logger.info("Created memory service for GraphBrainService")
            
            # Create agent factory
            agent_factory = LangGraphAgentFactory(db)
            logger.info("Created LangGraphAgentFactory for GraphBrainService")
            
            # Create brain service
            _graph_brain_service = GraphBrainService(
                db_session=db,
                config=config,
                memory_service=memory_service,
                agent_factory=agent_factory
            )
            
            # Initialize the service
            success = await _graph_brain_service.initialize()
            if not success:
                logger.error("Failed to initialize GraphBrainService")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to initialize graph brain service"
                )
                
            logger.info("GraphBrainService initialized successfully")
            
        # Return the service instance
        yield _graph_brain_service
        
    except Exception as e:
        logger.error(f"Error in get_graph_brain_service: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error initializing graph brain service: {str(e)}"
        )