#!/usr/bin/env python3
"""Quick SIAM test - just check if we can reach the page"""

import asyncio
from playwright.async_api import async_playwright

async def quick_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            
            print("🔍 Testing SICON...")
            response = await page.goto("http://sicon.siam.org/cgi-bin/main.plex", timeout=10000)
            print(f"   Status: {response.status if response else 'No response'}")
            print(f"   URL: {page.url}")
            
            # Quick screenshot
            await page.screenshot(path="quick_sicon.png")
            print("   📸 Screenshot: quick_sicon.png")
            
            # Check for modal
            modal = await page.locator(".privacy-modal, #privacy-modal, button:has-text('Continue')").count()
            print(f"   Modal elements: {modal}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await browser.close()

asyncio.run(quick_test())