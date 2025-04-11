"""
Main application module for Staples Brain.
This is the entry point for the Flask application.
Simply imports from the backend package.
"""
from backend.main import app

# This is needed for Gunicorn to find the app
# No additional code required - all logic is now in the backend package