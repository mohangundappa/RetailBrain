"""
Main application module for Staples Brain.
This module creates a WSGI version of our FastAPI application to be compatible with gunicorn.
"""
import os
import sys
import logging
import json
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

# Import the app from the FastAPI gateway
# Renamed to fastapi_app to avoid name conflict with the WSGI app function
from backend.api_gateway import app as fastapi_app

try:
    # Try to import the ASGI to WSGI adapter
    import uvicorn
    from asgi_wsgi import asgi_to_wsgi
    # Convert our FastAPI (ASGI) app to a WSGI app
    wsgi_app = asgi_to_wsgi(fastapi_app)
    logger.info("Using ASGI-to-WSGI adapter for full API functionality")
    
    # Create the WSGI application
    def app(environ, start_response):
        return wsgi_app(environ, start_response)
        
except ImportError:
    # Fall back to a simple WSGI app if adapter is not available
    logger.warning("ASGI-to-WSGI adapter not available, using limited WSGI app")
    
    def app(environ, start_response):
        """
        WSGI adapter for FastAPI app to work with gunicorn.
        This will display a meaningful message instead of crashing with the 
        missing 'send' parameter error.
        """
        status = '200 OK'
        headers = [('Content-type', 'application/json')]
        start_response(status, headers)
        
        response = {
            "status": "Service is running", 
            "message": "This is a WSGI response. For full API functionality, please use the ASGI server (uvicorn) instead of gunicorn.", 
            "info": "The service is running in compatibility mode with limited functionality",
            "endpoints": [
                "/api/v1/health",
                "/api/v1/agents",
                "/api/v1/chat",
                "/api/v1/telemetry/sessions",
                "/api/v1/circuit-breakers"
            ]
        }
        
        return [json.dumps(response).encode('utf-8')]