#!/usr/bin/env python3
"""
Test SICON directly by going to the authenticated page we know works
"""

import asyncio
import logging
import os
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sicon_direct():
    """Test SICON by using the direct authenticated URL"""
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        # Go directly to login
        logger.info("🔐 Going to SICON login...")
        await page.goto("https://sicon.siam.org/cgi-bin/main.plex", timeout=30000)
        
        # Handle CloudFlare
        await asyncio.sleep(10)
        content = await page.content()
        if "cloudflare" in content.lower():
            logger.info("🛡️ CloudFlare detected - waiting...")
            await asyncio.sleep(60)
        
        # Handle privacy modal
        try:
            continue_btn = page.locator("input[value='Continue']").first
            if await continue_btn.is_visible():
                await continue_btn.click()
                await asyncio.sleep(3)
                logger.info("✅ Clicked Continue on privacy modal")
        except:
            pass
        
        # Click ORCID login
        logger.info("🔗 Looking for ORCID login...")
        orcid_link = page.locator("a[href*='orcid']").first
        if await orcid_link.is_visible():
            await orcid_link.click()
            await asyncio.sleep(5)
            logger.info("✅ Clicked ORCID login")
        
        # Enter credentials
        logger.info("🔑 Entering ORCID credentials...")
        await asyncio.sleep(5)
        
        # Accept cookies
        try:
            accept_btn = page.locator("button:has-text('Accept All Cookies')").first
            if await accept_btn.is_visible():
                await accept_btn.click()
                await asyncio.sleep(3)
        except:
            pass
        
        # Sign in to ORCID
        try:
            signin_btn = page.get_by_role("button", name="Sign in to ORCID")
            if await signin_btn.is_visible():
                await signin_btn.click()
                await asyncio.sleep(5)
        except:
            pass
        
        # Fill credentials
        await page.fill("input[placeholder*='Email or']", "dylan.possamai@polytechnique.org")
        await page.fill("input[placeholder*='password']", "Hioupy0042%")
        
        # Submit
        submit_btn = page.locator("button:has-text('Sign in to ORCID')").last
        await submit_btn.click()
        
        logger.info("🔑 Submitted ORCID credentials")
        
        # Wait for redirect and handle post-auth modals
        await asyncio.sleep(15)
        
        # Handle post-auth privacy modal
        try:
            continue_btn = page.locator("input[value='Continue']").first
            if await continue_btn.is_visible():
                await continue_btn.click()
                await asyncio.sleep(5)
                logger.info("✅ Clicked Continue on post-auth modal")
        except:
            pass
        
        # Now look for manuscripts
        logger.info("🔍 Looking for manuscript links...")
        
        # Get current URL and content
        current_url = page.url
        logger.info(f"📍 Current URL: {current_url}")
        
        # Take screenshot
        await page.screenshot(path="sicon_after_auth.png")
        logger.info("📸 Screenshot saved")
        
        # Look for "Under Review" link
        under_review_links = await page.locator("a:has-text('Under Review')").all()
        logger.info(f"Found {len(under_review_links)} 'Under Review' links")
        
        if under_review_links:
            await under_review_links[0].click()
            await asyncio.sleep(5)
            logger.info("✅ Clicked 'Under Review' link")
            
            # Take another screenshot
            await page.screenshot(path="sicon_under_review.png")
            
            # Look for manuscript table
            table = page.locator("table[border='1']").first
            if await table.is_visible():
                logger.info("✅ Found manuscript table")
                
                rows = await table.locator("tr").all()
                logger.info(f"Table has {len(rows)} rows")
                
                for i, row in enumerate(rows):
                    try:
                        cells = await row.locator("td").all()
                        if len(cells) >= 2:
                            cell1_text = await cells[0].inner_text()
                            cell2_text = await cells[1].inner_text()
                            logger.info(f"Row {i}: {cell1_text} | {cell2_text}")
                    except:
                        pass
            else:
                logger.warning("❌ No manuscript table found")
        
        # Wait for manual inspection
        logger.info("⏳ Check browser and press Enter...")
        input()
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            await browser.close()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_sicon_direct())