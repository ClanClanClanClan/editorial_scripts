"""Core components for the editorial extraction system."""

from .data_models import (
    Manuscript,
    Referee,
    Author,
    Document,
    ManuscriptStatus,
    RefereeStatus,
    DocumentType
)
from .base_extractor import BaseExtractor
from .browser_manager import BrowserManager
from .credential_manager import CredentialManager

__all__ = [
    'Manuscript',
    'Referee', 
    'Author',
    'Document',
    'ManuscriptStatus',
    'RefereeStatus',
    'DocumentType',
    'BaseExtractor',
    'BrowserManager',
    'CredentialManager'
]