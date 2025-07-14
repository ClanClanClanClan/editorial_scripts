#!/usr/bin/env python3
"""Test SICON with ultra-simple approach"""

import asyncio
import os
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def simple_sicon_test():
    print("🧪 ULTRA-SIMPLE SICON TEST")
    print("=" * 60)
    
    email = os.environ.get('ORCID_EMAIL', 'dylan.possamai@polytechnique.org')
    password = os.environ.get('ORCID_PASSWORD', 'Hioupy0042%')
    
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Step 1: Navigate to SICON
            print("📍 Step 1: Navigate to SICON...")
            await page.goto("http://sicon.siam.org/cgi-bin/main.plex", timeout=60000)
            
            # Wait for Cloudflare
            print("⏳ Waiting for Cloudflare...")
            await page.wait_for_timeout(60000)  # Full 60 seconds
            
            # Check page content
            content = await page.content()
            if "cloudflare" in content.lower():
                print("🛡️ Still showing Cloudflare, waiting more...")
                await page.wait_for_timeout(30000)
            
            # Step 2: Handle modals
            print("🍪 Step 2: Handle modals...")
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
            
            # Handle privacy notification
            try:
                continue_btn = page.locator("input[value='Continue']").first
                if await continue_btn.is_visible():
                    await continue_btn.click()
                    await page.wait_for_timeout(2000)
                    print("✅ Clicked Continue")
            except:
                pass
            
            # Step 3: Click ORCID
            print("🔐 Step 3: ORCID authentication...")
            orcid_img = page.locator("img[src*='orcid']").first
            if await orcid_img.is_visible():
                parent_link = orcid_img.locator("..")
                await parent_link.click()
                await page.wait_for_timeout(5000)
                print("✅ Clicked ORCID")
            
            # Handle ORCID page
            if "orcid.org" in page.url:
                print("📍 On ORCID page")
                
                # Accept cookies
                try:
                    accept_btn = page.locator("button:has-text('Accept All Cookies')").first
                    if await accept_btn.is_visible():
                        await accept_btn.click()
                        await page.wait_for_timeout(3000)
                except:
                    pass
                
                # Click Sign in
                try:
                    signin_btn = page.get_by_role("button", name="Sign in to ORCID")
                    if await signin_btn.is_visible():
                        await signin_btn.click()
                        await page.wait_for_timeout(5000)
                except:
                    pass
                
                # Fill credentials
                await page.fill("input[placeholder*='Email or']", email)
                await page.fill("input[placeholder*='password']", password)
                
                # Submit
                submit_btn = page.locator("button:has-text('Sign in to ORCID')").last
                await submit_btn.click()
                
                print("🔑 Submitted credentials")
                await page.wait_for_timeout(10000)
            
            # Step 4: Check if authenticated
            if "sicon.siam.org" in page.url:
                print("✅ Back on SICON - authenticated!")
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find manuscript links
                print("\n📋 Looking for manuscripts...")
                all_links = soup.find_all('a')
                
                for link in all_links:
                    text = link.get_text(strip=True)
                    if 'manuscript' in text.lower() or 'review' in text.lower():
                        print(f"   - Found: {text}")
                
                # Try to click on a manuscript folder
                folder_names = [
                    "Live Manuscripts Under Review",
                    "Live Manuscripts",
                    "Under Review",
                    "Manuscripts Under Review"
                ]
                
                for folder_name in folder_names:
                    try:
                        folder_link = page.locator(f"a:has-text('{folder_name}')").first
                        if await folder_link.is_visible():
                            print(f"\n🔗 Clicking: {folder_name}")
                            await folder_link.click()
                            await page.wait_for_timeout(5000)
                            
                            # Check for manuscripts
                            ms_content = await page.content()
                            if "no manuscripts" in ms_content.lower():
                                print("   ℹ️  No manuscripts in this folder")
                            else:
                                # Count tables
                                ms_soup = BeautifulSoup(ms_content, 'html.parser')
                                tables = ms_soup.find_all('table')
                                print(f"   📊 Tables found: {len(tables)}")
                                
                                # Look for manuscript IDs
                                ms_ids = re.findall(r'SICON-D-\d{2}-\d{5}', ms_content)
                                if ms_ids:
                                    print(f"   📄 Manuscripts found: {len(set(ms_ids))}")
                                    for ms_id in set(ms_ids)[:5]:
                                        print(f"      - {ms_id}")
                            break
                    except:
                        continue
                
                print("\n✅ SICON test completed successfully!")
            else:
                print(f"❌ Not on SICON after auth: {page.url}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
            # Save screenshot for debugging
            await page.screenshot(path="sicon_error.png")
            print("💾 Saved screenshot: sicon_error.png")
            
        finally:
            await browser.close()

if __name__ == "__main__":
    import re
    asyncio.run(simple_sicon_test())