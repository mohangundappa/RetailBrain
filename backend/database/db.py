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
if DB_URL:
    # Parse the DB URL to handle sslmode parameter (which asyncpg doesn't accept directly)
    import re
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    # Parse URL
    parsed_url = urlparse(DB_URL)
    
    # Parse query parameters
    query_params = parse_qs(parsed_url.query)
    
    # Remove sslmode parameter from query as asyncpg doesn't accept it in the connection string
    if 'sslmode' in query_params:
        del query_params['sslmode']
        
    # Rebuild query string
    query_string = urlencode(query_params, doseq=True)
    
    # Rebuild URL without sslmode parameter
    parts = list(parsed_url)
    parts[4] = query_string  # Replace query part
    clean_url = urlunparse(parts)
    
    # Convert to asyncpg if needed
    if not clean_url.startswith("postgresql+asyncpg://"):
        DB_URL = clean_url.replace("postgresql://", "postgresql+asyncpg://")
    else:
        DB_URL = clean_url

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