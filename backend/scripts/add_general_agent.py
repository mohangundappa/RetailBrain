"""
Script to add a general conversation agent to the system.
This agent handles basic conversational interactions, greetings, and simple queries.
"""

import asyncio
import logging
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.database.agent_schema import AgentDefinition, AgentPattern, AgentResponseTemplate
from backend.database.entity_schema import EntityDefinition
from backend.config.config import get_config
from backend.orchestration.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

async def add_general_agent():
    """
    Add a general conversation agent to the database using LLM-based approach.
    """
    logger.info("Adding General Conversation Agent...")
    
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
        query = select(AgentDefinition).where(AgentDefinition.name == "General Conversation Agent")
        result = await session.execute(query)
        existing_agent = result.scalar_one_or_none()
        
        if existing_agent:
            logger.info("General Conversation Agent already exists, skipping creation")
            return True
        
        # Create new general conversation agent
        general_agent = AgentDefinition(
            name="General Conversation Agent",
            description="Handles greetings, goodbyes, small talk, and general questions that don't fit other specialized agents.",
            status="active",
            is_system=True,
            version=1,
            agent_type="llm-driven"
        )
        
        session.add(general_agent)
        await session.flush()
        
        # Add patterns for this agent
        patterns = [
            # Greetings
            AgentPattern(
                agent_id=general_agent.id,
                pattern_type="keyword",
                pattern_value="hello",
                priority=1,
                confidence_boost=0.2
            ),
            AgentPattern(
                agent_id=general_agent.id,
                pattern_type="keyword",
                pattern_value="hi there",
                priority=1,
                confidence_boost=0.2
            ),
            AgentPattern(
                agent_id=general_agent.id,
                pattern_type="keyword",
                pattern_value="good morning",
                priority=1,
                confidence_boost=0.2
            ),
            AgentPattern(
                agent_id=general_agent.id,
                pattern_type="keyword",
                pattern_value="hey",
                priority=1,
                confidence_boost=0.2
            ),
            # Goodbyes
            AgentPattern(
                agent_id=general_agent.id,
                pattern_type="keyword",
                pattern_value="goodbye",
                priority=1,
                confidence_boost=0.2
            ),
            AgentPattern(
                agent_id=general_agent.id,
                pattern_type="keyword",
                pattern_value="bye",
                priority=1,
                confidence_boost=0.2
            ),
            AgentPattern(
                agent_id=general_agent.id,
                pattern_type="keyword",
                pattern_value="thank you",
                priority=1,
                confidence_boost=0.2
            ),
            # Small talk
            AgentPattern(
                agent_id=general_agent.id,
                pattern_type="keyword",
                pattern_value="how are you",
                priority=1,
                confidence_boost=0.2
            ),
            AgentPattern(
                agent_id=general_agent.id,
                pattern_type="keyword",
                pattern_value="nice to meet you",
                priority=1,
                confidence_boost=0.2
            ),
            # Help
            AgentPattern(
                agent_id=general_agent.id,
                pattern_type="keyword",
                pattern_value="help",
                priority=0,
                confidence_boost=0.1
            ),
            AgentPattern(
                agent_id=general_agent.id,
                pattern_type="keyword",
                pattern_value="what can you do",
                priority=0,
                confidence_boost=0.1
            )
        ]
        
        for pattern in patterns:
            session.add(pattern)
            
        # Add basic templates
        templates = [
            AgentResponseTemplate(
                agent_id=general_agent.id,
                template_key="greeting",
                template_content="Hello! I'm your Staples Assistant. How can I help you today?",
                template_type="text",
                language="en",
                tone="friendly"
            ),
            AgentResponseTemplate(
                agent_id=general_agent.id,
                template_key="goodbye",
                template_content="Thank you for chatting with Staples. Have a great day!",
                template_type="text",
                language="en",
                tone="friendly"
            ),
            AgentResponseTemplate(
                agent_id=general_agent.id,
                template_key="help",
                template_content="I can help with many things related to Staples, such as tracking orders, resetting passwords, finding stores, and providing product information. What would you like assistance with?",
                template_type="text",
                language="en", 
                tone="helpful"
            )
        ]
        
        for template in templates:
            session.add(template)
            
        # Generate and store embeddings for this agent
        embedding_service = EmbeddingService()
        
        # Create embedding text
        embedding_text = f"{general_agent.name}\n{general_agent.description}\n"
        for pattern in patterns:
            embedding_text += f"{pattern.pattern_value}\n"
            
        # Generate embedding
        embedding = await embedding_service.create_embedding(embedding_text)
        general_agent.embedding = embedding
        
        # Commit all changes
        await session.commit()
        
        logger.info(f"Successfully added General Conversation Agent (ID: {general_agent.id})")
        return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(add_general_agent())