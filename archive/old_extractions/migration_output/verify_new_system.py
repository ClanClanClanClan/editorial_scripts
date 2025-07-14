#!/usr/bin/env python3
"""
New System Verification
Verify all components of new system are working
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import src
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

async def verify_new_system():
    print("Verifying new system components...")
    
    try:
        # Test configuration
        from src.infrastructure.config import get_settings
        settings = get_settings()
        print("✓ Configuration loaded")
        
        # Test database
        from src.infrastructure.database.engine import get_session
        from sqlalchemy import text
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
        print("✓ Database connection working")
        
        # Test browser pool
        from src.infrastructure.browser_pool import PlaywrightBrowserPool
        browser_pool = PlaywrightBrowserPool(size=1)
        await browser_pool.start()
        await browser_pool.stop()
        print("✓ Browser pool working")
        
        # Test scrapers
        from src.infrastructure.scrapers.sicon_scraper import SICONScraper
        from src.infrastructure.scrapers.sifin_scraper import SIFINScraper
        
        browser_pool = PlaywrightBrowserPool(size=1)
        await browser_pool.start()
        
        sicon = SICONScraper(browser_pool)
        sifin = SIFINScraper(browser_pool)
        
        await browser_pool.stop()
        print("✓ Scrapers instantiated successfully")
        
        print("\n🎉 New system verification complete!")
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_new_system())
    sys.exit(0 if success else 1)
