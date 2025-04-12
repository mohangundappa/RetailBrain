"""
Dependencies for the optimized brain service.
This module provides FastAPI dependency functions for the optimized brain service.
"""
import logging
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.config import Config
from backend.database.db import get_db
from backend.dependencies import get_app_config
from backend.services.optimized_brain_service import OptimizedBrainService

logger = logging.getLogger(__name__)

# Global singleton instance
_optimized_brain_service: Optional[OptimizedBrainService] = None


async def get_optimized_brain_service(
    db: AsyncSession = Depends(get_db),
    config: Config = Depends(get_app_config)
) -> AsyncGenerator[OptimizedBrainService, None]:
    """
    Get or create an optimized brain service instance.
    
    Args:
        db: Database session
        config: Application configuration
        
    Yields:
        OptimizedBrainService instance
    
    Raises:
        HTTPException: If the brain service cannot be initialized
    """
    global _optimized_brain_service
    
    try:
        if _optimized_brain_service is None:
            logger.info("Initializing OptimizedBrainService")
            
            # Create the service
            _optimized_brain_service = OptimizedBrainService(
                db_session=db,
                config=config
            )
            
            # Initialize the service
            success = await _optimized_brain_service.initialize()
            if not success:
                logger.error("Failed to initialize OptimizedBrainService")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to initialize optimized brain service"
                )
                
            logger.info("OptimizedBrainService initialized successfully")
            
        # Yield the service instance
        yield _optimized_brain_service
    except Exception as e:
        logger.error(f"Error in get_optimized_brain_service: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error initializing optimized brain service: {str(e)}"
        )