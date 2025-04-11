#!/usr/bin/env python
"""
Runner script for the Staples Brain FastAPI application using uvicorn.
"""
import os
import sys
import logging
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("staples_brain.log")
    ]
)

logger = logging.getLogger("staples_brain")
logger.info("Starting uvicorn runner for Staples Brain API")

if __name__ == "__main__":
    # Run the FastAPI app with uvicorn
    try:
        # Configure uvicorn with a different port (8000) to avoid conflicts with gunicorn
        uvicorn_config = {
            "app": "main:app",
            "host": "0.0.0.0",
            "port": 8000,
            "reload": True,
            "log_level": "info",
            "workers": 1,
            "loop": "asyncio"
        }
        
        # Log configuration
        logger.info(f"Starting uvicorn server with configuration: {uvicorn_config}")
        
        # Run uvicorn
        uvicorn.run(**uvicorn_config)
        
    except Exception as e:
        logger.error(f"Error starting uvicorn server: {str(e)}", exc_info=True)
        sys.exit(1)