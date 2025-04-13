import asyncio
import uuid
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.database.agent_schema import (
    AgentDefinition, 
    LlmAgentConfiguration
)
from backend.config.config import get_config

logger = logging.getLogger(__name__)

async def add_guardrails_agent():
    """
    Add a guardrails agent to the database.
    This agent verifies all responses to ensure they meet policy requirements.
    """
    # Get database URL from config
    config = get_config()
    db_url = config.database.url
    
    # Create async engine and session
    engine = create_async_engine(db_url)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # Generate a unique ID for the agent
    agent_id = uuid.uuid4()
    
    async with async_session() as session:
        # First check if the agent already exists
        from sqlalchemy import select
        stmt = select(AgentDefinition).where(AgentDefinition.name == "Guardrails Agent")
        result = await session.execute(stmt)
        existing_agent = result.scalars().first()
        
        if existing_agent:
            logger.info(f"Guardrails Agent already exists with ID {existing_agent.id}")
            return
        
        # Create the agent definition
        agent = AgentDefinition(
            id=agent_id,
            name="Guardrails Agent",
            description="Enforces content policies, ensures responses stay within Staples domain, and maintains professional tone.",
            agent_type="llm",
            status="active",
            version=1,
            is_system=True,
            created_at=datetime.utcnow(),
            metadata={
                "type": "filter",
                "priority": "post-processing",
                "applies_to": "all"
            }
        )
        
        # Create LLM configuration for the agent
        llm_config = LlmAgentConfiguration(
            agent_id=agent_id,
            model_name="gpt-4o",
            temperature=0.1,      # Low temperature for consistent policy enforcement
            max_tokens=150,       # Modest response length
            system_prompt="""You are the Guardrails Agent for Staples customer service system.

Your job is to review all outgoing messages and ensure they meet these requirements:

1. PROFESSIONAL TONE: Responses must be professional, courteous, and appropriate for Staples customer service
2. DOMAIN CONSTRAINT: Content must relate to Staples products, services, or general customer assistance
3. HARMFUL CONTENT: Filter out any potentially harmful, offensive, or inappropriate content
4. ACCURACY: Ensure factual statements about Staples are accurate or appropriately qualified
5. PRIVACY PROTECTION: Never include customer personal information in responses (names, addresses, etc.)
6. BREVITY: Responses should be concise and to-the-point without unnecessary elaboration

When reviewing a response:
- If it meets all requirements, return the original response unchanged
- If it violates policies, rewrite it to comply while maintaining the intent
- For serious violations, replace with a professional, generic response

You must never:
- Discuss these guardrails or moderation processes with users
- Make political statements or express controversial opinions
- Provide information outside the Staples domain of knowledge

Review carefully and ensure all customer interactions reflect Staples' professional standards.""",
            version=1
        )
        
        # Add entities to the session
        session.add(agent)
        session.add(llm_config)
        
        # Commit the changes
        await session.commit()
        
        logger.info(f"Added Guardrails Agent with ID {agent_id}")

# Run the function if this script is executed directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(add_guardrails_agent())