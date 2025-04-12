"""
Main application module for Staples Brain.
This is the entry point for the FastAPI application.

This unified main module combines the functionality from:
1. The original main.py
2. The start_api.py module

It provides a single entry point for running the Staples Brain API.
"""
import os
import sys
import logging
import asyncio
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
load_dotenv()

# Import app from API gateway
from backend.api_gateway import app

async def init_db():
    """Initialize the database."""
    logger.info("Initializing database tables...")
    try:
        from sqlalchemy import create_engine, text
        from backend.database.db import Base, DB_URL
        
        # Convert to sync URL for initialization
        sync_url = DB_URL.replace("postgresql+asyncpg://", "postgresql://")
        
        # Create engine
        engine = create_engine(sync_url)
        
        # Create vector extension first
        with engine.connect() as connection:
            logger.info("Creating pgvector extension...")
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.commit()
            logger.info("pgvector extension created successfully")
        
        # Create tables
        Base.metadata.create_all(engine)
        
        logger.info("Database tables initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}", exc_info=True)
        raise

def run_api():
    """Run the API gateway using uvicorn."""
    # Get host and port from environment or use defaults
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", 5000))
    
    logger.info(f"Starting Staples Brain API on {host}:{port}")
    
    # Run with uvicorn
    import uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=True if os.environ.get("ENVIRONMENT") != "production" else False
    )

# This is used when running the FastAPI app directly
if __name__ == "__main__":
    # Initialize the database
    asyncio.run(init_db())
    
    # Run the API
    run_api()