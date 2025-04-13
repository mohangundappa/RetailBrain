import asyncio
import logging

from backend.scripts.add_general_agent import add_general_agent
from backend.scripts.add_guardrails_agent import add_guardrails_agent

logger = logging.getLogger(__name__)

async def initialize_core_agents():
    """
    Initialize core agents needed for the system.
    """
    # Add general conversation agent
    logger.info("Ensuring General Conversation Agent exists...")
    await add_general_agent()
    
    # Add guardrails agent
    logger.info("Ensuring Guardrails Agent exists...")
    await add_guardrails_agent()
    
    logger.info("Core agent initialization complete")

# Run the function if this script is executed directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(initialize_core_agents())