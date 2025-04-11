"""
Main application module for Staples Brain.
This module imports and re-exports the FastAPI app from backend.api_gateway.
This is a pure ASGI application designed to be run with uvicorn.
"""
import os
import sys
import logging
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
logger.info("Starting Staples Brain API (FastAPI)")

# Import the FastAPI app for ASGI
try:
    from backend.api_gateway import app
    logger.info("Successfully imported FastAPI app")
except ImportError as e:
    logger.error(f"Error importing FastAPI app: {str(e)}")
    raise