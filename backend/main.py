"""
Main application module for Staples Brain.
This is the entry point for the Flask application.
"""
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("staples_brain.log")
    ]
)

logger = logging.getLogger("staples_brain")

# Load environment variables
from dotenv import load_dotenv
print(f"Loading environment from {os.path.abspath('.env')}")
load_dotenv()

# Import app factory
from backend.flask_app import create_app

# Create the Flask app
app = create_app()

# This is used when running the Flask app directly
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)