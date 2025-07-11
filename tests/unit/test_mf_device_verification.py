#!/usr/bin/env python3
"""
Test MF device verification fix
"""

from journals.mf import MFJournal
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

def test_mf_device_verification():
    """Test MF with enhanced device verification"""
    print("🔍 Testing MF Device Verification Fix")
    
    # Setup Chrome with options
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("1. Setting up MF journal...")
        mf = MFJournal(driver)
        
        print("2. Attempting login with device verification...")
        mf.login()
        
        print("3. Waiting for page to load after verification...")
        time.sleep(5)
        
        # Check current URL
        current_url = driver.current_url
        print(f"4. Current URL: {current_url}")
        
        # Check if we're still on unrecognized device page
        if "UNRECOGNIZED_DEVICE" in driver.page_source:
            print("❌ Still on UNRECOGNIZED_DEVICE page")
            # Save page for debugging
            with open("mf_device_verification_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        else:
            print("✅ Successfully passed device verification!")
            
        # Try to find Associate Editor Center
        print("5. Looking for Associate Editor Center...")
        mf.scrape_manuscripts_and_emails()
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        
        # Save debug info
        try:
            with open("mf_device_error_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            driver.save_screenshot("mf_device_error.png")
        except:
            pass
    
    finally:
        driver.quit()

if __name__ == "__main__":
    test_mf_device_verification()