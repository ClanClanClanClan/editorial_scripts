#!/usr/bin/env python3
"""
Back to basics - exactly what was working before I broke everything
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

def back_to_working_version():
    """Go back to exactly what was working."""
    
    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1400,900')
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    
    try:
        print("🔐 BACK TO BASICS - What was working before...")
        
        # Navigate to login
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)
        print(f"✓ Page loaded: {driver.current_url}")
        
        # Handle cookies
        try:
            driver.find_element(By.ID, "onetrust-reject-all-handler").click()
            time.sleep(2)
            print("✓ Cookies handled")
        except:
            print("✓ No cookies to handle")
        
        # Enter credentials
        email = os.getenv('MOR_EMAIL', 'dylan.possamai@math.ethz.ch')
        password = os.getenv('MOR_PASSWORD', '')
        
        if not email or not password:
            print("❌ No credentials found")
            return False
        
        print(f"✓ Using email: {email}")
        
        # Fill login form
        email_field = wait.until(EC.element_to_be_clickable((By.ID, "USERID")))
        email_field.clear()
        email_field.send_keys(email)
        print("✓ Email entered")
        
        password_field = driver.find_element(By.ID, "PASSWORD")
        password_field.clear()
        password_field.send_keys(password)
        print("✓ Password entered")
        
        # Record time BEFORE clicking login
        login_timestamp = datetime.now()
        print(f"✓ Login timestamp: {login_timestamp.strftime('%H:%M:%S.%f')}")
        
        # Click login
        login_button = driver.find_element(By.ID, "logInButton")
        login_button.click()
        print("✓ Login button clicked")
        
        # Wait for login to process
        time.sleep(8)
        print(f"✓ After login wait: {driver.current_url}")
        
        # Handle 2FA if needed - WAIT PROPERLY
        if "twoFactorAuthForm" in driver.page_source:
            print("📱 2FA form detected - waiting for code...")
            
            # Wait for email to arrive first
            print("⏳ Waiting 10 seconds for 2FA email to arrive...")
            time.sleep(10)
            
            # Now fetch code
            print(f"📧 Fetching code sent after {login_timestamp.strftime('%H:%M:%S.%f')}")
            code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=3, start_timestamp=login_timestamp)
            
            if code:
                print(f"✅ Got 2FA code: {code}")
                
                # Enter code
                code_field = driver.find_element(By.NAME, "verificationCode")
                code_field.clear()
                code_field.send_keys(code)
                print("✓ 2FA code entered")
                
                # Submit 2FA
                submit_btn = driver.find_element(By.ID, "submitButton")
                submit_btn.click()
                print("✓ 2FA submitted")
                
                # Wait for 2FA processing
                time.sleep(8)
                print(f"✓ After 2FA: {driver.current_url}")
            else:
                print("❌ No 2FA code received - aborting")
                return False
        else:
            print("✓ No 2FA required")
        
        # Handle device verification - ORIGINAL WORKING WAY
        try:
            modal = driver.find_element(By.ID, "unrecognizedDeviceModal")
            if modal.is_displayed():
                print("🔐 Device verification modal found")
                print("📱 Using ORIGINAL approach - just dismiss it")
                
                close_btn = modal.find_element(By.CLASS_NAME, "button-close")
                close_btn.click()
                print("✓ Modal dismissed")
                
                time.sleep(5)
                print(f"✓ After modal dismiss: {driver.current_url}")
                
        except:
            print("✓ No device verification modal")
        
        # Check final login status
        final_url = driver.current_url
        page_content = driver.page_source
        
        print(f"\n📍 FINAL STATUS CHECK:")
        print(f"URL: {final_url}")
        
        # Check for success indicators
        success_indicators = [
            "Dylan Possamaï" in page_content,
            "Associate Editor" in page_content,
            "logout" in page_content.lower() and "inactivity" not in page_content.lower()
        ]
        
        failure_indicators = [
            "logged out" in page_content.lower(),
            "inactivity" in page_content.lower(),
            "Log In" in page_content and final_url == "https://mc.manuscriptcentral.com/mathor"
        ]
        
        if any(failure_indicators):
            print("❌ FAILED - Logged out detected")
            page_preview = driver.find_element(By.TAG_NAME, "body").text[:300]
            print(f"📄 Page: {page_preview[:150]}...")
            return False
            
        elif any(success_indicators):
            print("✅ LOGIN SUCCESSFUL!")
            
            # Now try navigation
            print("\n📋 Testing navigation to AE Center...")
            ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
            driver.get(ae_url)
            time.sleep(8)
            
            nav_content = driver.page_source
            nav_url = driver.current_url
            
            print(f"📍 Navigation result: {nav_url}")
            
            if "Associate Editor" in nav_content:
                print("✅ Navigation successful!")
                
                # Look for manuscripts
                print("📊 Looking for manuscripts...")
                
                # Try category first
                category_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Awaiting Reviewer Reports")
                if category_links:
                    print("✓ Found category link")
                    category_links[0].click()
                    time.sleep(5)
                else:
                    print("⚠️ No category link")
                
                # Find Take Action buttons
                take_actions = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
                print(f"✓ Found {len(take_actions)} Take Action buttons")
                
                if len(take_actions) > 0:
                    # Extract manuscript IDs
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
                    result = {
                        "success": True,
                        "timestamp": datetime.now().isoformat(),
                        "manuscripts_found": len(manuscripts),
                        "manuscript_ids": manuscripts
                    }
                    
                    with open("back_to_basics_success.json", "w") as f:
                        json.dump(result, f, indent=2)
                    
                    print(f"\n🎉 SUCCESS!")
                    print(f"✓ Found {len(manuscripts)} manuscripts")
                    print(f"✓ Saved to back_to_basics_success.json")
                    
                    return True
                else:
                    print("⚠️ No manuscripts found")
                    return False
                    
            else:
                print("❌ Navigation failed")
                nav_preview = driver.find_element(By.TAG_NAME, "body").text[:200]
                print(f"📄 Nav page: {nav_preview}...")
                return False
        else:
            print("⚠️ Login status unclear")
            page_preview = driver.find_element(By.TAG_NAME, "body").text[:200]
            print(f"📄 Page: {page_preview}...")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        print("\n⏸️ Keeping browser open for 30 seconds...")
        time.sleep(30)
        driver.quit()

if __name__ == "__main__":
    print("Going back to exactly what was working...")
    success = back_to_working_version()
    
    if success:
        print("\n✅ BACK TO WORKING STATE!")
    else:
        print("\n❌ Still broken")