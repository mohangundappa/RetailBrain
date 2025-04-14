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

def check_port_available(port=5000):
    """
    Check if the specified port is available.
    
    Args:
        port: The port to check
    
    Returns:
        bool: True if the port is available, False otherwise
    """
    import socket
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True
    except OSError:
        logger.warning(f"Port {port} is already in use")
        return False
    finally:
        sock.close()
    
    return False

def run_api(app_instance=None, reload=None):
    """
    Run the API gateway using uvicorn.
    
    Args:
        app_instance: Optional FastAPI app instance. If None, uses the imported app.
        reload: Whether to enable reload mode. If None, determined by environment.
    """
    # Get host and port from environment or use defaults
    host = os.environ.get("API_HOST", "0.0.0.0")
    
    # User requested to use only port 5000 for the backend
    port = 5000
    
    # Check if the port is available
    is_available = check_port_available(port)
    
    if not is_available:
        logger.warning(f"Port {port} is already in use")
        logger.error("Please stop any services using port 5000 and try again")
        
    # Save the port to an environment variable for other components to use
    os.environ["BACKEND_PORT"] = str(port)
    os.environ["API_PORT"] = str(port)
    
    # Also write to a file that the frontend can read
    port_file = Path(ROOT_DIR) / "backend_port.txt"
    with open(port_file, "w") as f:
        f.write(str(port))
    logger.info(f"Wrote port information to {port_file}")
    
    # Determine if reload should be enabled
    should_reload = reload
    if should_reload is None:
        should_reload = os.environ.get("ENVIRONMENT") != "production"
    
    logger.info(f"Starting Staples Brain API on {host}:{port} (reload={should_reload})")
    
    # Run with uvicorn - use string for reload mode, instance otherwise
    import uvicorn
    try:
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
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"Port {port} is already in use despite our check")
            logger.error("Please stop any other services using port 5000 and try again.")
            
            # We'll only use the requested ports (3000, 3001, 5000) as specified
            logger.info("Per user request, we'll only use ports 3000, 3001, and 5000.")
            
            # Exit with an error code
            sys.exit(1)
        else:
            raise

# This is used when running the FastAPI app directly
if __name__ == "__main__":
    # Initialize the database
    asyncio.run(init_db())
    
    # Run the API
    run_api()