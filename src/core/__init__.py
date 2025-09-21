"""Core components for the editorial extraction system."""

from .base_extractor import BaseExtractor
from .browser_manager import BrowserManager
from .credential_manager import CredentialManager
from .data_models import (
    Author,
    Document,
    DocumentType,
    Manuscript,
    ManuscriptStatus,
    Referee,
    RefereeStatus,
)

__all__ = [
    "Manuscript",
    "Referee",
    "Author",
    "Document",
    "ManuscriptStatus",
    "RefereeStatus",
    "DocumentType",
    "BaseExtractor",
    "BrowserManager",
    "CredentialManager",
]
