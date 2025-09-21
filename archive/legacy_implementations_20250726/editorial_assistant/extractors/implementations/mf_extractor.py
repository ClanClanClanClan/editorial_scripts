"""
Mathematical Finance (MF) specific extractor.

This module contains MF-specific customizations for the ScholarOne extractor.
"""

from ..scholarone import ScholarOneExtractor


class MFExtractor(ScholarOneExtractor):
    """Extractor specifically for Mathematical Finance journal."""

    def __init__(self, **kwargs):
        """Initialize MF extractor."""
        super().__init__("MF", **kwargs)

        # MF-specific settings
        self.journal_specific_patterns = {
            "manuscript_id": r"MAFI-\d{4}-\d{4}",
            "referee_section": "Reviewer List",
        }

    def _extract_referees(self):
        """Extract referees with MF-specific handling."""
        # Use base implementation with MF-specific logging
        self.logger.info("Extracting referees for Mathematical Finance")
        referees = super()._extract_referees()

        # MF-specific post-processing if needed
        for referee in referees:
            # MF uses specific date format
            if referee.dates.invited:
                self.logger.debug(f"MF Referee: {referee.name} - Invited: {referee.dates.invited}")

        return referees
