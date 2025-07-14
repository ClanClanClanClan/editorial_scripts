#!/usr/bin/env python3
"""
Check for iframes and dynamic content on MAFE page
"""

import asyncio
from playwright.async_api import async_playwright

async def check_iframes_and_dynamic():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            print("🔍 Checking for iframes and dynamic content...")
            await page.goto("https://www2.cloud.editorialmanager.com/mafe/default2.aspx")
            await asyncio.sleep(5)
            
            # Handle cookies
            try:
                await page.click('button:has-text("Accept all cookies")', timeout=3000)
                await asyncio.sleep(3)
            except:
                pass
            
            # Check for iframes
            print("=== Checking for iframes ===")
            frames = page.frames
            print(f"Found {len(frames)} frames")
            
            for i, frame in enumerate(frames):
                print(f"Frame {i+1}: {frame.url}")
                
                if i > 0:  # Skip main frame
                    print(f"  Checking frame {i+1} for login fields...")
                    
                    # Check for inputs in this frame
                    try:
                        frame_inputs = await frame.query_selector_all('input')
                        print(f"    Found {len(frame_inputs)} inputs in frame {i+1}")
                        
                        for j, inp in enumerate(frame_inputs):
                            inp_type = await inp.get_attribute('type')
                            inp_name = await inp.get_attribute('name')
                            inp_id = await inp.get_attribute('id')
                            
                            if inp_type in ['text', 'password']:
                                print(f"      Input {j+1}: type={inp_type}, name={inp_name}, id={inp_id}")
                    except Exception as e:
                        print(f"    Error checking frame {i+1}: {e}")
            
            # Wait for page to fully load
            print("\n=== Waiting for dynamic content ===")
            await asyncio.sleep(10)
            
            # Check again after waiting
            print("=== Checking again after waiting ===")
            
            # Try to find by XPath
            print("Trying XPath selectors...")
            
            # Check page source for the actual HTML
            content = await page.content()
            
            # Look for input fields in the HTML
            if 'type="text"' in content:
                print("✓ Found text input in HTML")
                # Count them
                text_count = content.count('type="text"')
                print(f"  Found {text_count} text inputs in HTML")
            
            if 'type="password"' in content:
                print("✓ Found password input in HTML")
                # Count them
                password_count = content.count('type="password"')
                print(f"  Found {password_count} password inputs in HTML")
            
            if 'Username:' in content:
                print("✓ Found 'Username:' text in HTML")
                
            if 'Password:' in content:
                print("✓ Found 'Password:' text in HTML")
                
            if 'Editor Login' in content:
                print("✓ Found 'Editor Login' text in HTML")
            
            # Try to interact with the login form by clicking on it
            print("\n=== Trying to interact with login form ===")
            
            # Try to click where username field should be (based on screenshot)
            try:
                await page.click('body', position={'x': 650, 'y': 300})
                await asyncio.sleep(1)
                await page.type('body', 'test_username')
                print("✓ Successfully typed in username area")
            except Exception as e:
                print(f"Failed to type username: {e}")
            
            # Try to click where password field should be
            try:
                await page.click('body', position={'x': 650, 'y': 325})
                await asyncio.sleep(1)
                await page.type('body', 'test_password')
                print("✓ Successfully typed in password area")
            except Exception as e:
                print(f"Failed to type password: {e}")
            
            # Try to click Editor Login button
            try:
                await page.click('body', position={'x': 664, 'y': 375})
                await asyncio.sleep(2)
                print("✓ Successfully clicked Editor Login area")
            except Exception as e:
                print(f"Failed to click Editor Login: {e}")
            
            # Take another screenshot
            await page.screenshot(path="mafe_after_interaction.png")
            print("📸 Screenshot saved: mafe_after_interaction.png")
            
            print("\n⏳ Waiting for manual inspection...")
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(check_iframes_and_dynamic())