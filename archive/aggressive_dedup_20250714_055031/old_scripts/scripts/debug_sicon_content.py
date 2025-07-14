#!/usr/bin/env python3
"""
Debug SICON content after authentication to see what's actually on the page
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_sicon_after_auth():
    """Debug SICON page content after authentication"""
    try:
        # Set service account token
        os.environ['OP_SERVICE_ACCOUNT_TOKEN'] = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjNnZkpDeW1iMGJBRHRYWmlGWGVuWUJyX1Y5T3R6UHVSLUFwNVcyZVgwRW8iLCJ0eXAiOiJKV1QifQ.eyJhZXMiOiJNRFVYUUxBV0I3WktFWDNBSktVQ0RFTEZIK1pSSktGUVJOSzVBVkxKNVdZSkNOR0FDUlJRPT09PSIsImF1ZCI6ImJFN3hZVGNJUXlzWXZpanEzN2tQM1kiLCJjbGQiOjAsImV4cCI6MTc2ODI1ODM0MiwiaWF0IjoxNzM2NjM1MzQyLCJpc3MiOiJzZXJ2aWNlYWNjb3VudC50b2tlbi4xUGFzc3dvcmQuZXUiLCJqdGkiOiJ6cGl0M2xqaTNidGVmZDV6NzN1ZzNxY3l1NCIsInN0YSI6MTA0LCJ1aWQiOiJSSjdQNklPWEVSQU9URlRXTDNDUEtHR1lUUSIsInZlciI6Mn0.oKgBMaNSdQ6zJ1JG7YqcPQ4bVE8KK6F-BfHVzZtYaMQhQD5ELqrqEgbdISDhEE-rqkR9rCo8oFfJF_CJo4TG3D0wAaXM0v5X6zznL5EfnMJCVQqOa-Z02KPHbW4e_GZqPP2jKMPi2KnB9zKgBGgRWjGPkfKyOJv1K0Z7bNqV6wkGDe0W2xXWJhWEKwxOu6r6rjQ8G4VZfzYWdmHeCq4FHbWwW3xnOeqKQZSfCnXEyKCN7N2fIHLV0wGjQWJjgN_1fZ8vU_fVm7XzjmIZaGO_LpCLRt_Bz_W8-9MfVR5l5M1F5TsGQkNnHrY-yz1P2mS5rIiGhBL8xF_E_1QgmGCw"
        
        from unified_system.extractors.siam.sicon import SICONExtractor
        
        extractor = SICONExtractor()
        
        # Initialize browser (non-headless for debugging)
        await extractor._init_browser(headless=False)
        
        logger.info("🔐 Authenticating with SICON...")
        
        # Authenticate
        if await extractor._authenticate():
            logger.info("✅ Authentication successful!")
            
            # Wait a bit for page to load
            await asyncio.sleep(5)
            
            # Get current URL
            current_url = extractor.page.url
            logger.info(f"📍 Current URL: {current_url}")
            
            # Get page title
            title = await extractor.page.title()
            logger.info(f"📋 Page title: {title}")
            
            # Get page content
            content = await extractor.page.content()
            
            # Save content for analysis
            with open("debug_sicon_authenticated.html", "w") as f:
                f.write(content)
            logger.info("💾 Page content saved to debug_sicon_authenticated.html")
            
            # Take screenshot
            await extractor.page.screenshot(path="debug_sicon_authenticated.png")
            logger.info("📸 Screenshot saved to debug_sicon_authenticated.png")
            
            # Look for manuscript-related content
            logger.info("🔍 Looking for manuscript content...")
            
            # Method 1: Look for tables
            tables = await extractor.page.locator("table").all()
            logger.info(f"Found {len(tables)} tables")
            
            for i, table in enumerate(tables):
                try:
                    table_text = await table.inner_text()
                    if len(table_text) > 50:  # Only show substantial tables
                        logger.info(f"Table {i+1} content preview: {table_text[:200]}...")
                except:
                    pass
            
            # Method 2: Look for Under Review links
            under_review_links = await extractor.page.locator("a:has-text('Under Review')").all()
            logger.info(f"Found {len(under_review_links)} 'Under Review' links")
            
            # Method 3: Look for any manuscript IDs or numbers
            all_text = await extractor.page.inner_text("body")
            lines = all_text.split('\n')
            manuscript_lines = []
            
            for line in lines:
                line = line.strip()
                if line and any(keyword in line.lower() for keyword in ['manuscript', 'ms', 'under review', 'submission']):
                    manuscript_lines.append(line)
            
            logger.info(f"Found {len(manuscript_lines)} lines mentioning manuscripts:")
            for line in manuscript_lines[:10]:  # Show first 10
                logger.info(f"  {line}")
            
            # Method 4: Look for specific SICON table structure
            sicon_table = await extractor.page.locator("table[border='1']").first
            if await sicon_table.is_visible():
                logger.info("✅ Found SICON table with border='1'")
                table_html = await sicon_table.inner_html()
                logger.info(f"Table HTML preview: {table_html[:500]}...")
                
                # Count rows
                rows = await sicon_table.locator("tr").all()
                logger.info(f"Table has {len(rows)} rows")
                
                for i, row in enumerate(rows[:5]):  # First 5 rows
                    try:
                        row_text = await row.inner_text()
                        logger.info(f"Row {i+1}: {row_text}")
                    except:
                        pass
            else:
                logger.warning("❌ No SICON table found with border='1'")
            
            # Method 5: Try to navigate to manuscripts if not there
            logger.info("🔍 Looking for navigation options...")
            all_links = await extractor.page.locator("a").all()
            nav_links = []
            
            for link in all_links[:30]:  # Check first 30 links
                try:
                    text = await link.inner_text()
                    href = await link.get_attribute("href")
                    if text and any(keyword in text.lower() for keyword in ['manuscript', 'review', 'submission', 'editorial']):
                        nav_links.append((text.strip(), href))
                except:
                    pass
            
            logger.info(f"Found {len(nav_links)} potential navigation links:")
            for text, href in nav_links:
                logger.info(f"  '{text}' -> {href}")
            
            # Wait for manual inspection
            logger.info("⏳ Check browser window and press Enter to continue...")
            input()
            
        else:
            logger.error("❌ Authentication failed")
        
    except Exception as e:
        logger.error(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            await extractor._cleanup()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(debug_sicon_after_auth())