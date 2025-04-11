#!/usr/bin/env python
"""
Startup script for Staples Brain API server using uvicorn (ASGI).
This is the preferred way to run FastAPI applications.
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
logger.info("Starting Staples Brain API server with uvicorn")

if __name__ == "__main__":
    # Default configuration
    host = "0.0.0.0"
    port = 5000
    app_module = "main:app"
    reload = True
    
    # Allow overriding via environment variables
    if os.environ.get("PORT"):
        port = int(os.environ.get("PORT"))
    
    if os.environ.get("HOST"):
        host = os.environ.get("HOST")
    
    # Configure uvicorn
    config = {
        "app": app_module,
        "host": host,
        "port": port,
        "reload": reload,
        "log_level": "info",
        "workers": 1
    }
    
    logger.info(f"Starting uvicorn with config: {config}")
    
    # Run uvicorn
    try:
        uvicorn.run(**config)
    except Exception as e:
        logger.error(f"Error starting uvicorn: {str(e)}", exc_info=True)
        sys.exit(1)