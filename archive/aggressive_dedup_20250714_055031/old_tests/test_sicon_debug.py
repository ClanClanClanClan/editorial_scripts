#!/usr/bin/env python3
"""Debug SICON authentication and navigation"""

import asyncio
import os
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def debug_sicon():
    print("🔍 DEBUGGING SICON COMPLETE FLOW")
    print("=" * 60)
    
    email = "dylan.possamai@polytechnique.org"
    password = "Hioupy0042%"
    
    async with async_playwright() as p:
        # Use non-headless for debugging
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Step 1: Navigate to SICON
            print("📍 Step 1: Navigate to SICON...")
            await page.goto("http://sicon.siam.org/cgi-bin/main.plex", timeout=30000)
            
            # Wait for Cloudflare
            await page.wait_for_timeout(5000)
            content = await page.content()
            if "cloudflare" in content.lower():
                print("   Waiting for Cloudflare...")
                await page.wait_for_function(
                    "() => document.body.innerText.toLowerCase().includes('login')",
                    timeout=60000
                )
            
            # Step 2: Handle modals
            print("🍪 Step 2: Handle modals...")
            await page.evaluate("""
                if(document.getElementById('cookie-policy-layer-bg')) 
                    document.getElementById('cookie-policy-layer-bg').style.display = 'none';
                if(document.getElementById('cookie-policy-layer')) 
                    document.getElementById('cookie-policy-layer').style.display = 'none';
            """)
            
            # Handle privacy notification with Continue button
            continue_btn = page.locator("input[value='Continue']").first
            if await continue_btn.is_visible():
                await continue_btn.click()
                await page.wait_for_timeout(2000)
                print("   ✅ Clicked Continue on privacy modal")
            
            # Step 3: ORCID authentication
            print("🔐 Step 3: ORCID authentication...")
            orcid_img = page.locator("img[src*='orcid']").first
            if await orcid_img.is_visible():
                parent_link = orcid_img.locator("..")
                await parent_link.click()
                await page.wait_for_timeout(5000)
                print("   ✅ Clicked ORCID")
            
            # Handle ORCID page
            if "orcid.org" in page.url:
                # Accept cookies
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
                await page.fill("input[placeholder*='Email or']", email)
                await page.fill("input[placeholder*='password']", password)
                
                # Submit
                submit_btn = page.locator("button:has-text('Sign in to ORCID')").last
                await submit_btn.click()
                
                print("   ⏳ Waiting for authentication...")
                await page.wait_for_timeout(10000)
            
            # Step 4: Check SICON dashboard
            if "sicon.siam.org" in page.url:
                print("✅ Step 4: Back on SICON - authenticated!")
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find all manuscript links
                print("\n📋 Manuscript folders on dashboard:")
                all_links = soup.find_all('a')
                ms_folders = []
                
                for link in all_links:
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    # Look for manuscript-related folders
                    if any(keyword in text.lower() for keyword in ['manuscript', 'review', 'pending', 'ae ']):
                        ms_folders.append((text, href))
                        if len(ms_folders) <= 10:
                            print(f"   - {text}")
                
                # Try clicking on a manuscript folder
                if ms_folders:
                    # Look for "Under Review" or "Live Manuscripts"
                    target_folder = None
                    for text, href in ms_folders:
                        if 'live manuscript' in text.lower() or 'under review' in text.lower():
                            target_folder = text
                            break
                    
                    if target_folder:
                        print(f"\n🔗 Clicking on: {target_folder}")
                        folder_link = page.locator(f"a:has-text('{target_folder}')").first
                        await folder_link.click()
                        await page.wait_for_timeout(5000)
                        
                        # Check for manuscripts
                        ms_content = await page.content()
                        ms_soup = BeautifulSoup(ms_content, 'html.parser')
                        
                        # Look for manuscript table
                        tables = ms_soup.find_all('table')
                        print(f"\n📊 Tables found: {len(tables)}")
                        
                        # Look for "No Manuscripts" message
                        if "no manuscripts" in ms_content.lower():
                            print("   ℹ️  No manuscripts in this folder")
                        else:
                            # Count manuscript rows
                            ms_count = 0
                            for table in tables:
                                rows = table.find_all('tr')
                                # Assume first row is header
                                if len(rows) > 1:
                                    ms_count += len(rows) - 1
                            
                            print(f"   📄 Potential manuscripts found: {ms_count}")
                            
                            # Save page for analysis
                            await page.screenshot(path="sicon_manuscripts.png")
                            with open('sicon_manuscripts.html', 'w') as f:
                                f.write(ms_content)
                            print("\n💾 Saved:")
                            print("   - sicon_manuscripts.png")
                            print("   - sicon_manuscripts.html")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_sicon())