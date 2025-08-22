#!/usr/bin/env python3
"""
Complete MOR Login Flow - Handle all steps including post-device-verification
"""

import os
import sys
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.gmail_verification_wrapper import fetch_latest_verification_code

def complete_mor_login():
    """Complete MOR login with all steps."""
    
    # Setup Chrome - visible for debugging
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 30)  # Even longer wait times
    
    manuscripts = []
    
    try:
        # Step 1: Initial login
        print("🔐 COMPLETE Login Flow...")
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)
        
        email = os.getenv('MOR_EMAIL', 'dylan.possamai@math.ethz.ch')
        password = os.getenv('MOR_PASSWORD', '')
        
        # Enter credentials
        email_field = wait.until(EC.element_to_be_clickable((By.ID, "USERID")))
        email_field.clear()
        email_field.send_keys(email)
        
        password_field = driver.find_element(By.ID, "PASSWORD")
        password_field.clear()
        password_field.send_keys(password)
        
        login_button = driver.find_element(By.ID, "logInButton")
        login_button.click()
        print("   ✅ Submitted initial login")
        time.sleep(8)  # Longer wait
        
        # Step 2: Handle 2FA if needed
        if "twoFactorAuthForm" in driver.page_source:
            print("   📱 2FA verification...")
            login_time = datetime.now()
            code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=login_time)
            if code:
                print(f"   ✅ Got 2FA code: {code[:3]}***")
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                print("   ✅ Submitted 2FA code")
                time.sleep(8)
        
        # Step 3: Handle device verification
        if "Unrecognized Device" in driver.page_source:
            print("   🔐 Device verification detected...")
            
            # Get verification code
            device_time = datetime.now()
            device_code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=device_time)
            
            if device_code:
                print(f"   ✅ Got device code: {device_code}")
                
                # Enter code
                token_field = wait.until(EC.element_to_be_clickable((By.ID, "TOKEN_VALUE")))
                token_field.clear()
                token_field.send_keys(device_code)
                
                # Check remember device
                try:
                    remember_checkbox = driver.find_element(By.ID, "REMEMBER_THIS_DEVICE")
                    if not remember_checkbox.is_selected():
                        remember_checkbox.click()
                        print("   ✅ Checked remember device")
                except:
                    pass
                
                # Click Verify
                verify_btn = wait.until(EC.element_to_be_clickable((By.ID, "VERIFY_BTN")))
                verify_btn.click()
                print("   ✅ Submitted device verification")
                
                # Wait for processing
                print("   🔄 Waiting for device verification processing...")
                time.sleep(15)  # Longer wait for processing
                
                current_url = driver.current_url
                print(f"   📍 After device verification wait: {current_url}")
                
                # Check if modal is gone
                try:
                    modal = driver.find_element(By.ID, "unrecognizedDeviceModal")
                    if modal.is_displayed():
                        print("   ⚠️ Modal still visible, waiting more...")
                        time.sleep(10)
                    else:
                        print("   ✅ Modal closed")
                except:
                    print("   ✅ Modal not found (probably closed)")
                
                # Additional step: Check if there's a form to submit after device verification
                try:
                    # Look for any forms or submit buttons
                    submit_buttons = driver.find_elements(By.XPATH, "//input[@type='submit'] | //button[@type='submit'] | //a[contains(@class, 'btn')]")
                    visible_submits = [btn for btn in submit_buttons if btn.is_displayed()]
                    
                    print(f"   🔍 Found {len(visible_submits)} visible submit buttons after device verification")
                    
                    for btn in visible_submits[:3]:  # Check first 3
                        btn_text = btn.text.strip()
                        btn_class = btn.get_attribute("class")
                        print(f"      - Button: '{btn_text}' (class: {btn_class})")
                        
                        # If there's a "Continue" or "Submit" button, click it
                        if any(word in btn_text.lower() for word in ['continue', 'submit', 'proceed', 'next']):
                            print(f"      🎯 Clicking: {btn_text}")
                            btn.click()
                            time.sleep(8)
                            break
                except Exception as e:
                    print(f"   ⚠️ Error checking post-verification buttons: {e}")
        
        # Step 4: Final login check and redirect
        print("\n🔍 Final login status check...")
        current_url = driver.current_url
        page_source = driver.page_source
        
        print(f"   📍 Current URL: {current_url}")
        
        # Multiple ways to check if logged in
        login_indicators = [
            "Dylan Possamaï" in page_source,
            "Associate Editor" in page_source,
            "ASSOCIATE_EDITOR" in current_url,
            "dashboard" in current_url.lower(),
            "NEXT_PAGE" in current_url and "LOGIN" not in current_url
        ]
        
        if any(login_indicators):
            print("   🎉 LOGIN SUCCESSFUL!")
            
            # Try to go to AE dashboard
            print("\n📋 Navigating to AE Dashboard...")
            ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
            driver.get(ae_url)
            time.sleep(8)
            
            dashboard_url = driver.current_url
            dashboard_page = driver.find_element(By.TAG_NAME, "body").text[:300]
            
            print(f"   📍 Dashboard URL: {dashboard_url}")
            print(f"   📄 Dashboard content: {dashboard_page[:100]}...")
            
            # Look for manuscripts
            print("\n📊 Looking for manuscripts...")
            
            # Try to find category links first
            category_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Awaiting Reviewer Reports")
            if category_links:
                print("   ✅ Found category link")
                category_links[0].click()
                time.sleep(5)
            
            # Look for Take Action buttons
            take_action_images = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
            print(f"   📄 Found {len(take_action_images)} manuscripts")
            
            # Get manuscript IDs
            manuscript_ids = []
            for img in take_action_images:
                try:
                    row = img.find_element(By.XPATH, "./ancestor::tr[1]")
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        manuscript_id = cells[0].text.strip()
                        if manuscript_id and "MOR-" in manuscript_id:
                            manuscript_ids.append(manuscript_id)
                            print(f"   📋 {manuscript_id}")
                except:
                    pass
            
            print(f"\n🎯 FOUND {len(manuscript_ids)} MOR MANUSCRIPTS:")
            for mid in manuscript_ids:
                print(f"   - {mid}")
                
            # Save results
            output = {
                "login_successful": True,
                "extraction_time": datetime.now().isoformat(),
                "manuscript_ids": manuscript_ids,
                "total_found": len(manuscript_ids),
                "final_url": dashboard_url
            }
            
            with open("mor_complete_login_results.json", "w") as f:
                json.dump(output, f, indent=2)
            
            print(f"\n🎉 COMPLETE LOGIN SUCCESS!")
            print(f"   📊 Found {len(manuscript_ids)} manuscripts")
            
        else:
            print("   ❌ LOGIN FAILED - Still on login page")
            
            # Save debug page
            with open("final_login_debug.html", "w") as f:
                f.write(page_source)
            print("   💾 Saved debug page")
            
            # Check what's on the page
            page_preview = driver.find_element(By.TAG_NAME, "body").text[:500]
            print(f"   📄 Page content: {page_preview[:200]}...")
            
            # Look for any error messages
            error_indicators = ["error", "failed", "invalid", "incorrect"]
            page_lower = page_source.lower()
            for indicator in error_indicators:
                if indicator in page_lower:
                    print(f"   ⚠️ Found '{indicator}' in page")
                    break
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        input("\n⏸️ Press Enter to close browser...")
        driver.quit()
    
    return manuscripts

if __name__ == "__main__":
    results = complete_mor_login()
    print(f"\n📊 COMPLETE")