#!/usr/bin/env python
"""
A simple runner script for starting the Staples Brain API with uvicorn.
This script is designed to be used by the Replit workflow.
"""
import os
import sys
import logging
import asyncio

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger("staples_brain_runner")
logger.info("Starting Staples Brain API runner script")

# Configuration
host = "0.0.0.0"
port = 5000
app_module = "main:app"

logger.info(f"Starting uvicorn with app={app_module}, host={host}, port={port}")

# Import the API runner and database initialization
try:
    from backend.main import init_db, run_api
    
    # Run in asyncio event loop
    async def start_app():
        # Initialize database
        await init_db()
        
        # Import uvicorn and run directly
        import uvicorn
        config = uvicorn.Config(
            app_module, 
            host=host, 
            port=port,
            reload=True
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    # Run the app
    try:
        asyncio.run(start_app())
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Error running server: {str(e)}", exc_info=True)
        sys.exit(1)
        
except ImportError as e:
    logger.error(f"Error importing modules: {str(e)}", exc_info=True)
    
    # Fallback to subprocess if import fails
    logger.info("Falling back to subprocess execution")
    import subprocess
    
    # Construct the command
    cmd = [
        sys.executable, "-m", "uvicorn", 
        app_module, 
        "--host", host, 
        "--port", str(port),
        "--reload"
    ]
    
    # Execute uvicorn directly
    try:
        logger.info(f"Executing command: {' '.join(cmd)}")
        # We use subprocess.run() with check=True to raise an exception on error
        process = subprocess.run(cmd, check=True)
        logger.info(f"Process exited with code {process.returncode}")
    except Exception as e:
        logger.error(f"Error starting uvicorn: {str(e)}", exc_info=True)
        sys.exit(1)