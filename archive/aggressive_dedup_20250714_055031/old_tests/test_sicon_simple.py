#!/usr/bin/env python3
"""Simple SICON test without stealth complications"""

import asyncio
import os
from playwright.async_api import async_playwright

async def test_sicon_simple():
    print("🧪 SIMPLE SICON TEST")
    print("=" * 50)
    
    email = "dylan.possamai@polytechnique.org"
    password = "Hioupy0042%"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Navigate to SICON
            print("📍 Navigating to SICON...")
            await page.goto("http://sicon.siam.org/cgi-bin/main.plex", timeout=30000)
            
            # Wait for Cloudflare
            await page.wait_for_timeout(5000)
            
            # Dismiss cookie modal
            await page.evaluate("if(document.getElementById('cookie-policy-layer-bg')) document.getElementById('cookie-policy-layer-bg').style.display = 'none';")
            await page.wait_for_timeout(2000)
            
            # Dismiss privacy modal
            continue_btn = page.locator("input[value='Continue']").first
            if await continue_btn.is_visible():
                await continue_btn.click()
                await page.wait_for_timeout(2000)
            
            # Click ORCID
            print("🔗 Clicking ORCID...")
            orcid_img = page.locator("img[src*='orcid']").first
            parent_link = orcid_img.locator("..")
            await parent_link.click()
            await page.wait_for_timeout(5000)
            
            # Accept ORCID cookies
            accept_btn = page.locator("button:has-text('Accept All Cookies')").first
            if await accept_btn.is_visible():
                await accept_btn.click()
                await page.wait_for_timeout(3000)
            
            # Click Sign in
            signin_btn = page.get_by_role("button", name="Sign in to ORCID")
            if await signin_btn.is_visible():
                await signin_btn.click()
                await page.wait_for_timeout(5000)
            
            # Enter credentials
            print("🔐 Entering credentials...")
            await page.fill("input[placeholder*='Email or']", email)
            await page.fill("input[placeholder*='password']", password)
            
            # Submit
            submit_btn = page.locator("button:has-text('Sign in to ORCID')").last
            await submit_btn.click()
            
            print("⏳ Waiting for authentication...")
            await page.wait_for_timeout(10000)
            
            # Check result
            print(f"\n📍 Current URL: {page.url}")
            
            if "sicon.siam.org" in page.url:
                print("✅ Back on SICON!")
                await page.screenshot(path="sicon_authenticated.png")
                
                # Look for manuscript links
                print("\n🔍 Looking for manuscript folders...")
                
                # Get all links
                links = await page.locator("a").all()
                manuscript_links = []
                
                for link in links:
                    try:
                        text = await link.text_content()
                        href = await link.get_attribute("href")
                        if text and any(word in text.lower() for word in ['pending', 'review', 'manuscript', 'folder']):
                            manuscript_links.append(f"{text.strip()} -> {href}")
                    except:
                        pass
                
                if manuscript_links:
                    print("✅ Found manuscript-related links:")
                    for ml in manuscript_links[:10]:
                        print(f"   - {ml}")
                else:
                    print("❌ No manuscript links found")
                    
                    # Try clicking on first folder with manuscripts
                    folder_link = page.locator("a[href*='folder_id']").first
                    if await folder_link.is_visible():
                        print("\n🔗 Clicking first folder link...")
                        await folder_link.click()
                        await page.wait_for_timeout(5000)
                        await page.screenshot(path="sicon_folder.png")
                        print("📸 Screenshot saved: sicon_folder.png")
            else:
                print("❌ Not on SICON after auth")
                
            print("\n⏸️ Keeping browser open for 10 seconds...")
            await page.wait_for_timeout(10000)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_sicon_simple())