"""
Unified Browser Management for Editorial Assistant

This module provides standardized browser session management
with anti-detection capabilities and resource cleanup.
"""

from .browser_session import BrowserSession
from .browser_pool import BrowserPool  
from .browser_config import BrowserConfig, BrowserType

__all__ = [
    'BrowserSession',
    'BrowserPool', 
    'BrowserConfig',
    'BrowserType'
]