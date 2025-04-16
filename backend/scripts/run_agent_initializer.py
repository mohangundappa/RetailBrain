"""
Run the agent initializer script.
This script is a wrapper for the initialize_agent_configs.py script,
making it easier to run from the command line.
"""
import asyncio
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from backend.scripts.initialize_agent_configs import main

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Running agent initializer script")
    try:
        asyncio.run(main())
        logger.info("Agent initialization completed successfully")
    except Exception as e:
        logger.exception(f"Error running agent initializer: {str(e)}")
        sys.exit(1)