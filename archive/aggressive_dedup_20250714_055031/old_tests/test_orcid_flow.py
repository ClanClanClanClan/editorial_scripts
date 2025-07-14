#!/usr/bin/env python3
"""Test complete ORCID authentication flow step by step"""

import asyncio
import os
from playwright.async_api import async_playwright

async def test_orcid_flow():
    print("🧪 TESTING COMPLETE ORCID FLOW")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Step 1: Navigate to ORCID directly
            print("\n📍 Step 1: Navigate directly to ORCID signin...")
            await page.goto("https://orcid.org/signin", timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Step 2: Handle cookie consent
            print("\n🍪 Step 2: Handle cookie consent...")
            accept_btn = page.locator("button:has-text('Accept All Cookies')").first
            if await accept_btn.is_visible():
                print("   Found 'Accept All Cookies' - clicking...")
                await accept_btn.click()
                await page.wait_for_timeout(3000)
                print("   ✅ Cookies accepted")
            else:
                print("   No cookie consent visible")
            
            await page.screenshot(path="orcid_flow_1.png")
            
            # Step 3: Check for username field
            print("\n🔍 Step 3: Check for username field...")
            username_visible = await page.locator("#username").is_visible()
            print(f"   Username field visible: {username_visible}")
            
            if not username_visible:
                # Check if we need to click Sign in to ORCID
                signin_btn = page.get_by_role("button", name="Sign in to ORCID")
                if await signin_btn.is_visible():
                    print("   Found 'Sign in to ORCID' button - clicking...")
                    await signin_btn.click()
                    await page.wait_for_timeout(5000)
                    username_visible = await page.locator("#username").is_visible()
                    print(f"   Username field visible after click: {username_visible}")
            
            await page.screenshot(path="orcid_flow_2.png")
            
            # Step 4: Enter credentials if field is visible
            if username_visible:
                print("\n🔐 Step 4: Enter credentials...")
                email = os.environ.get('ORCID_EMAIL', 'dylan.possamai@polytechnique.org')
                password = os.environ.get('ORCID_PASSWORD', 'Hioupy0042%')
                
                await page.fill("#username", email)
                print("   ✅ Email entered")
                
                await page.fill("#password", password)
                print("   ✅ Password entered")
                
                await page.screenshot(path="orcid_flow_3_filled.png")
                
                # Submit
                await page.click("button[type='submit']")
                print("   ✅ Form submitted")
                
                await page.wait_for_timeout(5000)
                await page.screenshot(path="orcid_flow_4_after_submit.png")
                
                # Check result
                if "authorize" in page.url or "signin" not in page.url:
                    print("\n🎉 AUTHENTICATION SUCCESS!")
                    print(f"   Current URL: {page.url}")
                else:
                    print(f"\n❌ Authentication may have failed")
                    print(f"   Current URL: {page.url}")
            else:
                print("\n❌ Could not find username field!")
                
            print("\n⏸️ Keeping browser open for 10 seconds...")
            await page.wait_for_timeout(10000)
            
        except Exception as e:
            print(f"\n❌ Test error: {e}")
            await page.screenshot(path="orcid_error.png")
        finally:
            await browser.close()
    
    print("\n📸 Screenshots saved:")
    print("   orcid_flow_1.png - After cookie handling")
    print("   orcid_flow_2.png - After sign in button")
    print("   orcid_flow_3_filled.png - With credentials")
    print("   orcid_flow_4_after_submit.png - After submission")

if __name__ == "__main__":
    os.environ['ORCID_EMAIL'] = "dylan.possamai@polytechnique.org"
    os.environ['ORCID_PASSWORD'] = "Hioupy0042%"
    asyncio.run(test_orcid_flow())