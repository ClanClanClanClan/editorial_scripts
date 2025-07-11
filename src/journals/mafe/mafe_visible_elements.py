#!/usr/bin/env python3
"""
Find visible username/password fields on MAFE page
"""

import asyncio
from playwright.async_api import async_playwright

async def find_visible_fields():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            print("🔍 Finding visible login fields on MAFE...")
            await page.goto("https://www2.cloud.editorialmanager.com/mafe/default2.aspx")
            await asyncio.sleep(3)
            
            # Handle cookies
            try:
                await page.click('button:has-text("Accept all cookies")', timeout=3000)
                await asyncio.sleep(2)
            except:
                pass
            
            # Find all text inputs that are visible
            print("=== All visible text inputs ===")
            text_inputs = await page.query_selector_all('input[type="text"]')
            for i, inp in enumerate(text_inputs):
                is_visible = await inp.is_visible()
                if is_visible:
                    name = await inp.get_attribute('name')
                    id_attr = await inp.get_attribute('id')
                    placeholder = await inp.get_attribute('placeholder')
                    bbox = await inp.bounding_box()
                    print(f"Text input {i+1}: name={name}, id={id_attr}, placeholder={placeholder}")
                    if bbox:
                        print(f"  Position: x={bbox['x']}, y={bbox['y']}")
            
            # Find all password inputs that are visible
            print("\n=== All visible password inputs ===")
            password_inputs = await page.query_selector_all('input[type="password"]')
            for i, inp in enumerate(password_inputs):
                is_visible = await inp.is_visible()
                if is_visible:
                    name = await inp.get_attribute('name')
                    id_attr = await inp.get_attribute('id')
                    placeholder = await inp.get_attribute('placeholder')
                    bbox = await inp.bounding_box()
                    print(f"Password input {i+1}: name={name}, id={id_attr}, placeholder={placeholder}")
                    if bbox:
                        print(f"  Position: x={bbox['x']}, y={bbox['y']}")
            
            # Find all visible buttons/inputs with login-related text
            print("\n=== All visible buttons/inputs ===")
            all_buttons = await page.query_selector_all('button, input[type="submit"], input[type="button"]')
            for i, btn in enumerate(all_buttons):
                is_visible = await btn.is_visible()
                if is_visible:
                    name = await btn.get_attribute('name')
                    id_attr = await btn.get_attribute('id')
                    value = await btn.get_attribute('value')
                    text = await btn.text_content()
                    bbox = await btn.bounding_box()
                    
                    # Only show buttons that might be login related
                    if any(keyword in str(value).lower() + str(text).lower() for keyword in ['login', 'editor', 'author', 'reviewer']):
                        print(f"Button {i+1}: name={name}, id={id_attr}, value={value}, text={text}")
                        if bbox:
                            print(f"  Position: x={bbox['x']}, y={bbox['y']}")
            
            # Try to find elements by their visible text/labels
            print("\n=== Looking for elements by visible text ===")
            
            # Look for "Username:" label
            username_label = await page.query_selector('text="Username:"')
            if username_label:
                print("✓ Found Username: label")
                # Try to find the associated input
                username_input = await page.query_selector('input[type="text"]')
                if username_input:
                    name = await username_input.get_attribute('name')
                    id_attr = await username_input.get_attribute('id')
                    print(f"  Associated input: name={name}, id={id_attr}")
            
            # Look for "Password:" label
            password_label = await page.query_selector('text="Password:"')
            if password_label:
                print("✓ Found Password: label")
                # Try to find the associated input
                password_input = await page.query_selector('input[type="password"]')
                if password_input:
                    name = await password_input.get_attribute('name')
                    id_attr = await password_input.get_attribute('id')
                    print(f"  Associated input: name={name}, id={id_attr}")
            
            # Look for "Editor Login" button
            editor_login = await page.query_selector('input[value="Editor Login"]')
            if editor_login:
                print("✓ Found Editor Login button")
                name = await editor_login.get_attribute('name')
                id_attr = await editor_login.get_attribute('id')
                print(f"  Details: name={name}, id={id_attr}")
            
            print("\n⏳ Waiting for manual inspection...")
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(find_visible_fields())