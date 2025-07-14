#!/usr/bin/env python3
"""
Debug SIAM authentication with detailed screenshots
"""

import asyncio
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

# Add src and core to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Get ORCID credentials from 1Password
def setup_credentials():
    """Get and set ORCID credentials"""
    try:
        # Get userId field
        userId_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=userId'], 
                                   capture_output=True, text=True)
        # Get password field
        password_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=password'], 
                                     capture_output=True, text=True)
        
        if userId_cmd.returncode == 0 and password_cmd.returncode == 0:
            os.environ['ORCID_EMAIL'] = userId_cmd.stdout.strip()
            os.environ['ORCID_PASSWORD'] = password_cmd.stdout.strip()
            print(f"✅ Credentials set: {userId_cmd.stdout.strip()[:3]}****")
            return True
    except:
        pass
    return False

async def debug_sicon_auth():
    """Debug SICON authentication step by step"""
    print("\n🔍 DEBUGGING SICON AUTHENTICATION")
    print("=" * 60)
    
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        # Launch browser in non-headless mode for debugging
        browser = await p.chromium.launch(headless=False)
        print("✅ Browser launched (non-headless)")
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        print("✅ Context created")
        
        page = await context.new_page()
        print("✅ Page created")
        
        try:
            # Step 1: Navigate to login page
            login_url = "http://sicon.siam.org/cgi-bin/main.plex"
            print(f"\n📍 Navigating to: {login_url}")
            await page.goto(login_url, timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Save screenshot
            await page.screenshot(path="debug_1_initial_page.png")
            print("📸 Screenshot saved: debug_1_initial_page.png")
            
            # Step 2: Check for privacy modal
            print("\n🔍 Checking for privacy modal...")
            try:
                continue_button = page.locator("button:has-text('Continue')")
                if await continue_button.is_visible(timeout=3000):
                    print("✅ Privacy modal found - clicking Continue")
                    await continue_button.click()
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path="debug_2_after_continue.png")
                    print("📸 Screenshot saved: debug_2_after_continue.png")
                else:
                    print("❌ No privacy modal found")
            except Exception as e:
                print(f"⚠️ Error handling privacy modal: {e}")
            
            # Step 3: Look for ORCID login
            print("\n🔍 Looking for ORCID login...")
            orcid_selectors = [
                "a[href*='orcid']",
                "text=Sign in with ORCID", 
                "text=ORCID",
                "button:has-text('ORCID')",
                "input[value*='ORCID']",
                "a:has-text('Sign in with ORCID')",
                "a:has-text('ORCID')"
            ]
            
            found = False
            for selector in orcid_selectors:
                try:
                    elements = await page.locator(selector).all()
                    if elements:
                        print(f"✅ Found {len(elements)} element(s) with selector: {selector}")
                        for i, elem in enumerate(elements):
                            text = await elem.text_content() or ""
                            is_visible = await elem.is_visible()
                            print(f"   Element {i}: '{text.strip()}' - Visible: {is_visible}")
                        found = True
                except:
                    pass
            
            if not found:
                print("❌ No ORCID elements found")
                
                # Get all links on page
                print("\n📋 All links on page:")
                links = await page.locator("a").all()
                for i, link in enumerate(links[:20]):  # First 20 links
                    try:
                        text = await link.text_content() or ""
                        href = await link.get_attribute("href") or ""
                        if text.strip():
                            print(f"   Link {i}: '{text.strip()}' -> {href}")
                    except:
                        pass
            
            # Step 4: Save page HTML
            html = await page.content()
            with open("debug_page_source.html", "w") as f:
                f.write(html)
            print("\n📄 Page source saved: debug_page_source.html")
            
            # Wait for user to see
            print("\n⏸️ Browser will stay open for 10 seconds...")
            await page.wait_for_timeout(10000)
            
        except Exception as e:
            print(f"\n❌ Error during debug: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()
            print("\n✅ Browser closed")

async def main():
    """Main debug execution"""
    print("🔍 SIAM AUTHENTICATION DEBUG")
    print("=" * 80)
    
    # Setup credentials
    if not setup_credentials():
        print("❌ Failed to get credentials from 1Password")
        return
    
    # Run debug
    await debug_sicon_auth()
    
    print("\n📋 Debug Summary:")
    print("1. Check debug_1_initial_page.png - Shows initial page")
    print("2. Check debug_2_after_continue.png - Shows page after privacy modal")
    print("3. Check debug_page_source.html - Contains full page HTML")
    print("4. Look for ORCID login link in the output above")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Debug interrupted")
    except Exception as e:
        print(f"\n❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()