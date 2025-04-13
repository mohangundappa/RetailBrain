import asyncio
import uuid
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.database.agent_schema import (
    AgentDefinition, 
    AgentPattern, 
    AgentResponseTemplate,
    LlmAgentConfiguration
)
from backend.config.config import get_config

logger = logging.getLogger(__name__)

async def add_general_agent():
    """
    Add a general conversation agent to the database using LLM-based approach.
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
        stmt = select(AgentDefinition).where(AgentDefinition.name == "General Conversation Agent")
        result = await session.execute(stmt)
        existing_agent = result.scalars().first()
        
        if existing_agent:
            logger.info(f"General Conversation Agent already exists with ID {existing_agent.id}")
            return
        
        # Create the agent definition
        agent = AgentDefinition(
            id=agent_id,
            name="General Conversation Agent",
            description="Handles general conversation including greetings, goodbyes, and basic questions about Staples products and services.",
            agent_type="llm",  # Using LLM agent type
            status="active",
            version=1,
            is_system=True,
            created_at=datetime.utcnow()
        )
        
        # Create LLM configuration for the agent
        llm_config = LlmAgentConfiguration(
            agent_id=agent_id,
            model_name="gpt-4o",  # Using GPT-4o for high quality responses
            temperature=0.7,      # Some creativity for conversational feel
            max_tokens=150,       # Keep responses concise
            system_prompt="""You are the General Conversation Agent for Staples customer service.

Your primary responsibilities are:
1. Respond to greetings (hello, hi, hey, etc.) with warm, friendly welcomes
2. Handle goodbyes and thank yous appropriately
3. Respond to general questions about Staples
4. Identify when a customer needs specialized help and mention that you can assist with specific tasks like order tracking or password resets

Keep your responses concise, friendly, and helpful. Always maintain a professional tone appropriate for Staples customer service.

When you don't know something specific, acknowledge that and offer to help with what you can do.

Respond ONLY as the General Conversation Agent. Do not attempt to handle specific tasks that would be better served by specialized agents.""",
            version=1
        )
        
        # Create semantic patterns for the agent
        patterns = [
            # Greeting patterns
            AgentPattern(
                agent_id=agent_id,
                pattern="greeting the assistant",
                confidence=0.95,
                pattern_type="semantic"
            ),
            AgentPattern(
                agent_id=agent_id,
                pattern="saying hello",
                confidence=0.95,
                pattern_type="semantic"
            ),
            AgentPattern(
                agent_id=agent_id,
                pattern="introducing oneself",
                confidence=0.9,
                pattern_type="semantic"
            ),
            
            # Goodbye patterns
            AgentPattern(
                agent_id=agent_id,
                pattern="ending the conversation",
                confidence=0.95,
                pattern_type="semantic"
            ),
            AgentPattern(
                agent_id=agent_id,
                pattern="saying thank you",
                confidence=0.9,
                pattern_type="semantic"
            ),
            
            # General conversation patterns
            AgentPattern(
                agent_id=agent_id,
                pattern="asking how the assistant is doing",
                confidence=0.9,
                pattern_type="semantic"
            ),
            AgentPattern(
                agent_id=agent_id,
                pattern="making small talk",
                confidence=0.85,
                pattern_type="semantic"
            ),
            
            # Also add exact keyword matches for highest priority routing
            AgentPattern(
                agent_id=agent_id,
                pattern="hi",
                confidence=1.0,
                pattern_type="exact"
            ),
            AgentPattern(
                agent_id=agent_id,
                pattern="hello",
                confidence=1.0,
                pattern_type="exact"
            ),
            AgentPattern(
                agent_id=agent_id,
                pattern="hey",
                confidence=1.0,
                pattern_type="exact"
            ),
            AgentPattern(
                agent_id=agent_id,
                pattern="thanks",
                confidence=1.0,
                pattern_type="exact"
            ),
            AgentPattern(
                agent_id=agent_id,
                pattern="thank you",
                confidence=1.0,
                pattern_type="exact"
            ),
            AgentPattern(
                agent_id=agent_id,
                pattern="goodbye",
                confidence=1.0,
                pattern_type="exact"
            ),
            AgentPattern(
                agent_id=agent_id,
                pattern="bye",
                confidence=1.0,
                pattern_type="exact"
            )
        ]
        
        # Add all entities to the session
        session.add(agent)
        session.add(llm_config)
        for pattern in patterns:
            session.add(pattern)
        
        # Commit the changes
        await session.commit()
        
        logger.info(f"Added General Conversation Agent with ID {agent_id}")

# Run the function if this script is executed directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(add_general_agent())