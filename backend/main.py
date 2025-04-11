"""
Main application module for Staples Brain.
This is the entry point for the FastAPI application.
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

# Import app from API gateway
from backend.api_gateway import app

# This is used when running the FastAPI app directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, reload=True)