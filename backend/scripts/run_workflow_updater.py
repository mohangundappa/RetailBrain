"""
Run the workflow updater script.
This script is a wrapper for the update_agent_workflows.py script,
making it easier to run from the command line.
"""
import asyncio
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("staples_brain")

def main():
    """Execute the workflow updater script."""
    try:
        from backend.scripts.update_agent_workflows import main as update_main
        # Run the updater
        asyncio.run(update_main())
        logger.info("Workflow updater completed successfully")
    except Exception as e:
        logger.error(f"Error running workflow updater: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()