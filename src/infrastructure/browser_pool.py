"""
Browser pool implementation for Playwright
Manages a pool of browser instances for concurrent scraping
"""

import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from playwright.async_api import (
    async_playwright, Browser, BrowserContext, 
    Page, Playwright, Error as PlaywrightError
)
try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None

from .config import get_settings
from ..core.ports.browser_pool import BrowserPool as BrowserPoolPort

logger = logging.getLogger(__name__)
settings = get_settings()


class PlaywrightBrowserPool(BrowserPoolPort):
    """Manages a pool of browser instances for efficient scraping"""
    
    def __init__(self, size: int = None):
        self.size = size or settings.browser_pool_size
        self.playwright: Optional[Playwright] = None
        self.browsers: List[Browser] = []
        self.available: asyncio.Queue[Browser] = asyncio.Queue()
        self.contexts: Dict[str, BrowserContext] = {}  # Session persistence
        self._lock = asyncio.Lock()
        self._initialized = False
        
    async def start(self) -> None:
        """Start the browser pool (port interface method)"""
        await self.initialize()
        
    async def stop(self) -> None:
        """Stop the browser pool (port interface method)"""
        await self.shutdown()
        
    @asynccontextmanager
    async def get_browser(self) -> AsyncGenerator[Browser, None]:
        """Get a browser instance from the pool (port interface method)"""
        if not self._initialized:
            await self.initialize()
            
        browser = await self.available.get()
        try:
            yield browser
        finally:
            await self.available.put(browser)
        
    async def initialize(self) -> None:
        """Initialize the browser pool"""
        if self._initialized:
            return
            
        async with self._lock:
            if self._initialized:
                return
                
            logger.info(f"Initializing browser pool with {self.size} instances")
            
            # Start Playwright
            self.playwright = await async_playwright().start()
            
            # Launch browsers
            for i in range(self.size):
                browser = await self._launch_browser()
                self.browsers.append(browser)
                await self.available.put(browser)
                logger.debug(f"Browser {i+1}/{self.size} launched")
                
            self._initialized = True
            logger.info("Browser pool initialized successfully")
    
    async def _launch_browser(self) -> Browser:
        """Launch a single browser instance with optimal settings"""
        launch_options = {
            'headless': settings.browser_headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size={},{}'.format(
                    settings.browser_viewport_width,
                    settings.browser_viewport_height
                )
            ]
        }
        
        if settings.browser_user_agent:
            launch_options['args'].append(f'--user-agent={settings.browser_user_agent}')
            
        return await self.playwright.chromium.launch(**launch_options)
    
    @asynccontextmanager
    async def acquire_page(self, session_id: Optional[str] = None):
        """Acquire a page from the pool with optional session persistence"""
        if not self._initialized:
            await self.initialize()
            
        browser = await self.available.get()
        
        try:
            # Get or create context
            if session_id and session_id in self.contexts:
                context = self.contexts[session_id]
                logger.debug(f"Reusing context for session {session_id}")
            else:
                context = await self._create_context(browser)
                if session_id:
                    self.contexts[session_id] = context
                    
            # Create new page
            page = await context.new_page()
            
            # Apply stealth mode
            if settings.browser_use_stealth and stealth_async:
                await stealth_async(page)
                
            # Set viewport
            await page.set_viewport_size({
                'width': settings.browser_viewport_width,
                'height': settings.browser_viewport_height
            })
            
            yield page
            
        finally:
            # Clean up page
            try:
                await page.close()
            except Exception as e:
                logger.warning(f"Error closing page: {e}")
                
            # Return browser to pool
            await self.available.put(browser)
    
    async def _create_context(self, browser: Browser) -> BrowserContext:
        """Create a new browser context with optimal settings"""
        context_options = {
            'viewport': {
                'width': settings.browser_viewport_width,
                'height': settings.browser_viewport_height
            },
            'ignore_https_errors': True,
            'java_script_enabled': True,
        }
        
        if settings.browser_user_agent:
            context_options['user_agent'] = settings.browser_user_agent
            
        return await browser.new_context(**context_options)
    
    async def clear_session(self, session_id: str) -> None:
        """Clear a specific session context"""
        if session_id in self.contexts:
            try:
                await self.contexts[session_id].close()
            except Exception as e:
                logger.warning(f"Error closing context {session_id}: {e}")
            finally:
                del self.contexts[session_id]
                logger.info(f"Session {session_id} cleared")
    
    async def shutdown(self) -> None:
        """Shutdown the browser pool"""
        if not self._initialized:
            return
            
        logger.info("Shutting down browser pool")
        
        # Close all contexts
        for session_id, context in self.contexts.items():
            try:
                await context.close()
            except Exception as e:
                logger.warning(f"Error closing context {session_id}: {e}")
                
        # Close all browsers
        for browser in self.browsers:
            try:
                await browser.close()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
                
        # Stop Playwright
        if self.playwright:
            await self.playwright.stop()
            
        self._initialized = False
        logger.info("Browser pool shutdown complete")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of the browser pool"""
        return {
            'initialized': self._initialized,
            'pool_size': self.size,
            'available_browsers': self.available.qsize(),
            'active_sessions': len(self.contexts),
            'timestamp': datetime.utcnow().isoformat()
        }


# Global browser pool instance
_browser_pool: Optional[PlaywrightBrowserPool] = None


async def get_browser_pool() -> PlaywrightBrowserPool:
    """Get or create the global browser pool"""
    global _browser_pool
    if _browser_pool is None:
        _browser_pool = PlaywrightBrowserPool()
        await _browser_pool.initialize()
    return _browser_pool


async def shutdown_browser_pool() -> None:
    """Shutdown the global browser pool"""
    global _browser_pool
    if _browser_pool:
        await _browser_pool.shutdown()
        _browser_pool = None