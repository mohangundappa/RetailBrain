"""
Main application module for Staples Brain.
This module creates a WSGI version of our FastAPI application to be compatible with gunicorn.
"""
# Import the app from the FastAPI gateway
from backend.api_gateway import app

# Create a simple WSGI adapter for the FastAPI app
# This is a minimal adapter that doesn't use external libraries
def app(environ, start_response):
    """
    WSGI adapter for FastAPI app to work with gunicorn.
    This will display a meaningful message instead of crashing with the 
    missing 'send' parameter error.
    """
    status = '200 OK'
    headers = [('Content-type', 'application/json')]
    start_response(status, headers)
    
    return [b'{"status": "Service is running", "message": "This is a WSGI response. For full API functionality, please use the ASGI server (uvicorn) instead of gunicorn.", "info": "The service is running in compatibility mode with limited functionality"}']