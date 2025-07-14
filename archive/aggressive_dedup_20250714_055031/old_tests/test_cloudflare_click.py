#!/usr/bin/env python3
"""
Test Cloudflare bypass by clicking the checkbox
"""

import asyncio
from playwright.async_api import async_playwright

async def test_cloudflare_click():
    """Test clicking Cloudflare checkbox"""
    print("Starting Cloudflare click test...")
    
    async with async_playwright() as p:
        # Launch browser in headful mode to see what happens
        browser = await p.firefox.launch(
            headless=False,  # Run headful to see the process
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
            
            # Wait a bit for page to load
            await page.wait_for_timeout(3000)
            
            # Check for Cloudflare
            print("Checking for Cloudflare challenge...")
            content = await page.content()
            
            if "Verify you are human" in content:
                print("🛡️ Cloudflare detected! Looking for checkbox...")
                
                # Try to find and click the checkbox
                checkbox_selectors = [
                    'input[type="checkbox"]',
                    '#checkbox',
                    '.ctp-checkbox-label',
                    'label:has-text("Verify you are human")',
                    'div:has-text("Verify you are human")'
                ]
                
                clicked = False
                for selector in checkbox_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=5000)
                        if element:
                            print(f"Found element with selector: {selector}")
                            await element.click()
                            print("✅ Clicked verification checkbox!")
                            clicked = True
                            break
                    except:
                        continue
                
                if not clicked:
                    print("❌ Could not find checkbox to click")
                    # Try to click anywhere on the challenge box
                    try:
                        await page.click('text="Verify you are human"')
                        print("✅ Clicked on text instead")
                    except:
                        print("❌ Could not click anywhere")
                
                # Wait for challenge to complete
                print("⏳ Waiting for verification to complete...")
                await page.wait_for_timeout(10000)  # Wait 10 seconds
                
                # Check if we passed
                content = await page.content()
                if "ORCID" in content and "Verify you are human" not in content:
                    print("✅ Successfully passed Cloudflare!")
                else:
                    print("❌ Still on Cloudflare page")
            
            # Final screenshot
            await page.screenshot(path="cloudflare_click_result.png")
            print("📸 Screenshot saved: cloudflare_click_result.png")
            
            # Keep browser open for manual inspection
            print("\n🔍 Browser will stay open for 30 seconds for inspection...")
            await page.wait_for_timeout(30000)
            
        except Exception as e:
            print(f"Error: {e}")
            
        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_cloudflare_click())