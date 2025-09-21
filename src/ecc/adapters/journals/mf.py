"""Mathematical Finance (MF) journal adapter - ScholarOne implementation."""

from src.ecc.adapters.journals.base import JournalConfig
from src.ecc.adapters.journals.scholarone import ScholarOneAdapter
from src.ecc.core.domain.models import Manuscript


class MFAdapter(ScholarOneAdapter):
    """Mathematical Finance journal adapter."""

    def __init__(self, headless: bool = True):
        config = JournalConfig(
            journal_id="MF",
            name="Mathematical Finance",
            url="https://mc.manuscriptcentral.com/mafi",
            platform="ScholarOne",
            headless=headless,
        )
        super().__init__(config)

    def _get_manuscript_pattern(self) -> str:
        """Get MF-specific manuscript ID pattern."""
        return r"MAFI-\d{4}-\d{4}"

    async def get_default_categories(self) -> list[str]:
        """Get default manuscript categories for MF."""
        return [
            "Awaiting AE Recommendation",
            "Awaiting Referee Reports",
            "Under Review",
            "Awaiting AE Assignment",
            "Awaiting Final Decision",
        ]

    async def fetch_all_manuscripts(self) -> list[Manuscript]:
        """Fetch all manuscripts from all categories."""
        categories = await self.get_default_categories()
        return await self.fetch_manuscripts(categories)

    def _extract_mf_specific_metadata(self, manuscript: Manuscript):
        """Extract MF-specific metadata fields."""
        # MF-specific extraction logic can be added here
        # This is where journal-specific customizations go
        pass
