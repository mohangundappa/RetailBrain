"""
Dependencies for FastAPI API Gateway.
"""
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.db import get_db
from backend.services.brain_service import BrainService
from backend.services.chat_service import ChatService
from backend.services.telemetry_service import TelemetryService

# Set up logging
logger = logging.getLogger("staples_brain")

# Singleton instance of brain service
_brain_service = None


async def get_brain_service() -> BrainService:
    """
    Get or create a brain service instance
    
    Returns:
        BrainService instance
    """
    global _brain_service
    
    if _brain_service is None:
        _brain_service = BrainService()
    
    return _brain_service


async def get_chat_service(db: AsyncSession = Depends(get_db)) -> AsyncGenerator[ChatService, None]:
    """
    Get a chat service instance
    
    Args:
        db: Database session
        
    Yields:
        ChatService instance
    """
    brain_service = await get_brain_service()
    telemetry_service = TelemetryService(db)
    
    service = ChatService(
        db=db,
        brain_service=brain_service,
        telemetry_service=telemetry_service
    )
    
    try:
        yield service
    finally:
        # Clean up resources if needed
        pass


async def get_telemetry_service(db: AsyncSession = Depends(get_db)) -> AsyncGenerator[TelemetryService, None]:
    """
    Get a telemetry service instance
    
    Args:
        db: Database session
        
    Yields:
        TelemetryService instance
    """
    service = TelemetryService(db)
    
    try:
        yield service
    finally:
        # Clean up resources if needed
        pass