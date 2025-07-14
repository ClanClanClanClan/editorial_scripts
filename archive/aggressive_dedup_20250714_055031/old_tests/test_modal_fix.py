#!/usr/bin/env python3
"""Test privacy modal handling and ORCID clicking"""

import asyncio
from playwright.async_api import async_playwright

async def test_modal_and_orcid():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            print("📍 Navigating to SICON...")
            await page.goto("http://sicon.siam.org/cgi-bin/main.plex", timeout=30000)
            
            # Wait for Cloudflare if needed
            content = await page.content()
            if "cloudflare" in content.lower():
                print("🛡️ Waiting for Cloudflare...")
                await page.wait_for_function(
                    "() => document.body.innerText.toLowerCase().includes('login')",
                    timeout=60000
                )
                print("✅ Cloudflare cleared")
            
            await page.screenshot(path="test_before_modal.png")
            
            # Handle modals
            print("🔒 Handling modals...")
            await page.wait_for_timeout(3000)
            
            # First handle cookie policy modal
            print("🍪 Checking for cookie policy modal...")
            cookie_modal = page.locator("#cookie-policy-layer-bg")
            if await cookie_modal.is_visible():
                print("✅ Found cookie policy modal - dismissing with JS...")
                await page.evaluate("document.getElementById('cookie-policy-layer-bg').style.display = 'none';")
                await page.wait_for_timeout(1000)
                print("✅ Cookie modal dismissed")
            else:
                print("❌ No cookie modal visible")
            
            # Then handle privacy modal
            continue_btn = page.locator("button:has-text('Continue')")
            if await continue_btn.is_visible():
                print("✅ Found privacy Continue button - clicking...")
                await continue_btn.click()
                await page.wait_for_timeout(3000)
                print("✅ Privacy modal dismissed")
            else:
                print("❌ No privacy Continue button visible")
            
            await page.screenshot(path="test_after_modal.png")
            
            # Try to click ORCID
            print("🔍 Looking for ORCID...")
            
            # Look for ORCID image first
            orcid_img = page.locator("img[src*='orcid']").first
            if await orcid_img.is_visible():
                print("✅ Found ORCID image - checking parent...")
                parent = orcid_img.locator("..")
                if await parent.is_visible():
                    print("✅ Clicking ORCID image parent...")
                    await parent.click()
                    await page.wait_for_timeout(5000)
                    
                    if "orcid.org" in page.url:
                        print("🎉 Successfully navigated to ORCID!")
                        await page.screenshot(path="test_orcid_success.png")
                    else:
                        print(f"❌ Not on ORCID page: {page.url}")
                        await page.screenshot(path="test_orcid_failed.png")
            else:
                print("❌ ORCID image not visible")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_modal_and_orcid())