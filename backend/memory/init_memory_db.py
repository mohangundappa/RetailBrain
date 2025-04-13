"""
Database initialization for the mem0 memory system.

This module sets up the PostgreSQL database schema for mem0,
creating the necessary tables for long-term memory storage.
"""

import logging
from sqlalchemy import create_engine, inspect, MetaData, Table
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from backend.memory.schema import MemoryEntryModel, MemoryIndexModel, MemoryContextModel
from backend.database.db import get_sanitized_db_url
from backend.memory.config import MemoryConfig

logger = logging.getLogger(__name__)

async def init_memory_schema(config: MemoryConfig = None) -> bool:
    """
    Initialize the memory schema in the database.
    
    This function creates the necessary tables for the mem0 memory system
    if they don't already exist.
    
    Args:
        config: Memory configuration
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Initializing memory schema...")
    
    try:
        # Get database URL from environment or config
        db_url = get_sanitized_db_url()
        
        # Create async engine
        engine = create_async_engine(db_url)
        
        # Create metadata
        from backend.database.db import Base
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Memory schema initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing memory schema: {str(e)}")
        return False


def check_memory_tables_exist(engine) -> bool:
    """
    Check if memory tables exist in the database.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        True if all tables exist, False otherwise
    """
    inspector = inspect(engine)
    required_tables = ['memory_entry', 'memory_index', 'memory_context']
    
    for table in required_tables:
        if not inspector.has_table(table):
            return False
            
    return True


def migrate_legacy_memory_to_mem0(engine) -> bool:
    """
    Migrate legacy memory data to the new mem0 schema.
    
    This function is a placeholder for future migration logic
    when transitioning from an existing memory system.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        True if successful, False otherwise
    """
    # Placeholder for future migration logic
    return True