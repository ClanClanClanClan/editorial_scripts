#!/usr/bin/env python3
"""
Debug SIAM Login Pages
Check what selectors are actually available on SICON/SIFIN login pages
"""

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_siam_login(journal_url: str, journal_name: str):
    """Debug SIAM login page to see available selectors"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        try:
            logger.info(f"🔍 Debugging {journal_name} login page...")
            
            # Navigate to login page
            login_url = f"{journal_url}/cgi-bin/main.plex"
            await page.goto(login_url, timeout=60000)
            
            # Wait for page load
            await asyncio.sleep(10)
            
            # Check for CloudFlare
            content = await page.content()
            if "cloudflare" in content.lower():
                logger.info("🛡️ CloudFlare detected, waiting...")
                await asyncio.sleep(60)
            
            # Look for ORCID elements
            logger.info("🔍 Looking for ORCID login elements...")
            
            # Method 1: ORCID image
            orcid_imgs = await page.locator("img[src*='orcid']").all()
            logger.info(f"Found {len(orcid_imgs)} ORCID images")
            
            # Method 2: ORCID text links
            orcid_links = await page.locator("a:has-text('ORCID')").all()
            logger.info(f"Found {len(orcid_links)} ORCID text links")
            
            # Method 3: All images (to see what's available)
            all_imgs = await page.locator("img").all()
            logger.info(f"Found {len(all_imgs)} total images")
            
            for i, img in enumerate(all_imgs[:10]):  # First 10 images
                src = await img.get_attribute("src")
                alt = await img.get_attribute("alt")
                logger.info(f"  Image {i}: src={src}, alt={alt}")
            
            # Method 4: All links (to see login options)
            all_links = await page.locator("a").all()
            login_links = []
            
            for link in all_links[:20]:  # First 20 links
                text = await link.inner_text()
                href = await link.get_attribute("href")
                if any(keyword in text.lower() for keyword in ['login', 'sign in', 'orcid', 'authenticate']):
                    login_links.append((text.strip(), href))
            
            logger.info(f"Found {len(login_links)} potential login links:")
            for text, href in login_links:
                logger.info(f"  '{text}' -> {href}")
            
            # Method 5: Check for forms
            forms = await page.locator("form").all()
            logger.info(f"Found {len(forms)} forms")
            
            # Save screenshot for manual inspection
            screenshot_path = f"debug_{journal_name.lower()}_login.png"
            await page.screenshot(path=screenshot_path)
            logger.info(f"📸 Screenshot saved: {screenshot_path}")
            
            # Get page source for analysis
            html_path = f"debug_{journal_name.lower()}_login.html"
            with open(html_path, 'w') as f:
                f.write(content)
            logger.info(f"💾 HTML saved: {html_path}")
            
            # Wait for manual inspection
            logger.info("⏳ Page loaded - check browser window for ORCID login")
            logger.info("Press Enter when ready to continue...")
            input()
            
        except Exception as e:
            logger.error(f"❌ Error debugging {journal_name}: {e}")
        finally:
            await browser.close()

async def main():
    """Debug both SICON and SIFIN login pages"""
    journals = [
        ("https://sicon.siam.org", "SICON"),
        ("https://sifin.siam.org", "SIFIN")
    ]
    
    for url, name in journals:
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 DEBUGGING {name}")
        logger.info(f"{'='*60}")
        
        await debug_siam_login(url, name)
        
        if name == "SICON":
            logger.info("\n⏳ Moving to SIFIN in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Debug interrupted")