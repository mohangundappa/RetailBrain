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

def find_free_port(start_port=5000, max_attempts=100):
    """
    Find a free port starting from the given port.
    
    Args:
        start_port: The port to start searching from
        max_attempts: Maximum number of ports to try
    
    Returns:
        int: A free port number
    """
    import socket
    
    for port_offset in range(max_attempts):
        test_port = start_port + port_offset
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('0.0.0.0', test_port))
            sock.close()
            return test_port
        except OSError:
            logger.warning(f"Port {test_port} is already in use")
            continue
        finally:
            sock.close()
    
    # If we get here, we couldn't find a free port
    logger.error(f"Could not find a free port after {max_attempts} attempts")
    return start_port

def run_api(app_instance=None, reload=None):
    """
    Run the API gateway using uvicorn.
    
    Args:
        app_instance: Optional FastAPI app instance. If None, uses the imported app.
        reload: Whether to enable reload mode. If None, determined by environment.
    """
    # Get host and port from environment or use defaults
    host = os.environ.get("API_HOST", "0.0.0.0")
    requested_port = int(os.environ.get("API_PORT", 5000))
    
    # Find a free port if the requested one is in use
    port = find_free_port(start_port=requested_port)
    if port != requested_port:
        logger.warning(f"Requested port {requested_port} is in use. Using port {port} instead.")
        
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
            logger.error(f"Port {port} is already in use despite our best efforts to find a free port")
            # Try one more time with a random high port
            import random
            random_port = random.randint(8000, 9000)
            logger.info(f"Trying again with random port {random_port}")
            
            os.environ["BACKEND_PORT"] = str(random_port)
            os.environ["API_PORT"] = str(random_port)
            
            # Update the port file
            port_file = Path(ROOT_DIR) / "backend_port.txt"
            with open(port_file, "w") as f:
                f.write(str(random_port))
            
            # Try again with the new port
            if should_reload:
                uvicorn.run(
                    "backend.api_gateway:app",
                    host=host,
                    port=random_port,
                    reload=True
                )
            else:
                application = app_instance or app
                uvicorn.run(
                    application,
                    host=host,
                    port=random_port,
                    reload=False
                )
        else:
            raise

# This is used when running the FastAPI app directly
if __name__ == "__main__":
    # Initialize the database
    asyncio.run(init_db())
    
    # Run the API
    run_api()