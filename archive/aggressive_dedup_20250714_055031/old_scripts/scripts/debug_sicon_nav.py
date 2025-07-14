#!/usr/bin/env python3
"""Debug SICON navigation after authentication"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.scrapers.siam_scraper import SIAMScraper
from playwright.async_api import async_playwright

async def debug_sicon_nav():
    print("🔍 DEBUGGING SICON NAVIGATION")
    print("=" * 50)
    
    os.environ['ORCID_EMAIL'] = "dylan.possamai@polytechnique.org"
    os.environ['ORCID_PASSWORD'] = "Hioupy0042%"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        # Create SICON scraper
        scraper = SIAMScraper('SICON')
        context = await scraper.setup_browser_context(browser)
        page = await context.new_page()
        
        try:
            # Authenticate
            print("🔐 Authenticating...")
            auth_success = await scraper.authenticate(page)
            
            if auth_success:
                print("✅ Authentication successful!")
                await page.screenshot(path="sicon_after_auth.png")
                
                # Check current URL
                print(f"\n📍 Current URL: {page.url}")
                
                # Look for manuscript links
                print("\n🔍 Looking for manuscript navigation links...")
                
                # Check for "All Pending" link
                all_pending = await page.locator("a:has-text('All Pending')").count()
                print(f"   'All Pending' links: {all_pending}")
                
                # Check for "Under Review" links
                under_review = await page.locator("a:has-text('Under Review')").count()
                print(f"   'Under Review' links: {under_review}")
                
                # Check for folder links
                folder_links = await page.locator("a[href*='folder_id']").count()
                print(f"   Folder links: {folder_links}")
                
                # Get all links on page
                print("\n📋 All visible links:")
                links = await page.locator("a").all()
                for i, link in enumerate(links[:20]):  # First 20 links
                    try:
                        text = await link.text_content()
                        href = await link.get_attribute("href")
                        if text and text.strip():
                            print(f"   {i+1}. '{text.strip()[:50]}' -> {href}")
                    except:
                        pass
                
                # Check page content
                content = await page.content()
                if "manuscript" in content.lower():
                    print("\n✅ Page contains 'manuscript' text")
                if "folder" in content.lower():
                    print("✅ Page contains 'folder' text")
                if "review" in content.lower():
                    print("✅ Page contains 'review' text")
                
                print("\n⏸️ Browser will stay open for 15 seconds...")
                await page.wait_for_timeout(15000)
                
            else:
                print("❌ Authentication failed")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_sicon_nav())