"""
Main application module for Staples Brain.
This module imports and re-exports the FastAPI app from backend.api_gateway.
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

# Simply re-export the FastAPI app
from backend.api_gateway import app