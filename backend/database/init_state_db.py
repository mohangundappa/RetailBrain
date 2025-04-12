"""
Database initialization for state persistence.
This module handles the creation of tables required for state persistence and recovery.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text

from backend.database.db import engine as default_engine

logger = logging.getLogger(__name__)


async def create_state_persistence_schema(engine: Optional[AsyncEngine] = None) -> None:
    """
    Create the state persistence schema in the database.
    
    Args:
        engine: The database engine to use, defaults to the main engine
    """
    engine = engine or default_engine
    
    logger.info("Creating state persistence schema...")
    
    try:
        # Execute statements individually to avoid asyncpg issues with multiple commands
        async with engine.begin() as conn:
            # Create the main table
            await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS orchestration_state (
                id VARCHAR(36) PRIMARY KEY,
                session_id VARCHAR(36) NOT NULL,
                state_data JSONB NOT NULL,
                checkpoint_name VARCHAR(255) NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_checkpoint BOOLEAN NOT NULL DEFAULT FALSE
            )
            """))
            
            # Create index for session_id
            await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS orchestration_state_session_id_idx 
            ON orchestration_state(session_id)
            """))
            
            # Create index for checkpoints
            await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS orchestration_state_checkpoint_idx 
            ON orchestration_state(session_id, is_checkpoint) 
            WHERE is_checkpoint = TRUE
            """))
            
            # Create index for timestamps
            await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS orchestration_state_created_at_idx 
            ON orchestration_state(created_at)
            """))
        
        logger.info("State persistence schema created successfully")
    
    except Exception as e:
        logger.error(f"Error creating state persistence schema: {str(e)}")
        raise