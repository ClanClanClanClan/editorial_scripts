"""
Core components for the Editorial Assistant system.

This module contains the foundational classes and utilities that power
the journal extraction system.
"""

from .base_extractor import BaseExtractor
from .browser_manager import BrowserManager
from .pdf_handler import PDFHandler
from .data_models import (
    Referee,
    Manuscript,
    Journal,
    RefereeDates,
    RefereeStatus,
    ExtractionResult,
)
from .exceptions import (
    ExtractionError,
    LoginError,
    NavigationError,
    PDFDownloadError,
    RefereeDataError,
)

__all__ = [
    # Core Classes
    "BaseExtractor",
    "BrowserManager",
    "PDFHandler",
    
    # Data Models
    "Referee",
    "Manuscript",
    "Journal",
    "RefereeDates",
    "RefereeStatus",
    "ExtractionResult",
    
    # Exceptions
    "ExtractionError",
    "LoginError",
    "NavigationError",
    "PDFDownloadError",
    "RefereeDataError",
]