"""Mathematics of Operations Research (MOR) journal adapter - ScholarOne Selenium implementation."""

from src.ecc.adapters.journals.base import JournalConfig
from src.ecc.adapters.journals.scholarone_selenium import ScholarOneSeleniumAdapter
from src.ecc.core.domain.models import Manuscript


class MORAdapter(ScholarOneSeleniumAdapter):
    """MOR journal adapter (uses Selenium to bypass anti-bot)."""

    def __init__(self, headless: bool = True):
        config = JournalConfig(
            journal_id="MOR",
            name="Mathematics of Operations Research",
            url="https://mc.manuscriptcentral.com/mor",
            platform="ScholarOne",
            headless=headless,
        )
        super().__init__(config)

    def _get_manuscript_pattern(self) -> str:
        return r"MOR-\d{4}-\d{4}"

    async def get_default_categories(self) -> list[str]:
        return [
            "Awaiting Reviewer Reports",
            "Awaiting AE Recommendation",
            "Under Review",
            "Awaiting AE Assignment",
            "Awaiting Final Decision",
        ]

    async def fetch_all_manuscripts(self) -> list[Manuscript]:
        categories = await self.get_default_categories()
        return await self.fetch_manuscripts(categories)
