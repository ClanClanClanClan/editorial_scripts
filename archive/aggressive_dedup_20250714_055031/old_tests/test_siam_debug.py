#!/usr/bin/env python3
"""
Debug SIAM scraper with detailed logging
"""

import asyncio
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_siam_with_debug():
    """Test SIAM scraper with debugging"""
    # Set credentials
    os.environ['ORCID_EMAIL'] = 'dylan.possamai@polytechnique.org'
    os.environ['ORCID_PASSWORD'] = 'Hioupy0042%'
    
    from src.infrastructure.scrapers.siam_scraper import SIAMScraper
    
    print("Creating SIFIN scraper with debug logging...")
    scraper = SIAMScraper('SIFIN')
    scraper.setup_logging('DEBUG')
    
    try:
        print("\nCreating browser...")
        browser = await scraper.create_browser()
        context = await scraper.setup_browser_context(browser)
        page = await context.new_page()
        
        # Enable console logs
        page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"Browser error: {exc}"))
        
        print("\nStarting authentication...")
        auth_result = await scraper.authenticate(page)
        print(f"\nAuthentication result: {auth_result}")
        
        if not auth_result:
            # Take screenshot of failed auth
            await page.screenshot(path="sifin_auth_failed.png")
            print("Screenshot saved: sifin_auth_failed.png")
        
        await context.close()
        await browser.close()
        
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_siam_with_debug())