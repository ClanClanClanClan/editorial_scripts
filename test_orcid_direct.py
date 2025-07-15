#!/usr/bin/env python3
"""
Test ORCID Authentication Directly

This script tests ORCID authentication in visible mode to debug the form submission issue.
"""

import sys
import os
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(project_root / ".env.production")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_orcid_direct():
    """Test ORCID authentication directly."""
    credentials = {
        'username': os.getenv('ORCID_EMAIL'),
        'password': os.getenv('ORCID_PASSWORD')
    }
    
    if not all(credentials.values()):
        raise ValueError("Missing ORCID credentials")
    
    print("🔐 Testing ORCID Authentication")
    print("=" * 50)
    print(f"Username: {credentials['username']}")
    print(f"Password: {'*' * len(credentials['password'])}")
    print()
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        # Create visible browser for debugging
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1200,800")
        
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(10)
        
        print("✅ Browser created (visible mode)")
        
        # Navigate to SICON
        print("📍 Navigating to SICON...")
        driver.get("https://sicon.siam.org/cgi-bin/main.plex")
        time.sleep(3)
        
        print(f"✅ SICON loaded: {driver.title}")
        
        # Handle cookies
        try:
            continue_btn = driver.find_element(By.ID, "continue-btn")
            continue_btn.click()
            print("✅ Cookie consent handled")
            time.sleep(2)
        except:
            print("📝 No cookie consent needed")
        
        # Find and click ORCID
        wait = WebDriverWait(driver, 10)
        
        print("🔍 Looking for ORCID login...")
        orcid_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'orcid')]")))
        
        print("🔐 Found ORCID login, clicking...")
        driver.execute_script("arguments[0].click();", orcid_link)
        time.sleep(8)
        
        print(f"🌐 Current URL: {driver.current_url}")
        
        if 'orcid.org' in driver.current_url:
            print("✅ Redirected to ORCID successfully")
            
            # Test form field detection
            print("🔍 Looking for ORCID form fields...")
            
            try:
                # Wait longer for form to load
                wait = WebDriverWait(driver, 20)
                
                # Try different field selectors
                username_selectors = [
                    "#username",
                    "#signin-username", 
                    "input[name='username']",
                    "input[type='email']",
                    "input[placeholder*='email']",
                    "input[placeholder*='ORCID']"
                ]
                
                username_field = None
                for selector in username_selectors:
                    try:
                        username_field = driver.find_element(By.CSS_SELECTOR, selector)
                        print(f"✅ Found username field with: {selector}")
                        break
                    except:
                        continue
                
                if not username_field:
                    print("❌ Username field not found")
                    print("🔍 Available input fields:")
                    inputs = driver.find_elements(By.TAG_NAME, "input")
                    for i, inp in enumerate(inputs):
                        input_type = inp.get_attribute("type")
                        input_name = inp.get_attribute("name") 
                        input_id = inp.get_attribute("id")
                        input_placeholder = inp.get_attribute("placeholder")
                        print(f"  Input {i}: type={input_type}, name={input_name}, id={input_id}, placeholder={input_placeholder}")
                else:
                    print("✅ Username field found")
                    
                    # Look for password field
                    password_selectors = [
                        "#password",
                        "#signin-password",
                        "input[name='password']",
                        "input[type='password']"
                    ]
                    
                    password_field = None
                    for selector in password_selectors:
                        try:
                            password_field = driver.find_element(By.CSS_SELECTOR, selector)
                            print(f"✅ Found password field with: {selector}")
                            break
                        except:
                            continue
                    
                    if password_field:
                        print("✅ Both fields found - testing form submission")
                        
                        # Fill fields
                        username_field.clear()
                        username_field.send_keys(credentials['username'])
                        print("✅ Username entered")
                        
                        time.sleep(1)
                        
                        password_field.clear()
                        password_field.send_keys(credentials['password'])
                        print("✅ Password entered")
                        
                        time.sleep(2)
                        
                        # Find submit button
                        submit_selectors = [
                            "#signin-button",
                            "button[type='submit']",
                            "input[type='submit']",
                            "//button[contains(text(), 'Sign')]",
                            "//button[contains(text(), 'Login')]"
                        ]
                        
                        submit_button = None
                        for selector in submit_selectors:
                            try:
                                if selector.startswith("//"):
                                    submit_button = driver.find_element(By.XPATH, selector)
                                else:
                                    submit_button = driver.find_element(By.CSS_SELECTOR, selector)
                                print(f"✅ Found submit button with: {selector}")
                                break
                            except:
                                continue
                        
                        if submit_button:
                            print("🔐 Clicking submit button...")
                            driver.execute_script("arguments[0].click();", submit_button)
                            
                            print("⏳ Waiting for authentication...")
                            time.sleep(10)
                            
                            current_url = driver.current_url
                            print(f"🌐 Final URL: {current_url}")
                            
                            if 'sicon.siam.org' in current_url:
                                print("🎉 ORCID AUTHENTICATION SUCCESS!")
                                print("✅ Successfully returned to SICON")
                                
                                # Check for authenticated content
                                page_source = driver.page_source.lower()
                                auth_indicators = ['dashboard', 'manuscripts', 'author', 'logout']
                                found_indicators = [ind for ind in auth_indicators if ind in page_source]
                                
                                if found_indicators:
                                    print(f"✅ Authenticated indicators found: {found_indicators}")
                                else:
                                    print("🔍 No clear authentication indicators found")
                                
                                return True
                            else:
                                print(f"❌ Authentication failed - still at: {current_url}")
                                return False
                        else:
                            print("❌ Submit button not found")
                    else:
                        print("❌ Password field not found")
                        
            except Exception as e:
                print(f"❌ Form handling error: {e}")
                
        else:
            print(f"❌ Not redirected to ORCID - at: {driver.current_url}")
        
        # Keep browser open for manual inspection
        print("\n" + "="*50)
        print("🔍 MANUAL INSPECTION MODE")
        print("Browser will stay open for 30 seconds for manual inspection")
        print("You can manually complete the login to test the flow")
        print("="*50)
        time.sleep(30)
        
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            driver.quit()
            print("🖥️ Browser closed")
        except:
            pass


if __name__ == "__main__":
    print("🧪 ORCID Direct Authentication Test")
    print("=" * 50)
    
    success = test_orcid_direct()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ORCID AUTHENTICATION TEST PASSED!")
    else:
        print("❌ ORCID authentication test failed")
    print("=" * 50)