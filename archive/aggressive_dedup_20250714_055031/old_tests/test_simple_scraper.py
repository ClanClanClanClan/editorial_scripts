#!/usr/bin/env python3
"""
Simple test to isolate the scraper issue
"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_sifin_scraper():
    """Test SIFIN scraper in isolation"""
    try:
        # Set credentials
        os.environ['ORCID_EMAIL'] = 'dylan.possamai@polytechnique.org'
        os.environ['ORCID_PASSWORD'] = 'Hioupy0042%'
        
        from src.infrastructure.scrapers.siam_scraper import SIAMScraper
        
        print("Creating SIFIN scraper...")
        scraper = SIAMScraper('SIFIN')
        
        print("Creating browser...")
        browser = await scraper.create_browser()
        context = await scraper.setup_browser_context(browser)
        page = await context.new_page()
        
        print("Authenticating...")
        auth_result = await scraper.authenticate(page)
        print(f"Authentication result: {auth_result}")
        
        if auth_result:
            print("Extracting manuscripts...")
            manuscripts = await scraper.extract_manuscripts(page)
            print(f"Found {len(manuscripts)} manuscripts")
            
            for ms in manuscripts[:1]:  # Just process first one
                print(f"\nManuscript: {ms.id} - {ms.title}")
                print(f"Status: {ms.status}")
                print(f"Referee count: {len(ms.referees)}")
        
        await context.close()
        await browser.close()
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sifin_scraper())