#!/usr/bin/env python3
"""
Detailed analysis of MAFE login form fields
"""

import asyncio
from playwright.async_api import async_playwright

async def analyze_mafe_form():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            print("🔍 Analyzing MAFE login form...")
            await page.goto("https://www2.cloud.editorialmanager.com/mafe/default2.aspx")
            await asyncio.sleep(3)
            
            # Handle cookies
            try:
                await page.click('button:has-text("Accept all cookies")', timeout=3000)
                await asyncio.sleep(2)
            except:
                pass
            
            # Find the login form
            forms = await page.query_selector_all('form')
            print(f"Found {len(forms)} forms")
            
            for i, form in enumerate(forms):
                print(f"\n--- Form {i+1} ---")
                
                # Check form attributes
                action = await form.get_attribute('action')
                method = await form.get_attribute('method')
                form_id = await form.get_attribute('id')
                form_name = await form.get_attribute('name')
                
                print(f"Form ID: {form_id}")
                print(f"Form Name: {form_name}")
                print(f"Action: {action}")
                print(f"Method: {method}")
                
                # Find inputs in this form
                inputs = await form.query_selector_all('input')
                print(f"Contains {len(inputs)} inputs:")
                
                for j, inp in enumerate(inputs):
                    inp_type = await inp.get_attribute('type')
                    inp_name = await inp.get_attribute('name')
                    inp_id = await inp.get_attribute('id')
                    inp_placeholder = await inp.get_attribute('placeholder')
                    inp_value = await inp.get_attribute('value')
                    
                    # Only show visible text/password inputs
                    if inp_type in ['text', 'password']:
                        print(f"  Input {j+1}: type={inp_type}, name={inp_name}, id={inp_id}, placeholder={inp_placeholder}, value={inp_value}")
                        
                        # Check if it's visible
                        is_visible = await inp.is_visible()
                        print(f"    Visible: {is_visible}")
                        
                        # Get bounding box to see position
                        try:
                            bbox = await inp.bounding_box()
                            if bbox:
                                print(f"    Position: x={bbox['x']}, y={bbox['y']}, width={bbox['width']}, height={bbox['height']}")
                        except:
                            pass
                
                # Find buttons in this form
                buttons = await form.query_selector_all('input[type="submit"], button')
                print(f"Contains {len(buttons)} buttons:")
                
                for k, btn in enumerate(buttons):
                    btn_type = await btn.get_attribute('type')
                    btn_name = await btn.get_attribute('name')
                    btn_id = await btn.get_attribute('id')
                    btn_value = await btn.get_attribute('value')
                    btn_text = await btn.text_content()
                    
                    print(f"  Button {k+1}: type={btn_type}, name={btn_name}, id={btn_id}, value={btn_value}, text={btn_text}")
            
            # Look for username/password fields specifically
            print("\n=== Looking for Username/Password fields ===")
            
            # Try various selectors for username
            username_selectors = [
                'input[name*="username"]',
                'input[name*="user"]',
                'input[name*="login"]',
                'input[name*="email"]',
                'input[placeholder*="username"]',
                'input[placeholder*="user"]',
                'input[placeholder*="email"]'
            ]
            
            for selector in username_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        name = await element.get_attribute('name')
                        id_attr = await element.get_attribute('id')
                        placeholder = await element.get_attribute('placeholder')
                        print(f"✓ Potential username field: {selector}")
                        print(f"  name={name}, id={id_attr}, placeholder={placeholder}")
                except:
                    pass
            
            # Try various selectors for password
            password_selectors = [
                'input[type="password"]',
                'input[name*="password"]',
                'input[name*="pass"]',
                'input[placeholder*="password"]',
                'input[placeholder*="pass"]'
            ]
            
            for selector in password_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        name = await element.get_attribute('name')
                        id_attr = await element.get_attribute('id')
                        placeholder = await element.get_attribute('placeholder')
                        print(f"✓ Potential password field: {selector}")
                        print(f"  name={name}, id={id_attr}, placeholder={placeholder}")
                except:
                    pass
            
            # Look for "Editor Login" button specifically
            print("\n=== Looking for Editor Login button ===")
            
            editor_login_selectors = [
                'input[value*="Editor Login"]',
                'button:has-text("Editor Login")',
                'input[name*="editor"]',
                'input[name*="Editor"]'
            ]
            
            for selector in editor_login_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        name = await element.get_attribute('name')
                        id_attr = await element.get_attribute('id')
                        value = await element.get_attribute('value')
                        print(f"✓ Potential Editor Login button: {selector}")
                        print(f"  name={name}, id={id_attr}, value={value}")
                except:
                    pass
            
            # Wait for manual inspection
            print("\n⏳ Waiting for manual inspection...")
            await asyncio.sleep(15)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(analyze_mafe_form())