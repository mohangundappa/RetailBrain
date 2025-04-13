"""
Database utilities for mem0 memory system.

This module provides database connectivity functions for the memory system,
including connection management and session handling.
"""

import os
import logging
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

def get_sanitized_db_url() -> str:
    """
    Get the database URL with SSLMode parameter removed for compatibility.
    
    Returns:
        Sanitized database URL
    """
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    
    # Convert to async URL if needed
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    
    # Remove sslmode parameter if present
    if "sslmode=" in db_url:
        db_url = db_url.split("?")[0]
        
    return db_url


async def get_db_session() -> Optional[AsyncSession]:
    """
    Get a database session for async operations.
    
    Returns:
        AsyncSession instance
    """
    try:
        db_url = get_sanitized_db_url()
        engine = create_async_engine(db_url)
        async_session = sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
        
        return async_session()
    except Exception as e:
        logger.error(f"Error creating database session: {str(e)}")
        return None