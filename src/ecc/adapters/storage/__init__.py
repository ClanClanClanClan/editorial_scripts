"""Storage adapters for ECC database operations."""

from .repository import (
    AIAnalysisRepository,
    AuditRepository,
    AuthorRepository,
    ManuscriptRepository,
)

__all__ = [
    "ManuscriptRepository",
    "AuthorRepository",
    "AIAnalysisRepository",
    "AuditRepository",
]
