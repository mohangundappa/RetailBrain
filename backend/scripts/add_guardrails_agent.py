"""
Script to add a guardrails agent to the system.
This agent enforces content policies and ensures responses maintain professional tone.
"""

import asyncio
import logging
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.database.agent_schema import AgentDefinition, AgentPattern
from backend.database.agent_schema import AgentResponseTemplate as ResponseTemplate
from backend.database.entity_schema import EntityDefinition
from backend.config.config import get_config

logger = logging.getLogger(__name__)

async def add_guardrails_agent():
    """
    Add a guardrails agent to the database.
    This agent verifies all responses to ensure they meet policy requirements.
    """
    logger.info("Adding Guardrails Agent...")
    
    # Get database URL from environment
    config = get_config()
    db_url = os.environ.get("DATABASE_URL") or config.get("database", {}).get("url")
    if not db_url:
        logger.error("Database URL not found in environment or config")
        return False
    
    # Make sure we're using asyncpg for async operations
    # Replace 'postgresql://' with 'postgresql+asyncpg://' for async operations
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')
        
    # Remove sslmode parameter as it's not compatible with asyncpg
    if 'sslmode=' in db_url:
        # Parse the URL to remove the sslmode parameter
        parts = db_url.split('?')
        base_url = parts[0]
        if len(parts) > 1:
            query_params = parts[1].split('&')
            filtered_params = [p for p in query_params if not p.startswith('sslmode=')]
            if filtered_params:
                db_url = f"{base_url}?{'&'.join(filtered_params)}"
            else:
                db_url = base_url
    
    # Create async db engine and session
    engine = create_async_engine(db_url)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Check if agent already exists
        from sqlalchemy import select
        query = select(AgentDefinition).where(AgentDefinition.name == "Guardrails Agent")
        result = await session.execute(query)
        existing_agent = result.scalar_one_or_none()
        
        if existing_agent:
            logger.info("Guardrails Agent already exists, skipping creation")
            return True
        
        # Create new guardrails agent
        guardrails_agent = AgentDefinition(
            name="Guardrails Agent",
            description="Verifies all responses to ensure they meet policy requirements and maintain a professional tone.",
            status="active",
            is_system=True,
            version=1,
            agent_type="policy-enforcer"
        )
        
        session.add(guardrails_agent)
        await session.flush()
        
        # Add basic templates
        templates = [
            ResponseTemplate(
                agent_id=guardrails_agent.id,
                template_key="policy_violation",
                template_content="I apologize, but I cannot provide that information as it would violate our policies. How can I assist you with something else?",
                is_active=True
            ),
            ResponseTemplate(
                agent_id=guardrails_agent.id,
                template_key="refined_response",
                template_content="{{refined_response}}",
                is_active=True
            )
        ]
        
        for template in templates:
            session.add(template)
            
        # Commit all changes
        await session.commit()
        
        logger.info(f"Successfully added Guardrails Agent (ID: {guardrails_agent.id})")
        return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(add_guardrails_agent())