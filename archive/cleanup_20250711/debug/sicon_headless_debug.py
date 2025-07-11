#!/usr/bin/env python3
"""
SICON Headless Debug - Check what's happening in headless mode
"""

import os
import time
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

load_dotenv()


def test_headless():
    """Test headless mode with debugging."""
    output_dir = Path(f'./sicon_headless_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    output_dir.mkdir(exist_ok=True)
    
    chrome_options = Options()
    
    # HEADLESS MODE with debugging
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Enable logging
    chrome_options.add_argument('--enable-logging')
    chrome_options.add_argument('--v=1')
    
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)
    
    try:
        print("🔍 Testing headless mode...")
        
        # Try to load SICON
        print("\n1. Loading SICON homepage...")
        driver.get("http://sicon.siam.org")
        time.sleep(5)
        
        # Save screenshot
        screenshot_path = output_dir / "initial_page.png"
        driver.save_screenshot(str(screenshot_path))
        print(f"   📸 Screenshot saved: {screenshot_path}")
        
        # Save page source
        page_source_path = output_dir / "initial_page.html"
        with open(page_source_path, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print(f"   📄 Page source saved: {page_source_path}")
        
        # Check page content
        print(f"   📏 Page title: {driver.title}")
        print(f"   📏 Page URL: {driver.current_url}")
        
        # Look for key elements
        print("\n2. Looking for key elements...")
        
        # Check for privacy notification
        try:
            privacy_button = driver.find_element(By.XPATH, "//input[@value='Continue']")
            print("   ✅ Found privacy notification")
            privacy_button.click()
            time.sleep(3)
            
            # Save screenshot after privacy
            screenshot_path2 = output_dir / "after_privacy.png"
            driver.save_screenshot(str(screenshot_path2))
            print(f"   📸 Screenshot after privacy: {screenshot_path2}")
        except:
            print("   ℹ️  No privacy notification found")
        
        # Look for ORCID link with different patterns
        orcid_patterns = [
            "//a[contains(@href, 'orcid')]",
            "//a[contains(text(), 'ORCID')]",
            "//a[contains(text(), 'Sign in')]",
            "//a[contains(@class, 'orcid')]",
            "//img[contains(@src, 'orcid')]/..",
            "//button[contains(text(), 'ORCID')]"
        ]
        
        found_orcid = False
        for pattern in orcid_patterns:
            try:
                elements = driver.find_elements(By.XPATH, pattern)
                if elements:
                    print(f"   ✅ Found ORCID element with pattern: {pattern}")
                    print(f"      Text: {elements[0].text}")
                    print(f"      Href: {elements[0].get_attribute('href')}")
                    found_orcid = True
                    break
            except:
                continue
        
        if not found_orcid:
            print("   ❌ No ORCID link found")
            
            # Save final page state
            final_source_path = output_dir / "final_page.html"
            with open(final_source_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print(f"   📄 Final page source saved: {final_source_path}")
            
            # List all links on page
            print("\n3. All links on page:")
            all_links = driver.find_elements(By.TAG_NAME, 'a')
            for i, link in enumerate(all_links[:10]):  # First 10 links
                href = link.get_attribute('href')
                text = link.text.strip()
                if href or text:
                    print(f"   Link {i}: '{text}' -> {href}")
        
        print("\n✅ Debug complete. Check output directory for details.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        # Save error screenshot
        error_screenshot = output_dir / "error_screenshot.png"
        driver.save_screenshot(str(error_screenshot))
        print(f"📸 Error screenshot saved: {error_screenshot}")
    
    finally:
        driver.quit()
        print(f"\n📁 Debug files saved to: {output_dir}")


if __name__ == "__main__":
    test_headless()