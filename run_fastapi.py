"""
Script to run the FastAPI application with uvicorn.
"""
import os
import sys
import logging
import uvicorn

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

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

def run_app():
    """Run the FastAPI application with uvicorn."""
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting FastAPI application on port {port}")
    
    # Run the FastAPI app
    uvicorn.run(
        "backend.api_gateway:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

if __name__ == "__main__":
    run_app()