"""
Test script for mem0 memory system.

This script tests the mem0 memory system with Redis and PostgreSQL.
"""

import asyncio
import logging
import sys
import uuid
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory_test")

# Import memory system
try:
    from backend.memory import run_mem0_test
except ImportError as e:
    logger.error(f"Failed to import memory system: {str(e)}")
    sys.exit(1)

async def main():
    """Run memory system tests."""
    logger.info("Starting memory system test...")
    
    # Run the mem0 test
    success = await run_mem0_test()
    
    if success:
        logger.info("Memory system test completed successfully.")
    else:
        logger.error("Memory system test failed.")

if __name__ == "__main__":
    asyncio.run(main())