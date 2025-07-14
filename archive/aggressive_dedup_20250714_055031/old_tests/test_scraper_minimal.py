#!/usr/bin/env python3
"""
Minimal test to identify the scraper authentication issue
"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from playwright.async_api import async_playwright

async def test_minimal_sifin():
    """Test minimal SIFIN authentication"""
    print("Starting minimal SIFIN test...")
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)  # Use Firefox headless
        page = await browser.new_page()
        
        try:
            print("Navigating to SIFIN...")
            await page.goto("https://sifin.siam.org")
            await page.wait_for_timeout(5000)  # Wait for page to load
            
            # Check if we can find the ORCID login
            print("Looking for ORCID login...")
            orcid_link = await page.query_selector('img[alt*="ORCID"]')
            if orcid_link:
                print("✅ Found ORCID login button")
            else:
                print("❌ ORCID login button not found")
                
            # Take screenshot
            await page.screenshot(path="sifin_test.png")
            print("Screenshot saved as sifin_test.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_minimal_sifin())