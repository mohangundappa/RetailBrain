"""
Main application module for Staples Brain.
This module imports and re-exports both the FastAPI app and initialization functions.
This is a pure ASGI application designed to be run with uvicorn.
"""
import logging
import sys

# Set up basic logging before we import
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

# Import the FastAPI app and core functions
try:
    # Import app directly for ASGI
    from backend.api_gateway import app
    
    # Import utility functions
    from backend.main import init_db, run_api
    
    logger.info("Successfully imported FastAPI app")
except ImportError as e:
    logger.error(f"Error importing FastAPI app: {str(e)}")
    raise