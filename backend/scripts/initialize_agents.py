"""
Script to initialize core agents for the Staples Brain system.
This module ensures the essential agents are loaded at startup.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

async def initialize_core_agents():
    """
    Initialize core agents needed for the system.
    """
    logger.info("Initializing core agents...")
    agent_count = 0
    
    # Add General Conversation Agent
    try:
        from backend.scripts.add_general_agent import add_general_agent
        success = await add_general_agent()
        if success:
            agent_count += 1
            logger.info("Successfully initialized General Conversation Agent")
        else:
            logger.error("Failed to initialize General Conversation Agent")
    except Exception as e:
        logger.error(f"Error initializing General Conversation Agent: {str(e)}", exc_info=True)
        
    # Add Guardrails Agent
    try:
        from backend.scripts.add_guardrails_agent import add_guardrails_agent
        success = await add_guardrails_agent()
        if success:
            agent_count += 1
            logger.info("Successfully initialized Guardrails Agent")
        else:
            logger.error("Failed to initialize Guardrails Agent")
    except Exception as e:
        logger.error(f"Error initializing Guardrails Agent: {str(e)}", exc_info=True)
        
    # Add Store Locator Agent - COMMENTED OUT AS ALREADY EXISTS
    # We'll add more core agents as needed
        
    logger.info(f"Initialized {agent_count} core agents")
    return agent_count

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(initialize_core_agents())