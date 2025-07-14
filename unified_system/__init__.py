"""
Unified Editorial Scripts System
A comprehensive extraction framework for academic journal management
"""

__version__ = "1.0.0"
__author__ = "Editorial Scripts Team"

# Core components only (extractors moved to src/infrastructure/scrapers/)
from .core.base_extractor import BaseExtractor, Manuscript, Referee

__all__ = [
    "BaseExtractor",
    "Manuscript", 
    "Referee",
]