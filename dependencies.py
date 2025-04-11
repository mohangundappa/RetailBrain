"""
Dependencies for FastAPI API Gateway.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from database.db import get_db
from services.brain_service import BrainService
from services.chat_service import ChatService
from services.telemetry_service import TelemetryService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dependencies")

# Cache for brain service
_brain_service_instance = None

# Brain service dependency
async def get_brain_service() -> BrainService:
    """
    Get or create a brain service instance
    
    Returns:
        BrainService instance
    """
    global _brain_service_instance
    if _brain_service_instance is None:
        try:
            _brain_service_instance = BrainService()
            logger.info("Created new brain service instance")
        except Exception as e:
            logger.error(f"Error creating brain service: {e}")
            raise
    
    return _brain_service_instance

# Chat service dependency
async def get_chat_service(db: AsyncSession = get_db()) -> AsyncGenerator[ChatService, None]:
    """
    Get a chat service instance
    
    Args:
        db: Database session
        
    Yields:
        ChatService instance
    """
    brain_service = await get_brain_service()
    service = ChatService(db_session=db, brain=brain_service.brain)
    try:
        yield service
    finally:
        # Any cleanup if needed
        pass

# Telemetry service dependency
async def get_telemetry_service(db: AsyncSession = get_db()) -> AsyncGenerator[TelemetryService, None]:
    """
    Get a telemetry service instance
    
    Args:
        db: Database session
        
    Yields:
        TelemetryService instance
    """
    service = TelemetryService(db_session=db)
    try:
        yield service
    finally:
        # Any cleanup if needed
        pass