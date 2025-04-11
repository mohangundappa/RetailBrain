"""
ASGI application for Staples Brain.
This script is the entry point for the ASGI server (uvicorn).
"""
from backend.api_gateway import app

# This is used by uvicorn to run the FastAPI app
application = app