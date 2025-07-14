#!/usr/bin/env python3
"""
Test the updated SIAM scraper with fixed Cloudflare handling
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.scrapers.siam_scraper import SIAMScraper
from playwright.async_api import async_playwright

async def test_siam_scrapers():
    """Test both SICON and SIFIN scrapers"""
    print("🧪 TESTING UPDATED SIAM SCRAPERS")
    print("=" * 60)
    
    # Test SICON
    print("\n🔍 Testing SICON...")
    try:
        sicon_scraper = SIAMScraper('SICON')
        
        # Create browser manually for testing
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await sicon_scraper.setup_browser_context(browser)
            page = await context.new_page()
            
            # Test authentication only
            print("🔐 Testing SICON authentication...")
            auth_result = await sicon_scraper.authenticate(page)
            
            if auth_result:
                print("✅ SICON authentication successful!")
                await page.screenshot(path="sicon_authenticated.png")
            else:
                print("❌ SICON authentication failed")
                await page.screenshot(path="sicon_failed.png")
            
            await context.close()
            await browser.close()
            
    except Exception as e:
        print(f"❌ SICON test error: {e}")
    
    # Test SIFIN  
    print("\n🔍 Testing SIFIN...")
    try:
        sifin_scraper = SIAMScraper('SIFIN')
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await sifin_scraper.setup_browser_context(browser)
            page = await context.new_page()
            
            # Test authentication only
            print("🔐 Testing SIFIN authentication...")
            auth_result = await sifin_scraper.authenticate(page)
            
            if auth_result:
                print("✅ SIFIN authentication successful!")
                await page.screenshot(path="sifin_authenticated.png")
            else:
                print("❌ SIFIN authentication failed")
                await page.screenshot(path="sifin_failed.png")
            
            await context.close()
            await browser.close()
            
    except Exception as e:
        print(f"❌ SIFIN test error: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Test Results:")
    print("📸 Check screenshots:")
    print("   - sicon_authenticated.png (if successful)")
    print("   - sifin_authenticated.png (if successful)")
    print("   - *_failed.png (if authentication failed)")

if __name__ == "__main__":
    asyncio.run(test_siam_scrapers())