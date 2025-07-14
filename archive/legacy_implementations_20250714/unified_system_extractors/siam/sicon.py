"""
SICON (SIAM Journal on Control and Optimization) Extractor
Real implementation with actual data extraction
"""

import asyncio
import logging
from .base import SIAMBaseExtractor

logger = logging.getLogger(__name__)


class SICONExtractor(SIAMBaseExtractor):
    """SICON extractor with ORCID authentication and real data extraction"""
    
    # Journal-specific settings
    journal_name = "SICON"
    base_url = "https://sicon.siam.org"


# Example usage
if __name__ == "__main__":
    async def test_sicon():
        extractor = SICONExtractor()
        results = await extractor.extract(
            username="your_username",
            password="your_password",
            headless=False
        )
        
        print(f"\nExtracted {results['total_manuscripts']} manuscripts")
        print(f"Total referees: {results['statistics']['total_referees']}")
        print(f"PDFs found: {results['statistics']['pdfs_found']}")
    
    asyncio.run(test_sicon())