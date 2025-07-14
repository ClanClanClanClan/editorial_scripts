#!/usr/bin/env python3
"""
Test SICON by going directly to folder 1800 after authentication
"""

import asyncio
import logging
import os
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sicon_folder():
    """Test SICON folder 1800 directly"""
    try:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = await context.new_page()
        
        # Authenticate first (same as before)
        logger.info("🔐 Authenticating with SICON...")
        await page.goto("https://sicon.siam.org/cgi-bin/main.plex", timeout=30000)
        
        await asyncio.sleep(10)
        
        # Handle privacy modal
        try:
            continue_btn = page.locator("input[value='Continue']").first
            if await continue_btn.is_visible():
                await continue_btn.click()
                await asyncio.sleep(3)
        except:
            pass
        
        # Click ORCID
        orcid_link = page.locator("a[href*='orcid']").first
        if await orcid_link.is_visible():
            await orcid_link.click()
            await asyncio.sleep(5)
        
        # Credentials
        await asyncio.sleep(5)
        await page.fill("input[placeholder*='Email or']", "dylan.possamai@polytechnique.org")
        await page.fill("input[placeholder*='password']", "Hioupy0042%")
        
        submit_btn = page.locator("button:has-text('Sign in to ORCID')").last
        await submit_btn.click()
        
        # Wait for redirect
        await asyncio.sleep(15)
        
        # Handle post-auth modal
        try:
            continue_btn = page.locator("input[value='Continue']").first
            if await continue_btn.is_visible():
                await continue_btn.click()
                await asyncio.sleep(5)
        except:
            pass
        
        logger.info("✅ Authentication complete")
        
        # Now go directly to folder 1800
        folder_url = "https://sicon.siam.org/cgi-bin/main.plex?el=main&s=folder&fld_id=1800"
        logger.info(f"🔗 Going to folder URL: {folder_url}")
        
        await page.goto(folder_url, timeout=30000)
        await asyncio.sleep(5)
        
        # Get content
        current_url = page.url
        logger.info(f"📍 Current URL: {current_url}")
        
        content = await page.content()
        
        # Save for analysis
        with open("sicon_folder_1800.html", "w") as f:
            f.write(content)
        logger.info("💾 Content saved to sicon_folder_1800.html")
        
        # Take screenshot
        await page.screenshot(path="sicon_folder_1800.png")
        logger.info("📸 Screenshot saved")
        
        # Parse with BeautifulSoup like the working scraper
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for table with border='1' (SICON style)
        table = soup.find('table', {'border': '1'})
        if table:
            logger.info("✅ Found SICON table with border='1'")
            rows = table.find_all('tr')[1:]  # Skip header
            logger.info(f"Found {len(rows)} data rows")
            
            for i, row in enumerate(rows):
                cells = row.find_all('td')
                if len(cells) >= 5:
                    manuscript_id = cells[0].get_text(strip=True)
                    title = cells[1].get_text(strip=True)
                    ce = cells[2].get_text(strip=True) 
                    ae = cells[3].get_text(strip=True)
                    date = cells[4].get_text(strip=True)
                    
                    logger.info(f"Manuscript {i+1}:")
                    logger.info(f"  ID: {manuscript_id}")
                    logger.info(f"  Title: {title[:50]}...")
                    logger.info(f"  CE: {ce}")
                    logger.info(f"  AE: {ae}")
                    logger.info(f"  Date: {date}")
                else:
                    logger.info(f"Row {i+1} has {len(cells)} cells: {[cell.get_text(strip=True) for cell in cells]}")
        else:
            logger.warning("❌ No table with border='1' found")
            
            # Look for any tables
            all_tables = soup.find_all('table')
            logger.info(f"Found {len(all_tables)} total tables")
            
            for i, table in enumerate(all_tables):
                table_text = table.get_text(strip=True)
                if len(table_text) > 50:
                    logger.info(f"Table {i+1} preview: {table_text[:200]}...")
        
        # Wait for inspection
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
    asyncio.run(test_sicon_folder())