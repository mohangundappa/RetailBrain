"""
Run the agent configuration initialization script.

This script is a simple wrapper to run the agent configuration initialization.
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
    """Execute the agent configuration initialization."""
    try:
        from backend.scripts.initialize_agent_configs import main as init_main
        # Run the initialization
        asyncio.run(init_main())
        logger.info("Agent configuration initialization completed successfully")
    except Exception as e:
        logger.error(f"Error initializing agent configurations: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()