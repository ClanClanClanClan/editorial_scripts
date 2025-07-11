"""
Async database engine and session management
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from ..config import get_settings

# Global engine and session factory - initialized lazily
_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker] = None


def _get_or_create_engine() -> AsyncEngine:
    """Get or create async engine, ensuring it's in the current event loop"""
    global _engine
    
    # Always recreate engine to ensure it's in the current event loop
    settings = get_settings()
    
    # Check if we're in a test environment
    try:
        # Try to get current event loop
        loop = asyncio.get_running_loop()
        is_test_env = hasattr(loop, '_testserver_loop') or 'test' in str(loop)
    except RuntimeError:
        is_test_env = False
    
    # Aggressive connection pool optimization for both test and production
    if is_test_env:
        # Test environment: minimal pool to control connection count
        pool_size = 2
        max_overflow = 3
        pool_timeout = 5
        pool_recycle = 120  # 2 minutes - faster cleanup
    else:
        # Production environment: balanced pool for performance
        pool_size = 10
        max_overflow = 5
        pool_timeout = 20
        pool_recycle = 1800  # 30 minutes
    
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        # No NullPool - use proper pooling in all environments
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_pre_ping=True,
        pool_recycle=pool_recycle,
        # Aggressive connection optimization
        connect_args={
            "server_settings": {
                "application_name": "editorial_scripts_api",
                "idle_in_transaction_session_timeout": "30000",  # 30 seconds
                "statement_timeout": "30000",  # 30 seconds
            },
            # Shorter timeouts for faster cleanup
            "command_timeout": 15,
        },
        # Force connection cleanup
        pool_reset_on_return="commit"
    )
    
    return _engine


def _get_session_factory() -> async_sessionmaker:
    """Get session factory for current engine"""
    global _async_session_factory
    
    engine = _get_or_create_engine()
    _async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    return _async_session_factory

# Base class for models
Base = declarative_base()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with automatic cleanup"""
    session_factory = _get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables"""
    engine = _get_or_create_engine()
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from . import models  # noqa
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections and clean up resources"""
    global _engine, _async_session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
    _async_session_factory = None


async def get_connection_info() -> dict:
    """Get current connection pool information for monitoring"""
    global _engine
    if _engine and hasattr(_engine.pool, 'size'):
        return {
            'pool_size': _engine.pool.size(),
            'checked_in': _engine.pool.checkedin(),
            'checked_out': _engine.pool.checkedout(),
            'overflow': _engine.pool.overflow(),
            'invalid': _engine.pool.invalid()
        }
    return {'status': 'no_pool_info'}


def get_engine() -> AsyncEngine:
    """Public function to get the current engine"""
    return _get_or_create_engine()