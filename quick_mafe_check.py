#!/usr/bin/env python3
"""
Quick check of MAFE login page
"""

import asyncio
from playwright.async_api import async_playwright

async def check_mafe():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            print("🔍 Checking MAFE login page...")
            await page.goto("https://www2.cloud.editorialmanager.com/mafe/default2.aspx")
            await asyncio.sleep(5)
            
            # Check title
            title = await page.title()
            print(f"Title: {title}")
            
            # Handle cookies
            try:
                await page.click('button:has-text("Accept all cookies")', timeout=3000)
                print("✓ Accepted cookies")
                await asyncio.sleep(2)
            except:
                print("No cookie banner found")
            
            # Look for username field
            try:
                username = await page.wait_for_selector('#username', timeout=5000)
                print("✓ Found username field")
            except:
                print("❌ Username field not found")
                
                # List all input fields
                inputs = await page.query_selector_all('input')
                print(f"Found {len(inputs)} input fields:")
                for i, inp in enumerate(inputs):
                    inp_type = await inp.get_attribute('type')
                    inp_name = await inp.get_attribute('name')
                    inp_id = await inp.get_attribute('id')
                    inp_placeholder = await inp.get_attribute('placeholder')
                    print(f"  {i+1}. type={inp_type}, name={inp_name}, id={inp_id}, placeholder={inp_placeholder}")
            
            # Look for password field
            try:
                password = await page.wait_for_selector('#passwordTextbox', timeout=5000)
                print("✓ Found password field")
            except:
                print("❌ Password field not found")
            
            # Take screenshot
            await page.screenshot(path="mafe_login_check.png")
            print("📸 Screenshot saved: mafe_login_check.png")
            
            # Check page source for key elements
            content = await page.content()
            
            # Check for EditorialManager elements
            if "editorialmanager" in content.lower():
                print("✓ Editorial Manager page detected")
            else:
                print("❌ Not an Editorial Manager page")
                
            if "login" in content.lower():
                print("✓ Login form detected")
            else:
                print("❌ No login form found")
                
            # Check for error messages
            if "error" in content.lower():
                print("⚠️ Error message may be present")
                
            if "maintenance" in content.lower():
                print("⚠️ Maintenance message may be present")
                
            # Wait for user to examine
            print("Waiting 10 seconds for manual inspection...")
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(check_mafe())