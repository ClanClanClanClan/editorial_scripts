#!/usr/bin/env python3
"""
Simple direct test of SIAM authentication
"""

import asyncio
import os
import subprocess
from playwright.async_api import async_playwright

# Get credentials
userId_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=userId'], 
                           capture_output=True, text=True)
password_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=password'], 
                             capture_output=True, text=True)

os.environ['ORCID_EMAIL'] = userId_cmd.stdout.strip()
os.environ['ORCID_PASSWORD'] = password_cmd.stdout.strip()
print(f"✅ Credentials: {userId_cmd.stdout.strip()[:3]}****")

async def test_sicon():
    """Direct test of SICON authentication"""
    print("\n🔍 Testing SICON Authentication")
    print("=" * 50)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate to SICON
        print("📍 Navigating to SICON...")
        await page.goto("http://sicon.siam.org/cgi-bin/main.plex")
        await page.wait_for_timeout(3000)
        
        # Handle privacy modal
        print("🔍 Checking for privacy modal...")
        try:
            continue_btn = page.locator("button:has-text('Continue')")
            if await continue_btn.is_visible():
                print("✅ Found privacy modal - clicking Continue")
                await continue_btn.click()
                await page.wait_for_timeout(2000)
        except:
            print("❌ No privacy modal")
        
        # Save screenshot
        await page.screenshot(path="test_sicon_after_modal.png")
        print("📸 Saved: test_sicon_after_modal.png")
        
        # Look for ORCID
        print("\n🔍 Looking for ORCID login...")
        
        # Try image-based ORCID link
        orcid_img = page.locator("img[src*='orcid']")
        if await orcid_img.count() > 0:
            print("✅ Found ORCID image")
            parent = orcid_img.locator("..")
            if await parent.count() > 0:
                tag = await parent.evaluate("el => el.tagName")
                if tag.lower() == 'a':
                    print("✅ ORCID image is in a link - clicking")
                    await parent.click()
                    await page.wait_for_timeout(3000)
                    
                    # Check if we're on ORCID page
                    if "orcid.org" in page.url:
                        print("✅ Successfully navigated to ORCID login!")
                        await page.screenshot(path="test_orcid_page.png")
                        
                        # Try to login
                        print("\n🔐 Attempting ORCID login...")
                        email = os.environ.get('ORCID_EMAIL')
                        password = os.environ.get('ORCID_PASSWORD')
                        
                        # Enter credentials
                        await page.fill("#username", email)
                        await page.fill("#password", password)
                        await page.click("button[type='submit']")
                        await page.wait_for_timeout(5000)
                        
                        # Check result
                        if "sicon.siam.org" in page.url:
                            print("✅ Successfully authenticated!")
                            await page.screenshot(path="test_authenticated.png")
                        else:
                            print(f"❌ Authentication failed - URL: {page.url}")
                    else:
                        print(f"❌ Not on ORCID page - URL: {page.url}")
        else:
            print("❌ No ORCID image found")
            
            # Try text-based search
            links = await page.locator("a").all()
            print(f"\n📋 Found {len(links)} links on page")
            for link in links[:10]:
                try:
                    text = await link.text_content()
                    href = await link.get_attribute("href")
                    if text and "orcid" in text.lower():
                        print(f"   Found ORCID link: {text} -> {href}")
                except:
                    pass
        
        await browser.close()

# Run test
asyncio.run(test_sicon())
print("\n✅ Test complete!")