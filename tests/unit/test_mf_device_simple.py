#!/usr/bin/env python3
"""
Simple test to debug MF device verification
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys
sys.path.append('.')
from core.email_utils import fetch_latest_verification_code

def test_mf_device_simple():
    """Test MF device verification with detailed debugging"""
    print("🔍 Testing MF Device Verification (Simple)")
    
    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("1. Navigating to MF login page...")
        driver.get("https://mc.manuscriptcentral.com/mafi")
        time.sleep(3)
        
        # Accept cookies
        try:
            accept_button = driver.find_element(By.CLASS_NAME, "cc-btn.cc-dismiss")
            accept_button.click()
            print("✅ Accepted cookies")
        except:
            print("No cookie accept button found")
        
        print("2. Logging in...")
        # Get credentials
        import subprocess
        user = subprocess.run(["op", "read", "op://Work/MF/email"], capture_output=True, text=True).stdout.strip()
        pw = subprocess.run(["op", "read", "op://Work/MF/password"], capture_output=True, text=True).stdout.strip()
        
        user_box = driver.find_element(By.ID, "USERID")
        pw_box = driver.find_element(By.ID, "PASSWORD")
        
        user_box.clear()
        user_box.send_keys(user)
        pw_box.clear()
        pw_box.send_keys(pw)
        
        login_btn = driver.find_element(By.ID, "logInButton")
        login_btn.click()
        
        print("3. Waiting for device verification page...")
        time.sleep(5)
        
        # Check if we're on device verification page
        page_source = driver.page_source
        if "UNRECOGNIZED_DEVICE" in page_source:
            print("✅ On device verification page")
            
            # Save the page
            with open("mf_device_page_simple.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            
            # Look for verification code input
            try:
                code_input = driver.find_element(By.ID, "TOKEN_VALUE")
                print("✅ Found TOKEN_VALUE input")
                
                # Get verification code
                print("4. Fetching verification code...")
                code = fetch_latest_verification_code(journal="MF")
                if code:
                    print(f"✅ Got code: {code}")
                    code_input.clear()
                    code_input.send_keys(code)
                    
                    # Check remember device checkbox
                    try:
                        remember_checkbox = driver.find_element(By.ID, "REMEMBER_THIS_DEVICE")
                        if not remember_checkbox.is_selected():
                            remember_checkbox.click()
                            print("✅ Checked 'Remember this device'")
                    except:
                        print("❌ Could not find remember device checkbox")
                    
                    # Find and click VERIFY_BTN
                    print("5. Looking for VERIFY_BTN...")
                    
                    # Method 1: Direct ID
                    try:
                        verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
                        print(f"✅ Found VERIFY_BTN by ID")
                        print(f"   - Tag: {verify_btn.tag_name}")
                        print(f"   - Text: {verify_btn.text}")
                        print(f"   - Displayed: {verify_btn.is_displayed()}")
                        print(f"   - Enabled: {verify_btn.is_enabled()}")
                        
                        # Click it
                        driver.execute_script("arguments[0].scrollIntoView(true);", verify_btn)
                        time.sleep(1)
                        verify_btn.click()
                        print("✅ Clicked VERIFY_BTN!")
                        
                    except Exception as e:
                        print(f"❌ Could not find VERIFY_BTN by ID: {e}")
                        
                        # Method 2: Look for all buttons/links
                        print("Looking for all clickable elements...")
                        buttons = driver.find_elements(By.XPATH, "//button | //a | //input[@type='button'] | //input[@type='submit']")
                        for btn in buttons:
                            btn_id = btn.get_attribute("id") or ""
                            btn_text = btn.text or ""
                            btn_value = btn.get_attribute("value") or ""
                            if "verify" in btn_id.lower() or "verify" in btn_text.lower() or "verify" in btn_value.lower():
                                print(f"   Found verify element: ID={btn_id}, Text={btn_text}, Value={btn_value}")
                    
                    # Wait and check result
                    print("6. Waiting for page to load after verification...")
                    time.sleep(10)
                    
                    # Check current state
                    current_url = driver.current_url
                    page_title = driver.title
                    print(f"\n📍 Current state:")
                    print(f"   URL: {current_url}")
                    print(f"   Title: {page_title}")
                    
                    if "UNRECOGNIZED_DEVICE" in driver.page_source:
                        print("❌ Still on device verification page!")
                        with open("mf_still_on_device_page.html", "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                    else:
                        print("✅ Successfully passed device verification!")
                        
                        # Look for Associate Editor Center
                        try:
                            ae_link = driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                            print("✅ Found Associate Editor Center link!")
                        except:
                            print("❌ Could not find Associate Editor Center link")
                            
                else:
                    print("❌ No verification code found")
                    
            except Exception as e:
                print(f"❌ Error during verification: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("❌ Not on device verification page")
            print(f"   Current URL: {driver.current_url}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        input("\nPress Enter to close browser...")
        driver.quit()

if __name__ == "__main__":
    test_mf_device_simple()