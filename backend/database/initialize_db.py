"""
Database initialization module for Staples Brain.
This module handles all database initialization tasks including creating tables and seeding data.
"""
import logging
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

from sqlalchemy.ext.asyncio import AsyncEngine

from backend.database.db import engine as default_engine
from backend.database.init_agent_db import create_agent_schema
from backend.database.seed_agents import seed_all_agents

# Try to import memory schema, but don't fail if it doesn't exist
create_memory_schema = None
has_memory_schema = False
try:
    from backend.database.init_memory_db import create_memory_schema
    has_memory_schema = True
except ImportError:
    logger.warning("Memory schema module not found, skipping memory schema creation")


async def initialize_database(engine: Optional[AsyncEngine] = None) -> None:
    """
    Initialize the database with all required schemas and seed data.
    
    Args:
        engine: The database engine to use, defaults to the main engine
    """
    engine = engine or default_engine
    
    logger.info("Initializing database...")
    
    try:
        # Create agent schema
        await create_agent_schema(engine)
        logger.info("Agent schema created successfully")
        
        # Create memory schema if available
        if has_memory_schema and create_memory_schema is not None:
            try:
                await create_memory_schema(engine)
                logger.info("Memory schema created successfully")
            except Exception as mem_err:
                logger.warning(f"Failed to create memory schema: {str(mem_err)}")
        else:
            logger.info("Memory schema creation function not available")
        
        # Seed agent data
        await seed_all_agents(engine)
        logger.info("Agent data seeded successfully")
        
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise


async def main() -> None:
    """
    Main function to run the database initialization.
    """
    logging.basicConfig(level=logging.INFO)
    await initialize_database()


if __name__ == "__main__":
    asyncio.run(main())