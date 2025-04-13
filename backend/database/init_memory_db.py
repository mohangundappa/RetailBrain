"""
Database initialization wrapper for mem0 memory system.

This module provides a wrapper for the memory initialization system,
making it compatible with the main database initialization process.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

async def create_memory_schema(engine: AsyncEngine) -> bool:
    """
    Initialize the memory schema in the database.
    
    This function creates the necessary tables for the mem0 memory system
    if they don't already exist.
    
    Args:
        engine: The database engine to use
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Creating memory schema...")
    
    try:
        # Import the real memory schema initialization function
        from backend.memory.init_memory_db import init_memory_schema
        
        # Initialize memory schema
        success = await init_memory_schema()
        
        if success:
            logger.info("Memory schema created successfully")
        else:
            logger.warning("Memory schema creation returned False")
            
        return success
        
    except ImportError:
        logger.warning("Memory schema module not found")
        return False
    except Exception as e:
        logger.error(f"Error creating memory schema: {str(e)}")
        return False