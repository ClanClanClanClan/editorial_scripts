#!/usr/bin/env python3
"""
Investigate journal login pages using Playwright to understand current structure
"""

import asyncio
import os
from playwright.async_api import async_playwright
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def investigate_journal(journal_name, url, username_field, password_field, expected_elements):
    """Investigate a journal's login page structure"""
    print(f"\n🔍 Investigating {journal_name}")
    print(f"   URL: {url}")
    print(f"   Expected username field: {username_field}")
    print(f"   Expected password field: {password_field}")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Navigate to the page
            await page.goto(url)
            await asyncio.sleep(3)
            
            # Check page title
            title = await page.title()
            print(f"✓ Page title: {title}")
            
            # Check if page loaded successfully
            if "error" in title.lower() or "404" in title.lower():
                print("❌ Page appears to have an error")
                return False
            
            # Handle cookies
            cookie_selectors = [
                'button:has-text("Accept all cookies")',
                'button:has-text("Accept cookies")',
                'button:has-text("Accept")',
                'button:has-text("Got it")',
                'button:has-text("Agree")',
                '.cc-btn',
                '.cookie-accept',
                '.accept-cookies'
            ]
            
            for selector in cookie_selectors:
                try:
                    await page.click(selector, timeout=2000)
                    print(f"✓ Clicked cookie button: {selector}")
                    await asyncio.sleep(1)
                    break
                except:
                    continue
            
            # Check for username field
            username_found = False
            username_selectors = [
                f'#{username_field}',
                f'[name="{username_field}"]',
                'input[type="text"]',
                'input[type="email"]',
                'input[placeholder*="username"]',
                'input[placeholder*="email"]',
                'input[placeholder*="Username"]',
                'input[placeholder*="Email"]'
            ]
            
            for selector in username_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    if element:
                        print(f"✓ Found username field: {selector}")
                        username_found = True
                        break
                except:
                    continue
            
            if not username_found:
                print("❌ Username field not found")
                # List all input fields
                inputs = await page.query_selector_all('input')
                print(f"   Found {len(inputs)} input fields:")
                for i, input_el in enumerate(inputs):
                    input_type = await input_el.get_attribute('type')
                    input_name = await input_el.get_attribute('name')
                    input_id = await input_el.get_attribute('id')
                    input_placeholder = await input_el.get_attribute('placeholder')
                    print(f"     {i+1}. type={input_type}, name={input_name}, id={input_id}, placeholder={input_placeholder}")
            
            # Check for password field
            password_found = False
            password_selectors = [
                f'#{password_field}',
                f'[name="{password_field}"]',
                'input[type="password"]',
                'input[placeholder*="password"]',
                'input[placeholder*="Password"]'
            ]
            
            for selector in password_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    if element:
                        print(f"✓ Found password field: {selector}")
                        password_found = True
                        break
                except:
                    continue
            
            if not password_found:
                print("❌ Password field not found")
            
            # Check for expected elements
            for element_name, selector in expected_elements.items():
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    if element:
                        print(f"✓ Found {element_name}: {selector}")
                    else:
                        print(f"❌ {element_name} not found: {selector}")
                except:
                    print(f"❌ {element_name} not found: {selector}")
            
            # Take screenshot
            screenshot_path = f"investigation_{journal_name.lower()}_{int(asyncio.get_event_loop().time())}.png"
            await page.screenshot(path=screenshot_path)
            print(f"📸 Screenshot saved: {screenshot_path}")
            
            # Check page source for clues
            content = await page.content()
            
            # Look for common login indicators
            login_indicators = [
                "username", "password", "email", "login", "signin", "sign in",
                "authentication", "credentials", "user", "account"
            ]
            
            found_indicators = []
            for indicator in login_indicators:
                if indicator.lower() in content.lower():
                    found_indicators.append(indicator)
            
            print(f"✓ Login indicators found: {', '.join(found_indicators)}")
            
            # Check for forms
            forms = await page.query_selector_all('form')
            print(f"✓ Found {len(forms)} forms on page")
            
            for i, form in enumerate(forms):
                action = await form.get_attribute('action')
                method = await form.get_attribute('method')
                print(f"     Form {i+1}: action={action}, method={method}")
                
                # Count inputs in this form
                form_inputs = await form.query_selector_all('input')
                print(f"       Contains {len(form_inputs)} inputs")
            
            return username_found and password_found
            
        except Exception as e:
            print(f"❌ Error investigating {journal_name}: {e}")
            return False
        finally:
            await browser.close()

async def main():
    """Main investigation function"""
    print("🔍 JOURNAL LOGIN PAGE INVESTIGATION")
    print("=" * 60)
    
    # Define journals to investigate
    journals = {
        "MAFE": {
            "url": "https://www2.cloud.editorialmanager.com/mafe/default2.aspx",
            "username_field": "username",
            "password_field": "passwordTextbox",
            "expected_elements": {
                "Login button": '[name="editorLogin"]',
                "Associate Editor text": 'text="Associate Editor"',
                "Dashboard elements": '.aries-accordion-item'
            }
        },
        "MF": {
            "url": "https://www2.cloud.editorialmanager.com/mf/default2.aspx",
            "username_field": "username",
            "password_field": "passwordTextbox",
            "expected_elements": {
                "Login button": '[name="editorLogin"]',
                "Associate Editor Center": 'text="Associate Editor Center"'
            }
        },
        "MOR": {
            "url": "https://www2.cloud.editorialmanager.com/mor/default2.aspx",
            "username_field": "username",
            "password_field": "passwordTextbox",
            "expected_elements": {
                "Login button": '[name="editorLogin"]',
                "Associate Editor Center": 'text="Associate Editor Center"'
            }
        },
        "NACO": {
            "url": "https://www2.cloud.editorialmanager.com/naco/default2.aspx",
            "username_field": "username",
            "password_field": "passwordTextbox",
            "expected_elements": {
                "Login button": '[name="editorLogin"]',
                "Mine link": 'text="Mine"'
            }
        },
        "SICON": {
            "url": "https://www2.cloud.editorialmanager.com/sicon/default2.aspx",
            "username_field": "username",
            "password_field": "passwordTextbox",
            "expected_elements": {
                "Login button": '[name="editorLogin"]'
            }
        },
        "SIFIN": {
            "url": "https://www2.cloud.editorialmanager.com/sifin/default2.aspx",
            "username_field": "username",
            "password_field": "passwordTextbox",
            "expected_elements": {
                "Login button": '[name="editorLogin"]'
            }
        }
    }
    
    results = {}
    
    for journal_name, config in journals.items():
        success = await investigate_journal(
            journal_name,
            config["url"],
            config["username_field"],
            config["password_field"],
            config["expected_elements"]
        )
        results[journal_name] = success
        await asyncio.sleep(2)  # Brief pause between investigations
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 INVESTIGATION SUMMARY")
    print("=" * 60)
    
    for journal_name, success in results.items():
        status = "✅ WORKING" if success else "❌ ISSUES"
        print(f"{journal_name}: {status}")
    
    working_count = sum(results.values())
    total_count = len(results)
    
    print(f"\nOverall: {working_count}/{total_count} journals have expected login elements")
    
    if working_count < total_count:
        print("\n🔧 RECOMMENDATIONS:")
        print("1. Check screenshots for actual page structure")
        print("2. Update field selectors based on investigation")
        print("3. Check if credentials are valid")
        print("4. Verify if website structure has changed")

if __name__ == "__main__":
    asyncio.run(main())