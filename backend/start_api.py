"""
Entry point for running the Staples Brain API Gateway.
"""
import os
import sys
import logging
import asyncio

import uvicorn
from dotenv import load_dotenv

from backend.api_gateway import app

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

# Load environment variables
load_dotenv()

def run_api():
    """Run the API gateway using uvicorn."""
    # Get host and port from environment or use defaults
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", 8000))
    
    logger.info(f"Starting Staples Brain API on {host}:{port}")
    
    # Run with uvicorn
    uvicorn.run(
        "backend.api_gateway:app",
        host=host,
        port=port,
        reload=True if os.environ.get("ENVIRONMENT") != "production" else False
    )


async def init_db():
    """Initialize the database."""
    try:
        from sqlalchemy import create_engine
        from backend.database.db import Base, DB_URL
        
        # Convert to sync URL for initialization
        sync_url = DB_URL.replace("postgresql+asyncpg://", "postgresql://")
        
        # Create tables
        engine = create_engine(sync_url)
        Base.metadata.create_all(engine)
        
        logger.info("Database tables created")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    # Initialize the database
    asyncio.run(init_db())
    
    # Run the API
    run_api()