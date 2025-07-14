#!/usr/bin/env python3
"""
Debug SIFIN content after authentication to see what's actually on the page
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

async def debug_sifin_after_auth():
    """Debug SIFIN page content after authentication"""
    try:
        # Set service account token
        os.environ['OP_SERVICE_ACCOUNT_TOKEN'] = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjNnZkpDeW1iMGJBRHRYWmlGWGVuWUJyX1Y5T3R6UHVSLUFwNVcyZVgwRW8iLCJ0eXAiOiJKV1QifQ.eyJhZXMiOiJNRFVYUUxBV0I3WktFWDNBSktVQ0RFTEZIK1pSSktGUVJOSzVBVkxKNVdZSkNOR0FDUlJRPT09PSIsImF1ZCI6ImJFN3hZVGNJUXlzWXZpanEzN2tQM1kiLCJjbGQiOjAsImV4cCI6MTc2ODI1ODM0MiwiaWF0IjoxNzM2NjM1MzQyLCJpc3MiOiJzZXJ2aWNlYWNjb3VudC50b2tlbi4xUGFzc3dvcmQuZXUiLCJqdGkiOiJ6cGl0M2xqaTNidGVmZDV6NzN1ZzNxY3l1NCIsInN0YSI6MTA0LCJ1aWQiOiJSSjdQNklPWEVSQU9URlRXTDNDUEtHR1lUUSIsInZlciI6Mn0.oKgBMaNSdQ6zJ1JG7YqcPQ4bVE8KK6F-BfHVzZtYaMQhQD5ELqrqEgbdISDhEE-rqkR9rCo8oFfJF_CJo4TG3D0wAaXM0v5X6zznL5EfnMJCVQqOa-Z02KPHbW4e_GZqPP2jKMPi2KnB9zKgBGgRWjGPkfKyOJv1K0Z7bNqV6wkGDe0W2xXWJhWEKwxOu6r6rjQ8G4VZfzYWdmHeCq4FHbWwW3xnOeqKQZSfCnXEyKCN7N2fIHLV0wGjQWJjgN_1fZ8vU_fVm7XzjmIZaGO_LpCLRt_Bz_W8-9MfVR5l5M1F5TsGQkNnHrY-yz1P2mS5rIiGhBL8xF_E_1QgmGCw"
        
        from unified_system.extractors.siam.sifin import SIFINExtractor
        
        extractor = SIFINExtractor()
        
        # Initialize browser (non-headless for debugging)
        await extractor._init_browser(headless=False)
        
        logger.info("🔐 Authenticating with SIFIN...")
        
        # Authenticate
        if await extractor._authenticate():
            logger.info("✅ Authentication successful!")
            
            # Wait a bit for page to load
            await asyncio.sleep(5)
            
            # Get page content
            content = await extractor.page.content()
            
            # Save content for analysis
            with open("debug_sifin_authenticated.html", "w") as f:
                f.write(content)
            logger.info("💾 Page content saved to debug_sifin_authenticated.html")
            
            # Take screenshot
            await extractor.page.screenshot(path="debug_sifin_authenticated.png")
            logger.info("📸 Screenshot saved to debug_sifin_authenticated.png")
            
            # Look for manuscript elements
            logger.info("🔍 Looking for manuscript elements...")
            
            # Check for task links (SIFIN style)
            task_links = await extractor.page.locator("a.ndt_task_link").all()
            logger.info(f"Found {len(task_links)} task links")
            
            # Check for any links with manuscript IDs
            all_links = await extractor.page.locator("a").all()
            manuscript_links = []
            
            for link in all_links[:50]:  # Check first 50 links
                try:
                    text = await link.inner_text()
                    href = await link.get_attribute("href")
                    if text and ('#' in text or 'manuscript' in text.lower() or 'ms' in text.lower()):
                        manuscript_links.append((text.strip(), href))
                except:
                    pass
            
            logger.info(f"Found {len(manuscript_links)} potential manuscript links:")
            for text, href in manuscript_links[:10]:  # Show first 10
                logger.info(f"  '{text}' -> {href}")
            
            # Check for tables
            tables = await extractor.page.locator("table").all()
            logger.info(f"Found {len(tables)} tables")
            
            # Check for any text containing manuscript numbers
            page_text = await extractor.page.inner_text("body")
            lines_with_numbers = [line.strip() for line in page_text.split('\n') 
                                if line.strip() and any(char.isdigit() for char in line) 
                                and len(line.strip()) < 100][:20]
            
            logger.info("Lines with numbers (potential manuscript IDs):")
            for line in lines_with_numbers:
                logger.info(f"  {line}")
            
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
    asyncio.run(debug_sifin_after_auth())