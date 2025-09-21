"""Async PostgreSQL connection management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.ecc.infrastructure.database.models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages async PostgreSQL connections."""

    def __init__(self, database_url: str, echo: bool = False) -> None:
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL (must start with postgresql+asyncpg://)
            echo: Whether to log SQL queries
        """
        if not database_url.startswith("postgresql+asyncpg://"):
            raise ValueError("Database URL must use postgresql+asyncpg:// scheme")

        self.database_url = database_url
        self.echo = echo
        self.engine: AsyncEngine | None = None
        self.async_session_factory: async_sessionmaker[AsyncSession] | None = None

    async def initialize(self) -> None:
        """Initialize database connection and create tables."""
        logger.info("Initializing database connection")

        # Create async engine with connection pooling
        self.engine = create_async_engine(
            self.database_url,
            echo=self.echo,
            future=True,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
        )

        # Create async session factory
        self.async_session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Create tables if they don't exist
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized successfully")

    async def close(self) -> None:
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an async database session.

        Yields:
            AsyncSession: Database session for queries
        """
        if not self.async_session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """
        Check if database is healthy.

        Returns:
            bool: True if database is accessible
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def get_table_stats(self) -> dict[str, int]:
        """
        Get statistics about database tables.

        Returns:
            dict: Table names and row counts
        """
        stats: dict[str, int] = {}

        try:
            async with self.get_session() as session:
                # Get row counts for each table
                for table_name in Base.metadata.tables.keys():
                    # Note: table names come from application metadata
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    stats[table_name] = int(result.scalar() or 0)

        except Exception as e:
            logger.error(f"Failed to get table stats: {e}")

        return stats


# Global database manager instance
_db_manager: DatabaseManager | None = None


async def initialize_database(database_url: str, echo: bool = False) -> None:
    """
    Initialize the global database manager.

    Args:
        database_url: PostgreSQL connection URL
        echo: Whether to log SQL queries
    """
    global _db_manager

    if _db_manager is not None:
        logger.warning("Database already initialized")
        return

    _db_manager = DatabaseManager(database_url, echo)
    await _db_manager.initialize()


async def get_database_manager() -> DatabaseManager:
    """
    Get the global database manager.

    Returns:
        DatabaseManager: The initialized database manager

    Raises:
        RuntimeError: If database is not initialized
    """
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call initialize_database() first.")
    return _db_manager


async def close_database() -> None:
    """Close the global database connection."""
    global _db_manager

    if _db_manager is not None:
        await _db_manager.close()
        _db_manager = None
