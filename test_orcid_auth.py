#!/usr/bin/env python3
"""
Test ORCID authentication with detailed debugging
"""

import time
import logging
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
project_root = Path(__file__).parent
load_dotenv(project_root / ".env.production")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_orcid_auth():
    """Test ORCID authentication step by step."""
    
    orcid_email = os.getenv("ORCID_EMAIL")
    orcid_password = os.getenv("ORCID_PASSWORD")
    
    if not orcid_email or not orcid_password:
        print("❌ ORCID credentials not found in environment variables")
        return False
    
    driver = None
    try:
        # Create driver
        print("🚀 Creating Chrome driver...")
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.keys import Keys
        
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        
        # Navigate to SICON
        print("🌐 Navigating to SICON...")
        driver.get("https://sicon.siam.org/cgi-bin/main.plex")
        time.sleep(3)
        
        # Find and click ORCID login
        print("🔍 Looking for ORCID login...")
        orcid_link = driver.find_element(By.CSS_SELECTOR, "a[href*='orcid']")
        print(f"✅ Found ORCID link: {orcid_link.get_attribute('href')}")
        
        orcid_link.click()
        print("🖱️ Clicked ORCID login")
        time.sleep(5)
        
        # Check current URL
        current_url = driver.current_url
        print(f"📍 Current URL: {current_url}")
        
        if "orcid.org" not in current_url:
            print("❌ Not redirected to ORCID")
            return False
        
        # Handle cookie banner
        print("🍪 Handling cookie banner...")
        cookie_selectors = [
            "button[id*='accept']",
            "button[class*='accept']",
            ".cookie-accept",
            "#cookieAccept"
        ]
        
        cookie_handled = False
        for selector in cookie_selectors:
            try:
                cookie_btn = driver.find_element(By.CSS_SELECTOR, selector)
                cookie_btn.click()
                print(f"✅ Cookie banner handled: {selector}")
                cookie_handled = True
                time.sleep(2)
                break
            except:
                continue
        
        if not cookie_handled:
            print("ℹ️ No cookie banner found")
        
        # Find and fill email field
        print("📧 Looking for email field...")
        wait = WebDriverWait(driver, 15)
        
        email_selectors = ["#username", "input[name='username']", "#email", "input[type='email']"]
        email_field = None
        
        for selector in email_selectors:
            try:
                email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                print(f"✅ Found email field: {selector}")
                break
            except:
                continue
        
        if not email_field:
            print("❌ Email field not found")
            print("🔍 Available input fields:")
            inputs = driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                print(f"  - {inp.get_attribute('type')} | {inp.get_attribute('name')} | {inp.get_attribute('id')}")
            return False
        
        # Fill email
        print("✍️ Filling email field...")
        email_field.clear()
        email_field.send_keys(orcid_email)
        print("✅ Email entered")
        
        # Find and fill password field
        print("🔒 Looking for password field...")
        password_selectors = ["#password", "input[name='password']", "input[type='password']"]
        password_field = None
        
        for selector in password_selectors:
            try:
                password_field = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"✅ Found password field: {selector}")
                break
            except:
                continue
        
        if not password_field:
            print("❌ Password field not found")
            return False
        
        # Fill password
        print("✍️ Filling password field...")
        password_field.clear()
        password_field.send_keys(orcid_password)
        print("✅ Password entered")
        
        # Submit form
        print("🚀 Submitting form...")
        submit_selectors = [
            "#signin-button",
            "button[type='submit']",
            "input[type='submit']",
            ".btn-primary"
        ]
        
        submitted = False
        for selector in submit_selectors:
            try:
                submit_btn = driver.find_element(By.CSS_SELECTOR, selector)
                submit_btn.click()
                print(f"✅ Form submitted: {selector}")
                submitted = True
                break
            except:
                continue
        
        if not submitted:
            # Try Enter key
            password_field.send_keys(Keys.RETURN)
            print("✅ Form submitted via Enter key")
        
        # Wait for response
        print("⏳ Waiting for authentication response...")
        time.sleep(10)
        
        final_url = driver.current_url
        print(f"📍 Final URL: {final_url}")
        
        if "sicon.siam.org" in final_url:
            print("🎉 Successfully authenticated and returned to SICON!")
            return True
        elif "authorize" in final_url:
            print("🔓 Need to authorize access...")
            # Handle authorization
            auth_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            auth_btn.click()
            time.sleep(5)
            
            final_final_url = driver.current_url
            print(f"📍 Final final URL: {final_final_url}")
            
            if "sicon.siam.org" in final_final_url:
                print("🎉 Successfully authorized and returned to SICON!")
                return True
        
        page_source = driver.page_source
        if "dashboard" in page_source.lower() or "manuscripts" in page_source.lower():
            print("🎉 Authentication successful - found dashboard content!")
            return True
        
        print("❌ Authentication status unclear")
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if driver:
            print("🔧 Keeping browser open for manual inspection...")
            print("Press Enter to close browser...")
            input()
            driver.quit()

if __name__ == "__main__":
    success = test_orcid_auth()
    print(f"\n{'='*50}")
    print(f"Authentication test: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"{'='*50}")