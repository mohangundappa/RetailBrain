"""
Script to add a guardrails agent to the system.
This agent enforces content policies and ensures responses maintain professional tone.
"""

import asyncio
import logging
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.database.schema import AgentDefinition, AgentPattern, EntityDefinition
from backend.database.schema import ResponseTemplate
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
            is_active=True,
            is_system=True,
            prompts={
                "system_prompt": (
                    "You are the Guardrails Agent for Staples, responsible for ensuring all "
                    "responses meet the following requirements:\n\n"
                    "1. Professional and courteous tone\n"
                    "2. No inappropriate language or content\n"
                    "3. No personally identifiable information unless necessary for the request\n"
                    "4. All information is accurate and reflects Staples policies\n"
                    "5. Maintains brand voice: helpful, knowledgeable, and solution-oriented\n\n"
                    "You will review responses before they are sent to users and make any necessary "
                    "adjustments to ensure compliance with these guidelines."
                ),
                "user_prompt_template": (
                    "Original response: {{original_response}}\n\n"
                    "User query: {{user_query}}\n\n"
                    "Agent: {{agent_name}}\n\n"
                    "Please review the response and make any necessary adjustments to ensure "
                    "it meets our policy requirements and maintains a professional tone. "
                    "If no changes are needed, return the original response exactly."
                )
            },
            version=1,
            agent_type="policy-enforcer",
            parameters={
                "model": "gpt-4o",
                "temperature": 0.3,
                "response_format": "text",
                "max_tokens": 500
            }
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