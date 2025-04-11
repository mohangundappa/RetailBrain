"""
Starter script for FastAPI API Gateway application.
"""

import os
import asyncio
import logging
import uvicorn
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("startup")

# Load environment variables
load_dotenv()

# Try to initialize database tables
async def init_db():
    """Initialize database tables"""
    try:
        from database.db import create_tables
        await create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        logger.warning("Continuing without database initialization")

async def verify_openai_key():
    """Verify OpenAI API key is set"""
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        logger.warning("OPENAI_API_KEY not found in environment variables")
        logger.warning("You will need to set OPENAI_API_KEY for the API to function properly")
    else:
        logger.info("OPENAI_API_KEY found in environment variables")

async def verify_db_connection():
    """Verify database connection"""
    try:
        from sqlalchemy import text
        from database.db import engine
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            if result:
                logger.info("Database connection verified")
            else:
                logger.warning("Database connection test failed")
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        logger.warning("Database functionality will not be available")

async def setup():
    """Run setup tasks"""
    logger.info("Running setup tasks...")
    
    # Verify OpenAI API key
    await verify_openai_key()
    
    # Verify database connection
    await verify_db_connection()
    
    # Initialize database tables
    await init_db()
    
    logger.info("Setup tasks completed")

def start_api():
    """Start the FastAPI API Gateway"""
    # Run setup tasks
    asyncio.run(setup())
    
    # Start the API server
    logger.info("Starting API Gateway...")
    uvicorn.run(
        "api_gateway:app",
        host="0.0.0.0",
        port=int(os.environ.get("API_PORT", 8000)),
        reload=os.environ.get("APP_ENV") == "development"
    )

if __name__ == "__main__":
    start_api()