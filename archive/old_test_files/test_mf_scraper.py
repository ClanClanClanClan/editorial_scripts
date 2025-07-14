"""
Test script for MF scraper with new architecture
"""

import asyncio
import logging
from src.infrastructure.scrapers.mf_scraper import MFScraper
from src.infrastructure.browser_pool import BrowserPool
from src.infrastructure.config import get_settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mf_scraper():
    """Test the MF scraper"""
    settings = get_settings()
    
    # Initialize browser pool
    browser_pool = BrowserPool(
        pool_size=1,
        headless=False,  # Set to True for production
        timeout=30000
    )
    
    try:
        # Initialize browser pool
        await browser_pool.start()
        
        # Create MF scraper
        mf_scraper = MFScraper(browser_pool)
        
        # Extract manuscripts
        logger.info("Starting MF manuscript extraction...")
        manuscripts = await mf_scraper.extract_manuscripts()
        
        logger.info(f"Successfully extracted {len(manuscripts)} manuscripts")
        
        # Display results
        for manuscript in manuscripts:
            logger.info(f"Manuscript: {manuscript.external_id} - {manuscript.title}")
            logger.info(f"  Status: {manuscript.status}")
            logger.info(f"  Reviews: {len(manuscript.reviews)}")
            
            for review in manuscript.reviews:
                logger.info(f"    Review: {review.status} - Due: {review.due_date}")
    
    except Exception as e:
        logger.error(f"Error testing MF scraper: {e}")
        raise
    
    finally:
        # Clean up browser pool
        await browser_pool.stop()

if __name__ == "__main__":
    asyncio.run(test_mf_scraper())