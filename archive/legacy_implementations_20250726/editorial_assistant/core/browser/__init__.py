"""
Unified Browser Management for Editorial Assistant

This module provides standardized browser session management
with anti-detection capabilities and resource cleanup.
"""

from .browser_config import BrowserConfig, BrowserType
from .browser_pool import BrowserPool
from .browser_session import BrowserSession

__all__ = ["BrowserSession", "BrowserPool", "BrowserConfig", "BrowserType"]
