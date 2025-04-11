"""
Database configuration for Staples Brain.
Configures SQLAlchemy with PostgreSQL and PgVector support.
"""

import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("database")

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")

# Ensure DATABASE_URL is set and convert to async format if needed
if DATABASE_URL:
    # Convert standard PostgreSQL URL to asyncpg format if needed
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    logger.info(f"Database URL configured: {DATABASE_URL.split('@')[0]}@...")
else:
    logger.warning("DATABASE_URL not found in environment variables")
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost/staples_brain"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL logging
    future=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=300,
    pool_pre_ping=True
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Create base class for models
Base = declarative_base()

# Dependency for FastAPI endpoints
async def get_db():
    """
    Async database session dependency for FastAPI.
    
    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

# Function to create all tables
async def create_tables():
    """Create all tables defined in the models"""
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered with Base
            from database.models import Conversation, AgentConfig, TelemetryEvent
            
            # Create tables
            await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise