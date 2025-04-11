"""
Database connection and setup for Staples Brain.
"""
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Get database URL from environment variable
DB_URL = os.environ.get("DATABASE_URL")

# Convert SQLAlchemy URL to async format if not already
if DB_URL and not DB_URL.startswith("postgresql+asyncpg://"):
    DB_URL = DB_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
engine = create_async_engine(
    DB_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=20,
    max_overflow=10,
    echo=False,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session for dependency injection.
    
    Returns:
        AsyncGenerator yielding AsyncSession
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()