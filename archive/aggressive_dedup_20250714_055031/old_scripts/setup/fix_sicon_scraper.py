#!/usr/bin/env python3
"""Fix SICON scraper by simplifying authentication flow"""

import asyncio
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.scrapers.siam_scraper import SIAMScraper
from src.infrastructure.scrapers.base_scraper import BaseScraper
from playwright.async_api import Page
import logging

# Create a simplified SICON scraper that bypasses problematic stealth features
class SimplifiedSICONScraper(SIAMScraper):
    """SICON scraper with simplified authentication"""
    
    async def authenticate(self, page: Page) -> bool:
        """Simplified authentication without problematic stealth features"""
        try:
            self.logger.info(f"🔐 Starting simplified ORCID authentication for {self.journal_code}")
            
            # Navigate to login page
            login_url = f"{self.config.base_url}/cgi-bin/main.plex"
            await page.goto(login_url, timeout=60000)  # Longer timeout for Cloudflare
            
            # Wait for page to load
            await page.wait_for_timeout(10000)  # Give Cloudflare time
            
            # Check for Cloudflare and wait it out
            content = await page.content()
            if "cloudflare" in content.lower():
                self.logger.info("🛡️ Cloudflare detected - waiting...")
                # Just wait - don't use wait_for_function in headless
                await page.wait_for_timeout(15000)
            
            # Handle modals with JavaScript
            await page.evaluate("""
                // Remove all blocking elements
                const blockingElements = [
                    document.getElementById('cookie-policy-layer-bg'),
                    document.getElementById('cookie-policy-layer'),
                    ...document.querySelectorAll('[class*="modal"]'),
                    ...document.querySelectorAll('[class*="overlay"]')
                ];
                blockingElements.forEach(el => {
                    if (el && el.style) el.style.display = 'none';
                });
            """)
            await page.wait_for_timeout(2000)
            
            # Try to click Continue button if visible
            try:
                continue_btn = page.locator("input[value='Continue']").first
                if await continue_btn.is_visible():
                    await continue_btn.click()
                    await page.wait_for_timeout(2000)
                    self.logger.info("✅ Clicked Continue button")
            except:
                pass
            
            # Click ORCID login
            try:
                orcid_img = page.locator("img[src*='orcid']").first
                if await orcid_img.is_visible():
                    parent_link = orcid_img.locator("..")
                    await parent_link.click()
                    await page.wait_for_timeout(5000)
                    self.logger.info("🔗 Clicked ORCID login")
            except Exception as e:
                self.logger.error(f"Could not click ORCID: {e}")
                return False
            
            # Handle ORCID page
            if "orcid.org" in page.url:
                # Get credentials
                orcid_email = os.environ.get('ORCID_EMAIL')
                orcid_password = os.environ.get('ORCID_PASSWORD')
                
                if not orcid_email or not orcid_password:
                    raise Exception("ORCID credentials not found in environment")
                
                # Accept cookies
                try:
                    accept_btn = page.locator("button:has-text('Accept All Cookies')").first
                    if await accept_btn.is_visible():
                        await accept_btn.click()
                        await page.wait_for_timeout(3000)
                except:
                    pass
                
                # Click Sign in to ORCID
                try:
                    signin_btn = page.get_by_role("button", name="Sign in to ORCID")
                    if await signin_btn.is_visible():
                        await signin_btn.click()
                        await page.wait_for_timeout(5000)
                except:
                    pass
                
                # Fill credentials
                await page.fill("input[placeholder*='Email or']", orcid_email)
                await page.fill("input[placeholder*='password']", orcid_password)
                
                # Submit
                submit_btn = page.locator("button:has-text('Sign in to ORCID')").last
                await submit_btn.click()
                
                self.logger.info("🔑 Submitted ORCID credentials")
                await page.wait_for_timeout(10000)
            
            # Verify authentication
            if "sicon.siam.org" in page.url:
                self.authenticated = True
                self.logger.info("✅ SICON authentication successful")
                return True
            else:
                self.logger.error(f"❌ Not on SICON after auth: {page.url}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Simplified auth failed: {e}")
            return False

async def test_fixed_sicon():
    print("🧪 TESTING FIXED SICON SCRAPER")
    print("=" * 60)
    
    os.environ['ORCID_EMAIL'] = "dylan.possamai@polytechnique.org"
    os.environ['ORCID_PASSWORD'] = "Hioupy0042%"
    
    # Enable debug logging
    logging.basicConfig(level=logging.INFO)
    
    try:
        # Use simplified scraper
        scraper = SimplifiedSICONScraper('SICON')
        print("✅ Created simplified SICON scraper")
        
        # Run extraction
        result = await scraper.run_extraction()
        
        if result.success:
            print(f"\n🎉 SUCCESS! Found {result.total_count} manuscripts")
            
            for i, ms in enumerate(result.manuscripts, 1):
                print(f"\n📄 Manuscript {i}: {ms.id}")
                print(f"   Title: {ms.title[:60]}...")
                
                # Check documents
                docs = ms.metadata.get('documents', {})
                if docs.get('manuscript_pdf'):
                    print(f"   📎 PDF: {docs['manuscript_pdf']}")
                if docs.get('cover_letter'):
                    print(f"   📎 Cover Letter: ✓")
                if docs.get('referee_reports'):
                    print(f"   📎 Reports: {len(docs['referee_reports'])}")
                    
        else:
            print(f"\n❌ Extraction failed: {result.error_message}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fixed_sicon())