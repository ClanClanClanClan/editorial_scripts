"""
Base Extractor Compatibility Class

Provides a base class for all extractor stubs to maintain compatibility
with V2 production scripts while V3 implementation is in development.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from editorial_assistant.core.data_models import JournalConfig, Manuscript

logger = logging.getLogger(__name__)


class BaseExtractorV2Compat(ABC):
    """
    Base class for V2 extractor compatibility.

    This provides the interface that production scripts expect,
    but with stub implementations that log warnings about
    reduced functionality during V3 development.
    """

    def __init__(self, config: JournalConfig):
        """Initialize the extractor with journal configuration."""
        self.config = config
        self.journal_code = config.code
        self.journal_name = config.name
        logger.warning(
            f"V2 compatibility extractor initialized for {self.journal_name} ({self.journal_code}) - "
            "Limited functionality available during V3 development"
        )

    @abstractmethod
    def extract_all_manuscripts(self, **kwargs) -> list[Manuscript]:
        """
        Extract all manuscripts from the journal platform.

        This is the main method that production scripts call.
        Each extractor must implement this method.
        """
        pass

    def validate_login(self) -> bool:
        """
        Stub method for login validation.

        Returns:
            bool: Always False in compatibility mode
        """
        logger.warning(
            f"{self.journal_code} login validation not available in V2 compatibility mode"
        )
        return False

    def get_extraction_summary(self) -> dict[str, Any]:
        """
        Get summary of last extraction.

        Returns:
            Dict with summary information (minimal in compatibility mode)
        """
        return {
            "journal_code": self.journal_code,
            "journal_name": self.journal_name,
            "total_manuscripts": 0,
            "total_referees": 0,
            "extraction_status": "compatibility_mode",
            "warnings": ["V2 compatibility mode - reduced functionality"],
        }

    def cleanup_resources(self) -> None:
        """Clean up any resources."""
        logger.info(f"{self.journal_code} extractor cleanup completed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup_resources()


def create_stub_manuscripts(journal_code: str, count: int = 0) -> list[Manuscript]:
    """
    Create stub manuscript objects for compatibility.

    Args:
        journal_code: The journal code
        count: Number of stub manuscripts to create

    Returns:
        List of empty Manuscript objects
    """
    manuscripts = []
    for i in range(count):
        manuscript = Manuscript(
            manuscript_id=f"{journal_code}-STUB-{i+1:03d}",
            title=f"[V2 Compatibility Mode] Manuscript {i+1} for {journal_code}",
            authors=[],
            referees=[],
            abstract="V2 compatibility mode - actual data not available",
            status="compatibility_mode",
        )
        manuscripts.append(manuscript)

    return manuscripts
