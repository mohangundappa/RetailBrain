"""
ASGI adapter script for the Staples Brain FastAPI application.
This script adapts the FastAPI ASGI application to work with gunicorn.
"""
import asyncio
import logging
import os
import sys
import json
from typing import Any, Callable, Dict, List, Tuple, Union

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
logger.info("Starting Staples Brain ASGI adapter")

# Import the FastAPI app
try:
    from backend.api_gateway import app as fastapi_app
    logger.info("Successfully imported FastAPI app")
except ImportError as e:
    logger.error(f"Failed to import FastAPI app: {str(e)}")
    fastapi_app = None

# WSGI application
def app(environ, start_response):
    """
    WSGI application that returns a simple JSON response for all routes.
    """
    path_info = environ.get('PATH_INFO', '')
    method = environ.get('REQUEST_METHOD', 'GET')
    
    logger.info(f"WSGI request: {method} {path_info}")
    
    # Default response
    status = '200 OK'
    headers = [('Content-type', 'application/json')]
    
    if fastapi_app is None:
        # Error response if FastAPI app couldn't be imported
        status = '500 Internal Server Error'
        response = {
            "status": "error",
            "message": "Failed to load FastAPI application",
            "error": "Import error"
        }
    else:
        # Information response
        response = {
            "status": "running",
            "message": "Staples Brain API is available via uvicorn ASGI server only",
            "info": "Please use the uvicorn server to access the full FastAPI functionality",
            "api_version": "1.0.0",
            "path": path_info,
            "method": method,
            "documentation": "/docs",
            "endpoints": [
                "/api/v1/health",
                "/api/v1/agents",
                "/api/v1/chat",
                "/api/v1/telemetry/sessions",
                "/api/v1/circuit-breakers"
            ]
        }
    
    start_response(status, headers)
    return [json.dumps(response).encode('utf-8')]