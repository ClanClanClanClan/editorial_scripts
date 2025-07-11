"""
Editorial Assistant - Professional Journal Referee Management System

A comprehensive system for extracting and managing referee data from academic journal
submission systems.
"""

__version__ = "1.0.0"
__author__ = "Editorial Assistant Team"

from .core.data_models import (
    Referee,
    Manuscript,
    Journal,
    RefereeDates,
    RefereeStatus,
    ExtractionResult
)

from .core.base_extractor import BaseExtractor
from .core.browser_manager import BrowserManager
from .core.pdf_handler import PDFHandler

__all__ = [
    # Data Models
    "Referee",
    "Manuscript", 
    "Journal",
    "RefereeDates",
    "RefereeStatus",
    "ExtractionResult",
    
    # Core Components
    "BaseExtractor",
    "BrowserManager",
    "PDFHandler",
]