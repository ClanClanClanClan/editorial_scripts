"""
Browser Pool Management

Manages a pool of browser sessions for concurrent processing
with proper resource allocation and cleanup.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from .browser_config import BrowserConfig
from .browser_session import BrowserSession


class BrowserPool:
    """
    Manages a pool of browser sessions for concurrent processing.

    Provides efficient resource utilization and prevents browser session
    conflicts during concurrent extraction operations.
    """

    def __init__(
        self,
        pool_size: int = 3,
        config: BrowserConfig | None = None,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize browser pool.

        Args:
            pool_size: Maximum number of concurrent browser sessions
            config: Browser configuration template
            logger: Logger instance
        """
        self.pool_size = pool_size
        self.config = config or BrowserConfig()
        self.logger = logger or logging.getLogger(__name__)

        # Pool management
        self.available_sessions: asyncio.Queue = asyncio.Queue(maxsize=pool_size)
        self.active_sessions: list[BrowserSession] = []
        self.session_stats: dict[str, dict[str, Any]] = {}

        # Pool state
        self._is_initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """
        Initialize browser pool with configured sessions.

        Raises:
            RuntimeError: If pool initialization fails
        """
        if self._is_initialized:
            self.logger.warning("Browser pool already initialized")
            return

        async with self._lock:
            try:
                self.logger.info(f"Initializing browser pool with {self.pool_size} sessions")

                # Create initial browser sessions
                for i in range(self.pool_size):
                    session = BrowserSession(config=self.config, logger=self.logger)

                    await session.initialize()

                    # Track session
                    self.active_sessions.append(session)
                    self.session_stats[session._session_id] = {
                        "created_at": asyncio.get_event_loop().time(),
                        "usage_count": 0,
                        "last_used": None,
                        "errors": 0,
                    }

                    # Add to available queue
                    await self.available_sessions.put(session)

                    self.logger.debug(f"Created browser session {i+1}/{self.pool_size}")

                self._is_initialized = True
                self.logger.info(
                    f"Browser pool initialized successfully with {len(self.active_sessions)} sessions"
                )

            except Exception as e:
                self.logger.error(f"Failed to initialize browser pool: {str(e)}")
                await self.cleanup()
                raise RuntimeError(f"Browser pool initialization failed: {str(e)}")

    async def acquire(self, timeout: int = 30) -> BrowserSession:
        """
        Acquire a browser session from the pool.

        Args:
            timeout: Timeout for acquiring session in seconds

        Returns:
            BrowserSession instance

        Raises:
            TimeoutError: If no session available within timeout
            RuntimeError: If pool not initialized
        """
        if not self._is_initialized:
            raise RuntimeError("Browser pool not initialized")

        try:
            # Wait for available session
            session = await asyncio.wait_for(self.available_sessions.get(), timeout=timeout)

            # Update usage stats
            session_id = session._session_id
            if session_id in self.session_stats:
                stats = self.session_stats[session_id]
                stats["usage_count"] += 1
                stats["last_used"] = asyncio.get_event_loop().time()

            self.logger.debug(f"Acquired browser session: {session_id}")
            return session

        except TimeoutError:
            self.logger.error(f"Timeout acquiring browser session after {timeout}s")
            raise TimeoutError(f"No browser session available within {timeout} seconds")
        except Exception as e:
            self.logger.error(f"Error acquiring browser session: {str(e)}")
            raise

    async def release(self, session: BrowserSession) -> None:
        """
        Release browser session back to the pool.

        Args:
            session: Browser session to release
        """
        if not session or not session._is_initialized:
            self.logger.warning("Attempted to release invalid session")
            return

        try:
            session_id = session._session_id

            # Perform session cleanup/reset
            await self._reset_session(session)

            # Return to pool
            await self.available_sessions.put(session)

            self.logger.debug(f"Released browser session: {session_id}")

        except Exception as e:
            self.logger.error(f"Error releasing session: {str(e)}")

            # If release fails, recreate session
            await self._recreate_session(session)

    async def _reset_session(self, session: BrowserSession) -> None:
        """
        Reset session state for reuse.

        Args:
            session: Browser session to reset
        """
        try:
            if session.driver:
                # Clear cookies and cache
                session.driver.delete_all_cookies()
                session.driver.execute_script("window.localStorage.clear();")
                session.driver.execute_script("window.sessionStorage.clear();")

                # Navigate to blank page
                session.driver.get("about:blank")

                # Dismiss any overlays
                await session.dismiss_overlays()

        except Exception as e:
            self.logger.warning(f"Session reset error: {str(e)}")
            # If reset fails, session will be recreated on next use

    async def _recreate_session(self, old_session: BrowserSession) -> None:
        """
        Recreate a failed session.

        Args:
            old_session: Failed session to replace
        """
        try:
            # Remove old session
            if old_session in self.active_sessions:
                self.active_sessions.remove(old_session)

            # Clean up old session
            await old_session.cleanup()

            # Create new session
            new_session = BrowserSession(config=self.config, logger=self.logger)

            await new_session.initialize()

            # Track new session
            self.active_sessions.append(new_session)
            self.session_stats[new_session._session_id] = {
                "created_at": asyncio.get_event_loop().time(),
                "usage_count": 0,
                "last_used": None,
                "errors": 0,
            }

            # Add to available queue
            await self.available_sessions.put(new_session)

            self.logger.info(f"Recreated browser session: {new_session._session_id}")

        except Exception as e:
            self.logger.error(f"Failed to recreate session: {str(e)}")

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on browser pool.

        Returns:
            Dictionary containing pool health metrics
        """
        try:
            current_time = asyncio.get_event_loop().time()

            # Calculate pool metrics
            total_sessions = len(self.active_sessions)
            available_sessions = self.available_sessions.qsize()
            active_sessions = total_sessions - available_sessions

            # Calculate usage statistics
            total_usage = sum(stats["usage_count"] for stats in self.session_stats.values())
            avg_usage = total_usage / total_sessions if total_sessions > 0 else 0

            # Check for problematic sessions
            stale_sessions = []
            for session_id, stats in self.session_stats.items():
                if stats["last_used"]:
                    idle_time = current_time - stats["last_used"]
                    if idle_time > 3600:  # 1 hour
                        stale_sessions.append(session_id)

            health_data = {
                "pool_size": self.pool_size,
                "total_sessions": total_sessions,
                "available_sessions": available_sessions,
                "active_sessions": active_sessions,
                "total_usage": total_usage,
                "average_usage": avg_usage,
                "stale_sessions": len(stale_sessions),
                "is_healthy": available_sessions > 0 and total_sessions == self.pool_size,
            }

            return health_data

        except Exception as e:
            self.logger.error(f"Health check error: {str(e)}")
            return {"is_healthy": False, "error": str(e)}

    async def get_session_stats(self) -> dict[str, Any]:
        """
        Get detailed session statistics.

        Returns:
            Dictionary containing session usage statistics
        """
        return self.session_stats.copy()

    async def cleanup(self) -> None:
        """Clean up browser pool and all sessions."""
        async with self._lock:
            try:
                self.logger.info("Cleaning up browser pool")

                # Clean up all active sessions
                cleanup_tasks = []
                for session in self.active_sessions:
                    cleanup_tasks.append(session.cleanup())

                if cleanup_tasks:
                    await asyncio.gather(*cleanup_tasks, return_exceptions=True)

                # Clear pool state
                self.active_sessions.clear()
                self.session_stats.clear()

                # Clear queue
                while not self.available_sessions.empty():
                    try:
                        self.available_sessions.get_nowait()
                    except asyncio.QueueEmpty:
                        break

                self._is_initialized = False
                self.logger.info("Browser pool cleanup completed")

            except Exception as e:
                self.logger.error(f"Pool cleanup error: {str(e)}")


@asynccontextmanager
async def browser_pool(
    pool_size: int = 3,
    config: BrowserConfig | None = None,
    logger: logging.Logger | None = None,
):
    """
    Async context manager for browser pools.

    Args:
        pool_size: Number of browser sessions in pool
        config: Browser configuration
        logger: Logger instance

    Yields:
        BrowserPool instance
    """
    pool = BrowserPool(pool_size, config, logger)
    try:
        await pool.initialize()
        yield pool
    finally:
        await pool.cleanup()


@asynccontextmanager
async def pooled_browser_session(pool: BrowserPool, timeout: int = 30):
    """
    Async context manager for acquiring pooled browser sessions.

    Args:
        pool: Browser pool instance
        timeout: Acquisition timeout in seconds

    Yields:
        BrowserSession instance from pool
    """
    session = await pool.acquire(timeout)
    try:
        yield session
    finally:
        await pool.release(session)
