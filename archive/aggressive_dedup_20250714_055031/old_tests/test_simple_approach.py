#!/usr/bin/env python3
"""
Test multiple approaches to SIAM access
1. Simple Playwright (no stealth)
2. Selenium 
3. Non-headless mode
"""

import asyncio
import subprocess
import os
from pathlib import Path

# Get credentials
def get_creds():
    userId_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=userId'], 
                               capture_output=True, text=True)
    password_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=password'], 
                                 capture_output=True, text=True)
    return userId_cmd.stdout.strip(), password_cmd.stdout.strip()

email, password = get_creds()
print(f"✅ Credentials: {email[:3]}****")

async def test_simple_playwright():
    """Test with simple Playwright - no stealth measures"""
    print("\n🧪 TEST 1: Simple Playwright (No Stealth)")
    print("=" * 50)
    
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        # Use a regular Chrome browser with minimal config
        browser = await p.chromium.launch(
            headless=False,  # Non-headless 
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        # Simple context - no fancy stealth
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        try:
            print("📍 Navigating to SICON...")
            response = await page.goto("http://sicon.siam.org/cgi-bin/main.plex", timeout=30000)
            print(f"   Status: {response.status}")
            print(f"   URL: {page.url}")
            
            # Wait a bit for any redirects
            await page.wait_for_timeout(5000)
            
            # Take screenshot
            await page.screenshot(path="test1_simple_playwright.png")
            print("   📸 Screenshot: test1_simple_playwright.png")
            
            # Check page content
            content = await page.content()
            if "cloudflare" in content.lower() or "verifying you are human" in content.lower():
                print("   ❌ Still getting Cloudflare challenge")
            elif "orcid" in content.lower() or "login" in content.lower():
                print("   ✅ Looks like login page!")
            else:
                print("   ⚠️ Unknown page content")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        await browser.close()

def test_selenium():
    """Test with Selenium WebDriver"""
    print("\n🧪 TEST 2: Selenium WebDriver")
    print("=" * 50)
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        
        # Chrome options for Selenium
        chrome_options = Options()
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Create driver
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        try:
            print("📍 Navigating to SICON...")
            driver.get("http://sicon.siam.org/cgi-bin/main.plex")
            
            # Wait for page load
            time.sleep(5)
            
            print(f"   URL: {driver.current_url}")
            
            # Take screenshot
            driver.save_screenshot("test2_selenium.png")
            print("   📸 Screenshot: test2_selenium.png")
            
            # Check page content
            page_source = driver.page_source
            if "cloudflare" in page_source.lower() or "verifying you are human" in page_source.lower():
                print("   ❌ Still getting Cloudflare challenge")
            elif "orcid" in page_source.lower() or "login" in page_source.lower():
                print("   ✅ Looks like login page!")
            else:
                print("   ⚠️ Unknown page content")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        finally:
            driver.quit()
            
    except ImportError:
        print("   ❌ Selenium not installed")
        print("   💡 Install with: pip install selenium")
    except Exception as e:
        print(f"   ❌ Selenium error: {e}")

async def test_firefox():
    """Test with Firefox instead of Chrome"""
    print("\n🧪 TEST 3: Firefox Browser")
    print("=" * 50)
    
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        try:
            browser = await p.firefox.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            
            print("📍 Navigating to SICON with Firefox...")
            response = await page.goto("http://sicon.siam.org/cgi-bin/main.plex", timeout=30000)
            print(f"   Status: {response.status}")
            
            await page.wait_for_timeout(5000)
            
            # Take screenshot
            await page.screenshot(path="test3_firefox.png")
            print("   📸 Screenshot: test3_firefox.png")
            
            # Check page content
            content = await page.content()
            if "cloudflare" in content.lower() or "verifying you are human" in content.lower():
                print("   ❌ Still getting Cloudflare challenge")
            elif "orcid" in content.lower() or "login" in content.lower():
                print("   ✅ Looks like login page!")
            else:
                print("   ⚠️ Unknown page content")
                
            await browser.close()
            
        except Exception as e:
            print(f"   ❌ Firefox error: {e}")

async def test_wait_longer():
    """Test waiting longer for Cloudflare to clear"""
    print("\n🧪 TEST 4: Wait for Cloudflare Challenge")
    print("=" * 50)
    
    from playwright.async_api import async_playwright
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print("📍 Navigating to SICON...")
            await page.goto("http://sicon.siam.org/cgi-bin/main.plex")
            
            print("⏳ Waiting up to 60 seconds for Cloudflare challenge...")
            
            # Wait for either login page or timeout
            try:
                await page.wait_for_function(
                    """() => {
                        const content = document.body.innerText.toLowerCase();
                        return content.includes('login') || 
                               content.includes('orcid') || 
                               content.includes('sign in');
                    }""",
                    timeout=60000
                )
                print("   ✅ Challenge cleared! Login page detected")
                
                # Take screenshot of success
                await page.screenshot(path="test4_after_challenge.png")
                print("   📸 Screenshot: test4_after_challenge.png")
                
            except:
                print("   ❌ Timeout - challenge didn't clear")
                await page.screenshot(path="test4_timeout.png")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        await browser.close()

async def main():
    """Run all tests"""
    print("🔧 SIAM ACCESS TROUBLESHOOTING")
    print("=" * 80)
    print("Testing multiple approaches to bypass detection...")
    
    # Test 1: Simple Playwright
    await test_simple_playwright()
    
    # Test 2: Selenium
    test_selenium()
    
    # Test 3: Firefox
    await test_firefox()
    
    # Test 4: Wait for challenge
    await test_wait_longer()
    
    print("\n" + "=" * 80)
    print("📊 RESULTS SUMMARY")
    print("=" * 80)
    print("Check the screenshots to see which approach worked:")
    print("1. test1_simple_playwright.png")
    print("2. test2_selenium.png") 
    print("3. test3_firefox.png")
    print("4. test4_after_challenge.png")
    print("\nIf any show the login page instead of Cloudflare,")
    print("we'll use that approach for the scraper!")

if __name__ == "__main__":
    asyncio.run(main())