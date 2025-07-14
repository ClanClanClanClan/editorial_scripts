#!/usr/bin/env python3
"""
End-to-End Integration Test
Tests the complete architecture after migration
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.infrastructure.config import get_settings
from src.infrastructure.database.engine import get_session, engine, close_db, init_db
from src.infrastructure.browser_pool import PlaywrightBrowserPool
from src.infrastructure.scrapers.sicon_scraper import SICONScraper
from src.infrastructure.scrapers.sifin_scraper import SIFINScraper
from src.infrastructure.services.gmail_service import GmailService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_configuration():
    """Test configuration loading"""
    logger.info("Testing configuration...")
    
    try:
        settings = get_settings()
        
        # Check essential settings
        assert settings.db_host, "DB host not configured"
        assert settings.db_name, "DB name not configured"
        
        logger.info("✓ Configuration loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Configuration test failed: {e}")
        return False


async def test_database_connection():
    """Test database connectivity"""
    logger.info("Testing database connection...")
    
    try:
        # Test basic query
        from sqlalchemy import text
        async with get_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            assert row[0] == 1, "Database query failed"
        
        logger.info("✓ Database connection successful")
        return True
        
    except Exception as e:
        logger.error(f"✗ Database test failed: {e}")
        return False


async def test_browser_pool():
    """Test browser pool functionality"""
    logger.info("Testing browser pool...")
    
    try:
        browser_pool = PlaywrightBrowserPool(size=2)
        await browser_pool.start()
        
        # Test getting a browser
        async with browser_pool.get_browser() as browser:
            page = await browser.new_page()
            await page.goto("https://www.google.com")
            title = await page.title()
            assert "Google" in title, "Browser navigation failed"
            await page.close()
        
        await browser_pool.stop()
        logger.info("✓ Browser pool working correctly")
        return True
        
    except Exception as e:
        logger.error(f"✗ Browser pool test failed: {e}")
        return False


async def test_scrapers_instantiation():
    """Test scraper instantiation and basic setup"""
    logger.info("Testing scraper instantiation...")
    
    try:
        browser_pool = PlaywrightBrowserPool(size=1)
        await browser_pool.start()
        
        # Test SICON scraper
        sicon_scraper = SICONScraper(browser_pool)
        assert sicon_scraper.journal_code == "SICON"
        assert sicon_scraper.folder_id == "1800"
        logger.info("✓ SICON scraper instantiated")
        
        # Test SIFIN scraper
        sifin_scraper = SIFINScraper(browser_pool)
        assert sifin_scraper.journal_code == "SIFIN"
        assert sifin_scraper.folder_id == "1802"
        logger.info("✓ SIFIN scraper instantiated")
        
        await browser_pool.stop()
        logger.info("✓ All scrapers instantiated successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Scraper instantiation test failed: {e}")
        return False


async def test_gmail_service():
    """Test Gmail service instantiation"""
    logger.info("Testing Gmail service...")
    
    try:
        gmail_service = GmailService()
        
        # Check that the service is properly configured
        assert hasattr(gmail_service, 'settings')
        assert hasattr(gmail_service, 'SCOPES')
        
        logger.info("✓ Gmail service instantiated successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ Gmail service test failed: {e}")
        return False


async def test_database_operations():
    """Test basic database operations"""
    logger.info("Testing database operations...")
    
    try:
        from src.core.domain.models import Manuscript, ManuscriptStatus
        from src.infrastructure.database.models import ManuscriptModel
        
        # Create test manuscript
        test_manuscript = Manuscript(
            journal_code="TEST",
            external_id="TEST-001",
            title="Integration Test Manuscript",
            authors=[],
            submission_date=datetime.now(),
            status=ManuscriptStatus.SUBMITTED,
            custom_metadata={"test": True}
        )
        
        async with get_session() as session:
            # Convert to database model
            db_manuscript = ManuscriptModel(
                journal_code=test_manuscript.journal_code,
                external_id=test_manuscript.external_id,
                title=test_manuscript.title,
                submission_date=test_manuscript.submission_date,
                status=test_manuscript.status,
                custom_metadata=test_manuscript.custom_metadata
            )
            
            # Save to database
            session.add(db_manuscript)
            await session.commit()
            
            # Query back
            from sqlalchemy import text
            result = await session.execute(
                text("SELECT * FROM manuscripts WHERE external_id = 'TEST-001'")
            )
            row = result.fetchone()
            assert row is not None, "Failed to save/retrieve manuscript"
            
            # Cleanup
            await session.execute(
                text("DELETE FROM manuscripts WHERE external_id = 'TEST-001'")
            )
            await session.commit()
        
        logger.info("✓ Database operations working correctly")
        return True
        
    except Exception as e:
        logger.error(f"✗ Database operations test failed: {e}")
        return False


async def test_complete_architecture():
    """Test the complete architecture integration"""
    logger.info("Testing complete architecture integration...")
    
    try:
        # Initialize all components
        settings = get_settings()
        browser_pool = PlaywrightBrowserPool(size=1)
        
        await browser_pool.start()
        
        # Create scrapers
        sicon_scraper = SICONScraper(browser_pool)
        sifin_scraper = SIFINScraper(browser_pool)
        gmail_service = GmailService()
        
        # Test that all components can work together
        logger.info("✓ All components initialized and connected")
        
        # Cleanup
        await browser_pool.stop()
        
        logger.info("✓ Complete architecture test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Complete architecture test failed: {e}")
        return False


async def run_all_tests():
    """Run all integration tests"""
    logger.info("Starting Integration Tests")
    logger.info("=" * 50)
    
    tests = [
        ("Configuration", test_configuration()),
        ("Database Connection", test_database_connection()),
        ("Browser Pool", test_browser_pool()),
        ("Scrapers Instantiation", test_scrapers_instantiation()),
        ("Gmail Service", test_gmail_service()),
        ("Database Operations", test_database_operations()),
        ("Complete Architecture", test_complete_architecture())
    ]
    
    results = []
    for test_name, test_coro in tests:
        logger.info(f"\nRunning {test_name} test...")
        try:
            result = await test_coro
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\nIntegration Test Results")
    logger.info("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    total = len(results)
    logger.info(f"\nSummary: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - Migration is successful!")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed - Migration needs fixes")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)