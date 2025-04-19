#!/usr/bin/env python
"""
Start the backend on port 5000.
This script explicitly overrides any port configuration and ensures the backend runs on port 5000.
"""
import os
import sys
import logging
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)
logger.info("Starting backend on port 5000...")

# Set environment variables
os.environ["API_PORT"] = "5000"

# Start the server directly with uvicorn
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=5000,
    log_level="info"
)