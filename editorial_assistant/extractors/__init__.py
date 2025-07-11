"""
Journal-specific extractor implementations.

This module contains extractors for different journal submission platforms.
"""

from .scholarone import ScholarOneExtractor

__all__ = [
    "ScholarOneExtractor",
]