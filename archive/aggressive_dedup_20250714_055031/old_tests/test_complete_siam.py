#!/usr/bin/env python3
"""
Complete SIAM authentication test with all fixes
"""

import asyncio
import subprocess
from playwright.async_api import async_playwright

async def test_complete_siam():
    """Test complete SIAM authentication flow"""
    print("🧪 COMPLETE SIAM AUTHENTICATION TEST")
    print("=" * 60)
    
    # Get credentials
    try:
        userId_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=userId'], 
                                   capture_output=True, text=True)
        password_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=password'], 
                                     capture_output=True, text=True)
        
        if userId_cmd.returncode == 0 and password_cmd.returncode == 0:
            orcid_email = userId_cmd.stdout.strip()
            orcid_password = password_cmd.stdout.strip()
            print(f"✅ Got credentials: {orcid_email[:3]}****")
        else:
            print("❌ Failed to get 1Password credentials")
            return
    except Exception as e:
        print(f"❌ Credential error: {e}")
        return
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Step 1: Navigate and handle Cloudflare
            print("\n📍 Step 1: Navigate to SICON...")
            await page.goto("http://sicon.siam.org/cgi-bin/main.plex", timeout=30000)
            
            content = await page.content()
            if "cloudflare" in content.lower() or "verifying you are human" in content.lower():
                print("🛡️ Cloudflare detected - waiting up to 60 seconds...")
                try:
                    await page.wait_for_function(
                        """() => {
                            const content = document.body.innerText.toLowerCase();
                            return content.includes('login') || 
                                   content.includes('orcid') || 
                                   content.includes('sign in');
                        }""",
                        timeout=60000
                    )
                    print("✅ Cloudflare challenge passed!")
                except:
                    print("⚠️ Cloudflare timeout - continuing...")
                    await page.wait_for_timeout(10000)
            
            # Step 2: Handle cookie policy modal
            print("\n🍪 Step 2: Handle cookie policy modal...")
            await page.wait_for_timeout(3000)
            
            cookie_modal = page.locator("#cookie-policy-layer-bg")
            if await cookie_modal.is_visible():
                print("✅ Found cookie policy modal - dismissing...")
                await page.evaluate("document.getElementById('cookie-policy-layer-bg').style.display = 'none';")
                await page.wait_for_timeout(1000)
                print("✅ Cookie modal dismissed")
            
            # Step 3: Handle privacy modal
            print("\n🔒 Step 3: Handle privacy modal...")
            continue_btn = page.locator("button:has-text('Continue')")
            if await continue_btn.is_visible():
                print("✅ Found privacy modal - clicking Continue...")
                await continue_btn.click()
                await page.wait_for_timeout(3000)
                print("✅ Privacy modal dismissed")
            
            await page.screenshot(path="complete_after_modals.png")
            
            # Step 4: Click ORCID
            print("\n🔗 Step 4: Click ORCID login...")
            orcid_img = page.locator("img[src*='orcid']").first
            if await orcid_img.is_visible():
                print("✅ Found ORCID image - clicking parent...")
                parent_link = orcid_img.locator("..")
                await parent_link.click()
                await page.wait_for_timeout(5000)
                
                if "orcid.org" in page.url:
                    print("🎉 Successfully navigated to ORCID page!")
                    await page.screenshot(path="complete_orcid_page.png")
                    
                    # Step 5: Dismiss ORCID cookie modal using X button
                    print("\n🍪 Step 5: Dismiss ORCID cookie modal...")
                    await page.wait_for_timeout(3000)
                    
                    # Try clicking the X button to close the modal
                    close_btn = page.locator("button[aria-label='Close']")
                    if await close_btn.is_visible():
                        print("✅ Found close button - clicking...")
                        await close_btn.click()
                        await page.wait_for_timeout(2000)
                        print("✅ Modal closed with X button")
                    else:
                        # Try JavaScript to hide the modal
                        print("✅ Trying JavaScript to hide cookie modal...")
                        await page.evaluate("""
                            // Try to hide cookie consent modals
                            const modals = document.querySelectorAll('[class*="cookie"], [id*="cookie"], [class*="consent"], [id*="consent"]');
                            modals.forEach(modal => {
                                if (modal.style) modal.style.display = 'none';
                            });
                            
                            // Also try to hide any overlay
                            const overlays = document.querySelectorAll('[class*="overlay"], [id*="overlay"]');
                            overlays.forEach(overlay => {
                                if (overlay.style) overlay.style.display = 'none';
                            });
                        """)
                        await page.wait_for_timeout(2000)
                        print("✅ JavaScript modal dismissal attempted")
                    
                    # Now try to click Sign in to ORCID
                    signin_btn = page.get_by_role("button", name="Sign in to ORCID")
                    if await signin_btn.is_visible():
                        print("✅ Found 'Sign in to ORCID' button - clicking...")
                        await signin_btn.click()
                        await page.wait_for_timeout(5000)
                        print("✅ Clicked Sign in to ORCID")
                    
                    # Step 6: Enter credentials
                    print("\n🔐 Step 6: Enter ORCID credentials...")
                    await page.wait_for_timeout(2000)
                    
                    # Try multiple selectors for username field
                    username_selectors = ["#username", "#userId", "[name='userId']", "[name='username']"]
                    username_filled = False
                    
                    for selector in username_selectors:
                        try:
                            if await page.locator(selector).is_visible():
                                await page.fill(selector, orcid_email)
                                username_filled = True
                                print(f"✅ Filled username with selector: {selector}")
                                break
                        except:
                            continue
                    
                    if not username_filled:
                        print("❌ Could not find username field")
                        return False
                    
                    # Fill password
                    await page.fill("#password", orcid_password)
                    await page.click("button[type='submit']")
                    await page.wait_for_timeout(5000)
                    
                    # Check result
                    if "sicon.siam.org" in page.url:
                        print("🎉 COMPLETE SUCCESS! Authenticated with SIAM!")
                        await page.screenshot(path="complete_authenticated.png")
                        return True
                    else:
                        print(f"❌ Authentication failed - URL: {page.url}")
                        await page.screenshot(path="complete_auth_failed.png")
                else:
                    print(f"❌ Not on ORCID page - URL: {page.url}")
            else:
                print("❌ ORCID image not found")
                
        except Exception as e:
            print(f"❌ Test error: {e}")
            await page.screenshot(path="complete_error.png")
        finally:
            await browser.close()
    
    return False

if __name__ == "__main__":
    success = asyncio.run(test_complete_siam())
    if success:
        print("\n🎉 SIAM SCRAPERS ARE NOW WORKING!")
        print("All fixes have been successfully implemented:")
        print("✅ Cloudflare challenge handling (60s wait)")
        print("✅ Cookie policy modal dismissal")
        print("✅ Privacy modal handling") 
        print("✅ ORCID login clicking")
        print("✅ Direct 1Password credential access")
    else:
        print("\n❌ Test failed - check screenshots for details")