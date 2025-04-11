#!/usr/bin/env python
"""
Run script for the Staples Brain FastAPI application using uvicorn (ASGI).
This is the recommended way to run the FastAPI application.
"""
import os
import sys
import logging
import argparse
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

def run_application(host="0.0.0.0", port=5000, reload=True):
    """Run the FastAPI application using uvicorn."""
    try:
        import uvicorn
        
        # Configure uvicorn
        uvicorn_config = {
            "app": "backend.api_gateway:app",
            "host": host,
            "port": port,
            "reload": reload,
            "log_level": "info",
            "workers": 1
        }
        
        # Log configuration
        logger.info(f"Starting uvicorn server with configuration: {uvicorn_config}")
        
        # Run uvicorn
        uvicorn.run(**uvicorn_config)
        
    except ImportError:
        logger.error("uvicorn is not installed. Please install it with 'pip install uvicorn'.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting uvicorn server: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the Staples Brain FastAPI application")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    
    args = parser.parse_args()
    
    # Run the application
    run_application(
        host=args.host,
        port=args.port,
        reload=not args.no_reload
    )