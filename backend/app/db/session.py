"""
Database Session Configuration

Async SQLAlchemy session factory for PostgreSQL.
Sync session factory for Celery tasks.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.core.config import settings


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True for SQL logging in development
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# Create sync engine for Celery tasks
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

# Sync session factory for Celery tasks
sync_session_maker = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncSession:
    """Get async database session"""
    async with async_session_maker() as session:
        yield session
