#!/usr/bin/env python3
"""
Analyze SIFIN login page to find actual ORCID login elements
"""

import asyncio
import json
from playwright.async_api import async_playwright
import time

class SIFINAnalyzer:
    def __init__(self):
        self.base_url = "https://sifin.siam.org/cgi-bin/main.plex"
        
    async def analyze_page(self):
        """Analyze the SIFIN login page structure"""
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
                
                # Handle cookie policy layer
                try:
                    await page.evaluate("""
                        for(let sel of [
                            '#cookie-policy-layer-bg',
                            '.cc_banner-wrapper',
                            '#cookie-policy-layer',
                            '#onetrust-banner-sdk',
                            '.onetrust-pc-dark-filter'
                        ]) {
                            let el = document.querySelector(sel);
                            if(el) el.style.display='none';
                        }
                    """)
                    print("Cookie policy layer hidden")
                except Exception as e:
                    print(f"Error hiding cookie layer: {e}")
                
                await asyncio.sleep(1)
                
                # Take screenshot
                await page.screenshot(path="sifin_initial.png")
                print("Screenshot saved: sifin_initial.png")
                
                # Analyze page structure
                title = await page.title()
                print(f"Page title: {title}")
                
                # Look for ORCID-specific elements
                orcid_elements = await page.query_selector_all('[id*="orcid"], [class*="orcid"], [href*="orcid"]')
                print(f"Found {len(orcid_elements)} ORCID-related elements")
                
                for i, elem in enumerate(orcid_elements):
                    try:
                        tag = await elem.evaluate('el => el.tagName')
                        text = await elem.text_content()
                        href = await elem.get_attribute('href')
                        class_name = await elem.get_attribute('class')
                        id_attr = await elem.get_attribute('id')
                        
                        print(f"ORCID ELEMENT {i}: {tag}")
                        print(f"  text: {text}")
                        print(f"  href: {href}")
                        print(f"  class: {class_name}")
                        print(f"  id: {id_attr}")
                        
                    except Exception as e:
                        print(f"Error analyzing ORCID element {i}: {e}")
                
                # Try to find and click ORCID login if it exists
                orcid_login_selectors = [
                    'a[href*="orcid"]',
                    'button:has-text("ORCID")',
                    'input[value*="ORCID"]',
                    'a:has-text("ORCID")',
                    'button:has-text("Sign in with ORCID")',
                    'a:has-text("Sign in with ORCID")'
                ]
                
                for selector in orcid_login_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            print(f"FOUND ORCID LOGIN with selector: {selector}")
                            text = await element.text_content()
                            href = await element.get_attribute('href')
                            print(f"  Text: {text}")
                            print(f"  Href: {href}")
                            
                            # Try to click it
                            await element.click()
                            await asyncio.sleep(3)
                            
                            # Check if we're on a new page
                            new_url = page.url
                            if new_url != self.base_url:
                                print(f"Navigation successful to: {new_url}")
                                await page.screenshot(path="sifin_after_orcid_click.png")
                                print("Screenshot saved: sifin_after_orcid_click.png")
                                
                                # Analyze ORCID login form
                                username_inputs = await page.query_selector_all('input[type="text"], input[type="email"], input[name*="user"], input[id*="user"]')
                                password_inputs = await page.query_selector_all('input[type="password"], input[name*="pass"], input[id*="pass"]')
                                
                                print(f"Found {len(username_inputs)} username inputs and {len(password_inputs)} password inputs")
                                
                                for i, inp in enumerate(username_inputs):
                                    name = await inp.get_attribute('name')
                                    id_attr = await inp.get_attribute('id')
                                    placeholder = await inp.get_attribute('placeholder')
                                    print(f"USERNAME INPUT {i}: name={name}, id={id_attr}, placeholder={placeholder}")
                                
                                for i, inp in enumerate(password_inputs):
                                    name = await inp.get_attribute('name')
                                    id_attr = await inp.get_attribute('id')
                                    placeholder = await inp.get_attribute('placeholder')
                                    print(f"PASSWORD INPUT {i}: name={name}, id={id_attr}, placeholder={placeholder}")
                                
                                # Look for submit button
                                submit_buttons = await page.query_selector_all('button[type="submit"], input[type="submit"], button:has-text("Sign in"), button:has-text("Login")')
                                print(f"Found {len(submit_buttons)} submit buttons")
                                
                                for i, btn in enumerate(submit_buttons):
                                    text = await btn.text_content()
                                    value = await btn.get_attribute('value')
                                    print(f"SUBMIT BUTTON {i}: text={text}, value={value}")
                            
                            break
                            
                    except Exception as e:
                        print(f"Error trying selector {selector}: {e}")
                
                # Wait a bit more for any dynamic content
                await asyncio.sleep(5)
                
            except Exception as e:
                print(f"Error analyzing page: {e}")
                await page.screenshot(path="sifin_error.png")
                
            finally:
                await browser.close()

async def main():
    analyzer = SIFINAnalyzer()
    await analyzer.analyze_page()

if __name__ == "__main__":
    asyncio.run(main())