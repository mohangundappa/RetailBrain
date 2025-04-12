"""
ASGI application entrypoint for Staples Brain.

This module is the root ASGI entry point for the application and simply re-exports 
the FastAPI app from the backend module. It follows ASGI standards and should be used
when deploying with ASGI servers like Uvicorn.

Example:
    uvicorn main:app --host 0.0.0.0 --port 5000
"""
import logging
import sys

# Configure minimal logging for ASGI mode
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("staples_brain")
logger.info("Starting Staples Brain API (FastAPI)")

# Import the FastAPI app from the backend package
# This is the proper ASGI entry point
try:
    from backend.api_gateway import app
    logger.info("Successfully imported FastAPI app")
except ImportError as e:
    logger.error(f"Error importing FastAPI app: {str(e)}")
    raise

# Note: We don't import init_db or run_api here because
# this module should only export the ASGI app object
# Those functions are available directly from backend.main