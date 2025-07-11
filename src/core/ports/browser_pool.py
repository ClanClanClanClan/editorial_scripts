"""
Browser Pool Port (Interface)
Defines the contract for browser management
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from playwright.async_api import Browser


class BrowserPool(ABC):
    """Abstract interface for browser pool management"""
    
    @abstractmethod
    async def start(self) -> None:
        """Start the browser pool"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the browser pool and cleanup"""
        pass
    
    @abstractmethod
    @asynccontextmanager
    async def get_browser(self) -> AsyncGenerator[Browser, None]:
        """Get a browser instance from the pool"""
        pass