"""
Main application module for Staples Brain.
This is the central entry point for the FastAPI application and provides core initialization functions.

This module consolidates functionality from all entry points and serves as the single source of truth
for starting the application, initializing the database, and providing access to the FastAPI app.
"""
import os
import sys
import logging
import asyncio
from datetime import datetime
from pathlib import Path

# Set up log directory in project root
ROOT_DIR = Path(__file__).parent.parent
LOG_FILE = ROOT_DIR / "staples_brain.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE)
    ]
)

logger = logging.getLogger("staples_brain")

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import app from API gateway
from backend.api_gateway import app

async def init_db():
    """
    Initialize the database with comprehensive schema and seed data.
    This is the single source of truth for database initialization.
    """
    logger.info("Initializing database tables...")
    try:
        # Use comprehensive database initialization
        from backend.database.initialize_db import initialize_database
        await initialize_database()
        logger.info("Database tables initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}", exc_info=True)
        raise

def run_api(app_instance=None, reload=None):
    """
    Run the API gateway using uvicorn.
    
    Args:
        app_instance: Optional FastAPI app instance. If None, uses the imported app.
        reload: Whether to enable reload mode. If None, determined by environment.
    """
    # Get host and port from environment or use defaults
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", 5000))
    
    # Determine if reload should be enabled
    should_reload = reload
    if should_reload is None:
        should_reload = os.environ.get("ENVIRONMENT") != "production"
    
    logger.info(f"Starting Staples Brain API on {host}:{port} (reload={should_reload})")
    
    # Run with uvicorn - use string for reload mode, instance otherwise
    import uvicorn
    if should_reload:
        # Must use string import format for reload mode
        uvicorn.run(
            "backend.api_gateway:app",
            host=host,
            port=port,
            reload=True
        )
    else:
        # Can use app instance for non-reload mode
        application = app_instance or app
        uvicorn.run(
            application,
            host=host,
            port=port,
            reload=False
        )

# This is used when running the FastAPI app directly
if __name__ == "__main__":
    # Initialize the database
    asyncio.run(init_db())
    
    # Run the API
    run_api()