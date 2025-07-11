#!/usr/bin/env python3
"""
Analyze MF journal to find the Associate Editor Center
"""

import asyncio
from playwright.async_api import async_playwright
from core.credential_manager import get_credential_manager
import time

class MFAnalyzer:
    def __init__(self):
        self.base_url = "https://mc.manuscriptcentral.com/mafi"
        
        # Get credentials from environment variables (like original code)
        import os
        self.username = os.getenv("MF_USERNAME") or os.getenv("MF_USER")
        self.password = os.getenv("MF_PASSWORD") or os.getenv("MF_PASS")
        
        if not self.username or not self.password:
            print("MF credentials not found in environment variables")
            # Try credential manager as fallback
            try:
                cred_manager = get_credential_manager()
                mf_creds = cred_manager.get_journal_credentials("MF")
                self.username = mf_creds.get('username')
                self.password = mf_creds.get('password')
            except:
                pass
            
            if not self.username or not self.password:
                print("Using dummy credentials for analysis")
        
    async def analyze_page(self):
        """Analyze the MF journal page to find Associate Editor Center"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                print(f"Navigating to: {self.base_url}")
                await page.goto(self.base_url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(3)
                
                # Take screenshot
                await page.screenshot(path="mf_initial.png")
                print("Screenshot saved: mf_initial.png")
                
                # Try to login
                print("Attempting login...")
                
                # Find login fields
                username_field = await page.query_selector('#username')
                password_field = await page.query_selector('#password')
                
                if username_field and password_field and self.username and self.password:
                    await username_field.fill(self.username)
                    await password_field.fill(self.password)
                    
                    # Find submit button
                    submit_btn = await page.query_selector('input[type="submit"]')
                    if submit_btn:
                        await submit_btn.click()
                        await asyncio.sleep(5)
                        
                        print("Login attempted, taking screenshot...")
                        await page.screenshot(path="mf_after_login.png")
                        print("Screenshot saved: mf_after_login.png")
                        
                        # Look for Associate Editor related elements
                        print("Looking for Associate Editor elements...")
                        
                        # Search for all links and buttons
                        all_links = await page.query_selector_all('a')
                        all_buttons = await page.query_selector_all('button')
                        
                        ae_elements = []
                        
                        for link in all_links:
                            text = await link.text_content()
                            href = await link.get_attribute('href')
                            
                            if text and ('associate' in text.lower() or 'editor' in text.lower() or 'ae' in text.lower()):
                                ae_elements.append({
                                    'type': 'link',
                                    'text': text,
                                    'href': href
                                })
                        
                        for button in all_buttons:
                            text = await button.text_content()
                            
                            if text and ('associate' in text.lower() or 'editor' in text.lower() or 'ae' in text.lower()):
                                ae_elements.append({
                                    'type': 'button',
                                    'text': text,
                                    'href': None
                                })
                        
                        print(f"Found {len(ae_elements)} Associate Editor related elements:")
                        for i, elem in enumerate(ae_elements):
                            print(f"  {i+1}. {elem['type']}: {elem['text']} -> {elem['href']}")
                        
                        # Look for navigation menus
                        print("\nLooking for navigation menus...")
                        nav_elements = await page.query_selector_all('nav, .nav, .navigation, .menu')
                        
                        for i, nav in enumerate(nav_elements):
                            nav_text = await nav.text_content()
                            if nav_text and len(nav_text) > 10:
                                print(f"NAV {i+1}: {nav_text[:200]}...")
                        
                        # Look for table rows or list items
                        print("\nLooking for table structure...")
                        tables = await page.query_selector_all('table')
                        
                        for i, table in enumerate(tables):
                            rows = await table.query_selector_all('tr')
                            if len(rows) > 0:
                                print(f"TABLE {i+1}: {len(rows)} rows")
                                
                                # Check first few rows for AE content
                                for j, row in enumerate(rows[:5]):
                                    row_text = await row.text_content()
                                    if row_text and ('associate' in row_text.lower() or 'editor' in row_text.lower()):
                                        print(f"  Row {j+1}: {row_text}")
                        
                        # Look for dropdown menus
                        print("\nLooking for dropdown menus...")
                        selects = await page.query_selector_all('select')
                        
                        for i, select in enumerate(selects):
                            options = await select.query_selector_all('option')
                            for option in options:
                                option_text = await option.text_content()
                                if option_text and ('associate' in option_text.lower() or 'editor' in option_text.lower()):
                                    print(f"SELECT {i+1} OPTION: {option_text}")
                        
                        # Look for iframe elements
                        print("\nLooking for iframes...")
                        iframes = await page.query_selector_all('iframe')
                        
                        for i, iframe in enumerate(iframes):
                            src = await iframe.get_attribute('src')
                            print(f"IFRAME {i+1}: {src}")
                
                # Wait for manual inspection
                print("\nWaiting for manual inspection...")
                await asyncio.sleep(30)
                
            except Exception as e:
                print(f"Error analyzing page: {e}")
                await page.screenshot(path="mf_error.png")
                
            finally:
                await browser.close()

async def main():
    analyzer = MFAnalyzer()
    await analyzer.analyze_page()

if __name__ == "__main__":
    asyncio.run(main())