#!/usr/bin/env python3
"""Debug ORCID authentication issues"""

import asyncio
import os
from playwright.async_api import async_playwright

async def debug_orcid():
    print("🔍 DEBUGGING ORCID AUTHENTICATION")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Navigate to SICON
            print("📍 Navigating to SICON...")
            await page.goto("http://sicon.siam.org/cgi-bin/main.plex", timeout=30000)
            
            # Wait for Cloudflare
            await page.wait_for_timeout(5000)
            content = await page.content()
            if "cloudflare" in content.lower():
                print("🛡️ Waiting for Cloudflare...")
                await page.wait_for_function(
                    "() => document.body.innerText.toLowerCase().includes('login')",
                    timeout=60000
                )
            
            # Dismiss cookie modal
            print("🍪 Dismissing cookie modal...")
            await page.evaluate("if(document.getElementById('cookie-policy-layer-bg')) document.getElementById('cookie-policy-layer-bg').style.display = 'none';")
            await page.wait_for_timeout(2000)
            
            # Click ORCID
            print("🔗 Clicking ORCID...")
            orcid_img = page.locator("img[src*='orcid']").first
            if await orcid_img.is_visible():
                parent_link = orcid_img.locator("..")
                await parent_link.click()
                await page.wait_for_timeout(5000)
                
                if "orcid.org" in page.url:
                    print("✅ On ORCID page!")
                    await page.screenshot(path="debug_orcid_1.png")
                    
                    # Debug: Check what's on the page
                    print("\n📋 Page analysis:")
                    
                    # Check for cookie modal
                    cookie_modal = await page.locator("[class*='cookie']").count()
                    print(f"   Cookie elements: {cookie_modal}")
                    
                    # Check for Sign in button
                    signin_btns = await page.get_by_role("button", name="Sign in to ORCID").count()
                    print(f"   Sign in buttons: {signin_btns}")
                    
                    # Check for username fields
                    username_fields = await page.locator("#username").count()
                    print(f"   Username fields (#username): {username_fields}")
                    
                    userid_fields = await page.locator("[name='userId']").count()
                    print(f"   UserId fields: {userid_fields}")
                    
                    # Try clicking Sign in to ORCID
                    try:
                        signin_btn = page.get_by_role("button", name="Sign in to ORCID")
                        if await signin_btn.is_visible():
                            print("\n🔘 Clicking 'Sign in to ORCID'...")
                            await signin_btn.click()
                            await page.wait_for_timeout(5000)
                            await page.screenshot(path="debug_orcid_2.png")
                            
                            # Check again for fields
                            username_after = await page.locator("#username").count()
                            print(f"   Username fields after click: {username_after}")
                            
                            if username_after > 0:
                                print("✅ Username field now visible!")
                            else:
                                print("❌ Username field still not visible")
                                
                                # Try to dismiss any overlays with JS
                                print("🔧 Trying JS to remove overlays...")
                                await page.evaluate("""
                                    // Remove cookie modals
                                    document.querySelectorAll('[class*="cookie"], [id*="cookie"]').forEach(el => {
                                        if (el.style) el.style.display = 'none';
                                    });
                                    // Remove overlays
                                    document.querySelectorAll('[class*="overlay"]').forEach(el => {
                                        if (el.style) el.style.display = 'none';
                                    });
                                """)
                                await page.wait_for_timeout(2000)
                                await page.screenshot(path="debug_orcid_3.png")
                                
                                # Final check
                                username_final = await page.locator("#username").count()
                                print(f"   Username fields after JS: {username_final}")
                    except Exception as e:
                        print(f"❌ Sign in button error: {e}")
                        
            print("\n⏸️ Keeping browser open for 10 seconds...")
            await page.wait_for_timeout(10000)
            
        except Exception as e:
            print(f"❌ Debug error: {e}")
            await page.screenshot(path="debug_error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    os.environ['ORCID_EMAIL'] = "dylan.possamai@polytechnique.org"
    os.environ['ORCID_PASSWORD'] = "Hioupy0042%"
    asyncio.run(debug_orcid())