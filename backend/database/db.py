"""
Database setup for Staples Brain.
"""
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Get database URL from environment
DB_URL = os.environ.get("DATABASE_URL")

# Convert to async URL if needed
if DB_URL and not DB_URL.startswith("postgresql+asyncpg://"):
    # Remove sslmode parameter if present in the URL
    if "sslmode=" in DB_URL:
        # Split URL to remove sslmode
        base_url, query_string = DB_URL.split("?", 1) if "?" in DB_URL else (DB_URL, "")
        query_params = query_string.split("&")
        filtered_params = [p for p in query_params if not p.startswith("sslmode=")]
        
        # Reconstruct the URL
        DB_URL = base_url
        if filtered_params:
            DB_URL = f"{base_url}?{'&'.join(filtered_params)}"
            
    # Convert to asyncpg
    DB_URL = DB_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
engine = create_async_engine(
    DB_URL,
    pool_recycle=300,
    pool_pre_ping=True,
    echo=False,
)

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# Create an async session for direct use
async_session = async_session_factory


# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    """Base class for all models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session.
    
    Yields:
        AsyncSession: Database session
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()