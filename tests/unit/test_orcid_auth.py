#!/usr/bin/env python3
"""
Simple ORCID Authentication Test

This script tests just the ORCID authentication without trying to extract data.
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def test_orcid_auth():
    """Test ORCID authentication step by step."""
    print("🧪 Testing ORCID Authentication")
    
    # Get credentials
    orcid_user = os.getenv("ORCID_USER")
    orcid_pass = os.getenv("ORCID_PASS")
    
    if not orcid_user or not orcid_pass:
        print("❌ ORCID credentials not found")
        return False
    
    print(f"✅ Credentials available: {orcid_user}")
    
    # Setup browser
    chrome_options = Options()
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 15)
    
    try:
        print("\n1️⃣ Navigating to SICON...")
        driver.get("http://sicon.siam.org")
        time.sleep(3)
        
        print("2️⃣ Looking for ORCID login link...")
        orcid_link = driver.find_element(By.XPATH, "//a[contains(@href, 'orcid')]")
        print(f"   Found: {orcid_link.get_attribute('href')}")
        
        print("3️⃣ Clicking ORCID link...")
        orcid_link.click()
        time.sleep(3)
        
        print("4️⃣ Waiting for ORCID page...")
        wait.until(lambda driver: 'orcid.org' in driver.current_url)
        print(f"   Current URL: {driver.current_url}")
        
        print("5️⃣ Looking for username field...")
        
        # Try to find the username field with various methods
        username_field = None
        selectors = [
            "#username", "#userId", "#user-id", 
            "input[name='userId']", "input[name='username']",
            "input[type='text']", "input[type='email']"
        ]
        
        for selector in selectors:
            try:
                username_field = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                print(f"   ✅ Found username field: {selector}")
                break
            except:
                continue
        
        if not username_field:
            print("   ❌ No username field found")
            return False
        
        print("6️⃣ Filling username...")
        username_field.clear()
        username_field.send_keys(orcid_user)
        
        print("7️⃣ Looking for password field...")
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_field.clear()
        password_field.send_keys(orcid_pass)
        
        print("8️⃣ Looking for submit button...")
        submit_button = None
        submit_selectors = [
            "#signin-button", "button[type='submit']", 
            "input[type='submit']", "button:contains('Sign in')"
        ]
        
        for selector in submit_selectors:
            try:
                submit_button = driver.find_element(By.CSS_SELECTOR, selector)
                break
            except:
                continue
        
        if not submit_button:
            # Try XPath for text-based search
            try:
                submit_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Sign in') or contains(text(), 'SIGN IN')]")
            except:
                print("   ❌ No submit button found")
                return False
        
        print("9️⃣ Submitting form...")
        submit_button.click()
        time.sleep(5)
        
        print("🔟 Checking for redirect...")
        start_time = time.time()
        while time.time() - start_time < 30:
            current_url = driver.current_url
            print(f"   Current URL: {current_url}")
            
            if 'sicon.siam.org' in current_url:
                print("   ✅ Successfully redirected back to SICON!")
                
                # Check if we're logged in
                page_source = driver.page_source.lower()
                if 'logout' in page_source or 'associate editor' in page_source:
                    print("   ✅ Login appears successful!")
                    return True
                else:
                    print("   ⚠️ Redirected but login status unclear")
                    
            time.sleep(2)
        
        print("   ❌ Timeout waiting for redirect")
        return False
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        driver.quit()


if __name__ == "__main__":
    success = test_orcid_auth()
    if success:
        print("\n✅ ORCID authentication test successful!")
    else:
        print("\n❌ ORCID authentication test failed!")