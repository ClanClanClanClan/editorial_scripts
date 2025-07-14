#!/usr/bin/env python3
"""
Test Cloudflare bypass with proper waiting
"""

import asyncio
from playwright.async_api import async_playwright

async def test_cloudflare_bypass():
    """Test bypassing Cloudflare on SIFIN"""
    print("Starting Cloudflare bypass test...")
    
    async with async_playwright() as p:
        # Launch browser in headless mode
        browser = await p.firefox.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Add stealth script
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = await context.new_page()
        
        try:
            print("Navigating to SIFIN...")
            await page.goto("https://sifin.siam.org/cgi-bin/main.plex", timeout=120000)
            
            # Check for Cloudflare
            print("Checking for Cloudflare challenge...")
            content = await page.content()
            
            if "Verifying you are human" in content or "cloudflare" in content.lower():
                print("🛡️ Cloudflare detected! Waiting 60 seconds...")
                
                # Wait for Cloudflare to complete
                try:
                    await page.wait_for_function(
                        """() => {
                            return !document.body.textContent.includes('Verifying you are human') &&
                                   !document.body.textContent.includes('Checking your browser');
                        }""",
                        timeout=65000  # 65 seconds
                    )
                    print("✅ Cloudflare challenge completed!")
                except:
                    print("⏱️ Cloudflare timeout - checking page state...")
                    
                # Additional wait for page to stabilize
                await page.wait_for_timeout(5000)
            
            # Check if we're on the actual SIFIN page now
            content = await page.content()
            if "ORCID" in content:
                print("✅ Successfully reached SIFIN login page!")
                print("🔍 Looking for ORCID login...")
                
                # Look for ORCID elements
                orcid_found = False
                selectors = [
                    'img[alt*="ORCID"]',
                    'a[href*="orcid.org"]',
                    'button:has-text("ORCID")',
                    '*:has-text("Sign in with ORCID")'
                ]
                
                for selector in selectors:
                    element = await page.query_selector(selector)
                    if element:
                        print(f"✅ Found ORCID element with selector: {selector}")
                        orcid_found = True
                        break
                
                if not orcid_found:
                    print("❌ No ORCID login found")
            else:
                print(f"❌ Did not reach SIFIN page. Current title: {await page.title()}")
            
            # Save screenshot
            await page.screenshot(path="cloudflare_bypass_result.png")
            print("📸 Screenshot saved: cloudflare_bypass_result.png")
            
        except Exception as e:
            print(f"Error: {e}")
            await page.screenshot(path="cloudflare_bypass_error.png")
            
        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_cloudflare_bypass())