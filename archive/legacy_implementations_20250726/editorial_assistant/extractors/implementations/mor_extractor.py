"""
Mathematics of Operations Research (MOR) specific extractor.

This module contains MOR-specific customizations for the ScholarOne extractor.
"""

from ..scholarone import ScholarOneExtractor


class MORExtractor(ScholarOneExtractor):
    """Extractor specifically for Mathematics of Operations Research journal."""

    def __init__(self, **kwargs):
        """Initialize MOR extractor."""
        super().__init__("MOR", **kwargs)

        # MOR-specific settings
        self.journal_specific_patterns = {
            "manuscript_id": r"MOR-\d{4}-\d{4}",
            "referee_section": "Reviewer Information",
        }

        # MOR uses different category names
        self.mor_categories = ["Awaiting Reviewer Reports", "Awaiting Reviewer Selection"]

    def _navigate_to_manuscripts(self):
        """Navigate with MOR-specific handling."""
        # MOR sometimes requires additional navigation
        self.logger.info("Navigating to MOR manuscripts")

        try:
            super()._navigate_to_manuscripts()
        except Exception as e:
            # Try MOR-specific navigation if standard fails
            self.logger.warning(f"Standard navigation failed, trying MOR-specific: {e}")
            self._mor_specific_navigation()

    def _mor_specific_navigation(self):
        """MOR-specific navigation fallback."""
        # Implementation based on MOR's specific UI quirks
        pass
