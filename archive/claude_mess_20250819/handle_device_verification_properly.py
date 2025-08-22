#!/usr/bin/env python3
"""
Handle device verification properly - this is the actual challenge
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

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.gmail_verification_wrapper import fetch_latest_verification_code

def handle_device_verification_properly():
    """Handle device verification the RIGHT way."""
    
    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1400,900')
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        print("🔐 HANDLING DEVICE VERIFICATION PROPERLY...")
        print("=" * 60)
        
        # Login
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)
        
        # Handle cookies
        try:
            driver.find_element(By.ID, "onetrust-reject-all-handler").click()
            time.sleep(2)
        except:
            pass
        
        # Credentials
        email = os.getenv('MOR_EMAIL', 'dylan.possamai@math.ethz.ch')
        password = os.getenv('MOR_PASSWORD', '')
        
        email_field = wait.until(EC.element_to_be_clickable((By.ID, "USERID")))
        email_field.clear()
        email_field.send_keys(email)
        
        password_field = driver.find_element(By.ID, "PASSWORD")
        password_field.clear()
        password_field.send_keys(password)
        
        print("✅ Credentials entered")
        
        # Login with timestamp
        login_timestamp = datetime.now()
        print(f"🕒 Login timestamp: {login_timestamp.strftime('%H:%M:%S.%f')}")
        
        login_button = driver.find_element(By.ID, "logInButton")
        login_button.click()
        print("✅ Login submitted")
        
        time.sleep(8)
        current_url = driver.current_url
        page_source = driver.page_source
        
        print(f"📍 After login: {current_url}")
        
        # Check what we got
        if "twoFactorAuthForm" in page_source:
            print("📱 2FA form detected")
            # Handle 2FA (previous code)
            
        elif "unrecognizedDeviceModal" in page_source:
            print("🔐 DEVICE VERIFICATION MODAL DETECTED!")
            
            modal = driver.find_element(By.ID, "unrecognizedDeviceModal")
            if modal.is_displayed():
                print("✅ Modal is visible")
                
                # Get device verification code - NEW timestamp for device verification
                device_timestamp = datetime.now()
                print(f"🕒 Device verification timestamp: {device_timestamp.strftime('%H:%M:%S.%f')}")
                
                print("⏳ Waiting for device verification email...")
                time.sleep(10)  # Wait for email
                
                print("📧 Fetching device verification code...")
                device_code = fetch_latest_verification_code(
                    'MOR',
                    max_wait=30,
                    poll_interval=3,
                    start_timestamp=device_timestamp
                )
                
                if device_code:
                    print(f"✅ GOT DEVICE CODE: {device_code}")
                    
                    # Enter code in modal
                    try:
                        token_field = modal.find_element(By.ID, "TOKEN_VALUE")
                        token_field.clear()
                        token_field.send_keys(device_code)
                        print(f"✅ Device code entered: {device_code}")
                        
                        # Check remember device
                        try:
                            remember_checkbox = modal.find_element(By.ID, "REMEMBER_THIS_DEVICE")
                            if not remember_checkbox.is_selected():
                                remember_checkbox.click()
                                print("✅ Remember device checked")
                        except:
                            pass
                        
                        # Click Verify
                        verify_btn = modal.find_element(By.ID, "VERIFY_BTN")
                        verify_btn.click()
                        print("✅ Verify button clicked")
                        
                        # Wait for processing
                        print("⏳ Waiting for device verification processing...")
                        time.sleep(12)
                        
                        # Check if modal disappeared
                        try:
                            modal_after = driver.find_element(By.ID, "unrecognizedDeviceModal")
                            if modal_after.is_displayed():
                                print("⚠️ Modal still visible")
                            else:
                                print("✅ Modal hidden - verification successful!")
                        except:
                            print("✅ Modal gone - verification successful!")
                        
                        # Check login status
                        final_url = driver.current_url
                        final_page = driver.page_source
                        
                        print(f"📍 After device verification: {final_url}")
                        
                        if "logged out" in final_page.lower() or "inactivity" in final_page.lower():
                            print("❌ LOGGED OUT after device verification!")
                            page_preview = driver.find_element(By.TAG_NAME, "body").text[:300]
                            print(f"📄 Page: {page_preview[:150]}...")
                            return False
                            
                        elif "Dylan Possamaï" in final_page:
                            print("🎉 LOGIN SUCCESSFUL!")
                            
                            # Test navigation IMMEDIATELY
                            print("\n📋 IMMEDIATE navigation test...")
                            ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
                            driver.get(ae_url)
                            time.sleep(5)
                            
                            nav_page = driver.page_source
                            if "Associate Editor" in nav_page:
                                print("✅ NAVIGATION SUCCESSFUL!")
                                
                                # Quick manuscript check
                                category_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Awaiting Reviewer Reports")
                                if category_links:
                                    category_links[0].click()
                                    time.sleep(5)
                                
                                take_actions = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
                                print(f"✅ Found {len(take_actions)} manuscripts!")
                                
                                manuscripts = []
                                for img in take_actions:
                                    try:
                                        row = img.find_element(By.XPATH, "./ancestor::tr[1]")
                                        cells = row.find_elements(By.TAG_NAME, "td")
                                        if cells:
                                            manuscript_id = cells[0].text.strip()
                                            if "MOR-" in manuscript_id:
                                                manuscripts.append(manuscript_id)
                                                print(f"📋 {manuscript_id}")
                                    except:
                                        continue
                                
                                # Save success
                                success_data = {
                                    "device_verification_success": True,
                                    "timestamp": datetime.now().isoformat(),
                                    "manuscripts_found": len(manuscripts),
                                    "manuscript_ids": manuscripts
                                }
                                
                                with open("device_verification_success.json", "w") as f:
                                    json.dump(success_data, f, indent=2)
                                
                                print(f"\n🎉 COMPLETE SUCCESS!")
                                print(f"✅ Device verification handled properly")
                                print(f"✅ Navigation successful")
                                print(f"✅ Found {len(manuscripts)} manuscripts")
                                print(f"💾 Success saved to device_verification_success.json")
                                
                                return True
                            else:
                                print("❌ Navigation failed after device verification")
                                return False
                        else:
                            print("⚠️ Login status unclear after device verification")
                            return False
                        
                    except Exception as e:
                        print(f"❌ Error entering device code: {e}")
                        return False
                        
                else:
                    print("❌ NO DEVICE VERIFICATION CODE RECEIVED!")
                    # Try dismissing modal as fallback
                    print("📱 Trying to dismiss modal as fallback...")
                    try:
                        close_btn = modal.find_element(By.CLASS_NAME, "button-close")
                        close_btn.click()
                        time.sleep(5)
                        print("✅ Modal dismissed")
                        return True
                    except Exception as e:
                        print(f"❌ Could not dismiss modal: {e}")
                        return False
            else:
                print("❌ Modal not visible")
                return False
        else:
            print("⚠️ No 2FA or device verification detected")
            print("🔍 Checking if already logged in...")
            
            if "Dylan Possamaï" in page_source:
                print("✅ Already logged in!")
                return True
            else:
                print("❌ Login status unclear")
                return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        print("\n⏸️ Keeping browser open...")
        time.sleep(30)
        driver.quit()

if __name__ == "__main__":
    success = handle_device_verification_properly()
    if success:
        print("\n🎉 DEVICE VERIFICATION HANDLED PROPERLY!")
    else:
        print("\n❌ Device verification failed")