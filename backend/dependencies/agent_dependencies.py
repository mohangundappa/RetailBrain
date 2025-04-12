"""
Dependencies for agent-related functionality.
"""
import logging
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.db import get_db
from backend.repositories.agent_repository import AgentRepository

logger = logging.getLogger(__name__)


async def get_agent_repository(
    db: AsyncSession = Depends(get_db)
) -> AsyncGenerator[AgentRepository, None]:
    """
    Get an agent repository instance.
    
    Args:
        db: Database session
        
    Yields:
        AgentRepository instance
    """
    repo = AgentRepository(db)
    try:
        yield repo
    finally:
        pass  # The session is closed in the get_db dependency