"""
Utility module to initialize the agent database schema.
"""
import logging
import asyncio
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine

from backend.database.db import engine as default_engine
from backend.database.agent_schema import (
    AgentDefinition, AgentDeployment, AgentComposition,
    LlmAgentConfiguration, RuleAgentConfiguration, RetrievalAgentConfiguration,
    AgentPattern, AgentPatternEmbedding, AgentTool, AgentResponseTemplate,
    SupervisorConfiguration, SupervisorAgentMapping
)
from backend.database.entity_schema import (
    EntityDefinition, EntityEnumValue, AgentEntityMapping,
    EntityExtractionPattern, EntityTransformation
)

logger = logging.getLogger(__name__)


async def create_agent_schema(engine: Optional[AsyncEngine] = None) -> None:
    """
    Create all tables in the agent schema.
    
    Args:
        engine: The database engine to use, defaults to the main engine
    """
    from sqlalchemy.schema import CreateTable
    from sqlalchemy import text
    
    engine = engine or default_engine
    
    logger.info("Creating pgvector extension if not exists...")
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            logger.info("PGVector extension created or already exists")
        except Exception as e:
            logger.error(f"Failed to create pgvector extension: {str(e)}")
            raise
    
    # List of all model classes to create
    models = [
        # Agent schema
        AgentDefinition,
        AgentDeployment,
        AgentComposition,
        LlmAgentConfiguration,
        RuleAgentConfiguration,
        RetrievalAgentConfiguration,
        AgentPattern,
        AgentPatternEmbedding,
        AgentTool,
        AgentResponseTemplate,
        # Supervisor schema
        SupervisorConfiguration,
        SupervisorAgentMapping,
        # Entity schema
        EntityDefinition,
        EntityEnumValue,
        AgentEntityMapping,
        EntityExtractionPattern,
        EntityTransformation,
    ]
    
    logger.info("Creating agent schema tables...")
    async with engine.begin() as conn:
        for model in models:
            table_name = model.__tablename__
            try:
                # Check if table exists
                result = await conn.execute(
                    text(f"SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = '{table_name}');")
                )
                exists = result.scalar()
                
                if not exists:
                    logger.info(f"Creating table: {table_name}")
                    create_table = CreateTable(model.__table__)
                    await conn.execute(text(str(create_table).strip() + ";"))
                else:
                    logger.info(f"Table {table_name} already exists")
            except Exception as e:
                logger.error(f"Error creating table {table_name}: {str(e)}")
                raise

    logger.info("Agent schema tables created successfully")


async def main():
    """
    Main function to run the schema creation.
    """
    logging.basicConfig(level=logging.INFO)
    await create_agent_schema()


if __name__ == "__main__":
    asyncio.run(main())