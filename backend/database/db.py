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