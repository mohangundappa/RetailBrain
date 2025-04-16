"""
Run the workflow updater script.
This script is a wrapper for the update_agent_workflows.py script,
making it easier to run from the command line.
"""
import asyncio
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from backend.scripts.update_agent_workflows import main

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Running workflow updater script")
    try:
        asyncio.run(main())
        logger.info("Workflow update completed successfully")
    except Exception as e:
        logger.exception(f"Error running workflow updater: {str(e)}")
        sys.exit(1)