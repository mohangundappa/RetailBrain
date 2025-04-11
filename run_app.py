#!/usr/bin/env python
"""
Run the FastAPI application using uvicorn.
"""
import os
import sys
import logging
import uvicorn
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

def main():
    """Run the application."""
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting FastAPI application on port {port}")
    
    # Run with uvicorn directly - this is the ASGI server suitable for FastAPI
    uvicorn.run(
        "asgi:application",
        host="0.0.0.0",
        port=port,
        reload=True
    )

if __name__ == "__main__":
    main()