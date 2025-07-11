#!/usr/bin/env python3
"""
Analyze SICON login page to find actual ORCID login elements
"""

import asyncio
import json
from playwright.async_api import async_playwright
import time

class SICONAnalyzer:
    def __init__(self):
        self.base_url = "https://sicon.siam.org/cgi-bin/main.plex"
        
    async def analyze_page(self):
        """Analyze the SICON login page structure"""
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
                await page.screenshot(path="sicon_initial.png")
                print("Screenshot saved: sicon_initial.png")
                
                # Analyze page structure
                title = await page.title()
                print(f"Page title: {title}")
                
                # Look for all buttons and links
                buttons = await page.query_selector_all('button, input[type="button"], input[type="submit"], a')
                print(f"Found {len(buttons)} buttons/links")
                
                button_info = []
                for i, btn in enumerate(buttons):
                    try:
                        text = await btn.text_content()
                        href = await btn.get_attribute('href')
                        onclick = await btn.get_attribute('onclick')
                        class_name = await btn.get_attribute('class')
                        id_attr = await btn.get_attribute('id')
                        
                        if text or href:
                            button_info.append({
                                'index': i,
                                'text': text,
                                'href': href,
                                'onclick': onclick,
                                'class': class_name,
                                'id': id_attr
                            })
                            
                            # Check if this looks like an ORCID login button
                            if text and ('orcid' in text.lower() or 'login' in text.lower() or 'sign in' in text.lower()):
                                print(f"POTENTIAL ORCID LOGIN BUTTON {i}: {text}")
                                print(f"  href: {href}")
                                print(f"  onclick: {onclick}")
                                print(f"  class: {class_name}")
                                print(f"  id: {id_attr}")
                                
                    except Exception as e:
                        print(f"Error analyzing button {i}: {e}")
                
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
                
                # Check for iframes
                iframes = await page.query_selector_all('iframe')
                print(f"Found {len(iframes)} iframes")
                
                for i, iframe in enumerate(iframes):
                    try:
                        src = await iframe.get_attribute('src')
                        print(f"IFRAME {i}: {src}")
                    except Exception as e:
                        print(f"Error analyzing iframe {i}: {e}")
                
                # Look for forms
                forms = await page.query_selector_all('form')
                print(f"Found {len(forms)} forms")
                
                for i, form in enumerate(forms):
                    try:
                        action = await form.get_attribute('action')
                        method = await form.get_attribute('method')
                        print(f"FORM {i}: action={action}, method={method}")
                        
                        # Find inputs in this form
                        inputs = await form.query_selector_all('input')
                        for j, inp in enumerate(inputs):
                            inp_type = await inp.get_attribute('type')
                            inp_name = await inp.get_attribute('name')
                            inp_value = await inp.get_attribute('value')
                            print(f"  INPUT {j}: type={inp_type}, name={inp_name}, value={inp_value}")
                            
                    except Exception as e:
                        print(f"Error analyzing form {i}: {e}")
                
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
                                await page.screenshot(path="sicon_after_orcid_click.png")
                                print("Screenshot saved: sicon_after_orcid_click.png")
                                
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
                await page.screenshot(path="sicon_error.png")
                
            finally:
                await browser.close()

async def main():
    analyzer = SICONAnalyzer()
    await analyzer.analyze_page()

if __name__ == "__main__":
    asyncio.run(main())