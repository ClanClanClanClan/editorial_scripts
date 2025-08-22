#!/usr/bin/env python3
"""
Ultra-fast navigation - maybe there's a timing window
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

def ultra_fast_navigation_test():
    """Test ultra-fast navigation to beat the logout."""
    
    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1400,900')
    # Try different user agent
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    driver = webdriver.Chrome(options=options)
    
    try:
        print("⚡ ULTRA-FAST NAVIGATION TEST...")
        
        # Login phase
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(3)  # Reduced wait
        
        # Handle cookies quickly
        try:
            driver.find_element(By.ID, "onetrust-reject-all-handler").click()
            time.sleep(0.5)  # Faster
        except:
            pass
        
        # Credentials
        email = os.getenv('MOR_EMAIL', 'dylan.possamai@math.ethz.ch')
        password = os.getenv('MOR_PASSWORD', '')
        
        email_field = driver.find_element(By.ID, "USERID")
        email_field.clear()
        email_field.send_keys(email)
        
        password_field = driver.find_element(By.ID, "PASSWORD")
        password_field.clear()
        password_field.send_keys(password)
        
        # Submit
        login_timestamp = datetime.now()
        driver.find_element(By.ID, "logInButton").click()
        time.sleep(5)  # Reduced wait
        
        print(f"⚡ Login: {login_timestamp.strftime('%H:%M:%S')}")
        
        # Handle 2FA properly - wait for code to arrive
        if "twoFactorAuthForm" in driver.page_source:
            print("📱 2FA required - waiting for fresh code...")
            print(f"🕒 Waiting for code sent after: {login_timestamp.strftime('%H:%M:%S.%f')}")
            
            # Give proper time for email to arrive
            time.sleep(5)  # Wait for email to be sent
            
            code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=login_timestamp)
            if code:
                print(f"✅ Got fresh 2FA code: {code}")
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                time.sleep(5)  # Wait for 2FA processing
            else:
                print("❌ No 2FA code received")
                return False
        
        # Handle device verification properly or dismiss
        try:
            modal = driver.find_element(By.ID, "unrecognizedDeviceModal")
            if modal.is_displayed():
                print("🔐 Device verification modal found...")
                print("📱 Dismissing modal (original working approach)...")
                
                close_btn = modal.find_element(By.CLASS_NAME, "button-close")
                close_btn.click()
                time.sleep(3)  # Give time for modal to close
                print("✅ Modal dismissed")
        except:
            print("✅ No device verification modal")
        
        # IMMEDIATE NAVIGATION - no delays
        print("⚡ IMMEDIATE navigation (no delays)...")
        navigation_start = datetime.now()
        
        # Try multiple URLs rapidly
        urls_to_try = [
            "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD",
            "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_CENTER",
            "https://mc.manuscriptcentral.com/mathor"
        ]
        
        success = False
        for i, url in enumerate(urls_to_try):
            print(f"⚡ Try {i+1}: {url}")
            driver.get(url)
            time.sleep(2)  # Minimal wait
            
            page_content = driver.page_source
            
            if "logged out" in page_content.lower() or "inactivity" in page_content.lower():
                print(f"❌ Try {i+1}: Logged out detected")
                continue
            elif "Associate Editor" in page_content:
                print(f"✅ Try {i+1}: SUCCESS!")
                success = True
                break
            else:
                print(f"⚠️ Try {i+1}: Unclear status")
                
        navigation_end = datetime.now()
        navigation_time = (navigation_end - navigation_start).total_seconds()
        
        print(f"⚡ Navigation took: {navigation_time:.2f} seconds")
        
        if success:
            print("⚡ Ultra-fast navigation SUCCESS - looking for manuscripts...")
            
            # Fast manuscript search
            category_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Awaiting Reviewer Reports")
            if category_links:
                category_links[0].click()
                time.sleep(2)
            
            take_actions = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
            print(f"⚡ Found {len(take_actions)} manuscripts in {navigation_time:.2f}s!")
            
            manuscripts = []
            for img in take_actions[:3]:  # Just first 3
                try:
                    row = img.find_element(By.XPATH, "./ancestor::tr[1]")
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        manuscript_id = cells[0].text.strip()
                        if "MOR-" in manuscript_id:
                            manuscripts.append(manuscript_id)
                            print(f"⚡ {manuscript_id}")
                except:
                    continue
            
            result = {
                "ultra_fast_success": True,
                "navigation_time_seconds": navigation_time,
                "manuscripts": manuscripts,
                "timestamp": datetime.now().isoformat()
            }
            
            with open("ultra_fast_success.json", "w") as f:
                json.dump(result, f, indent=2)
                
            print(f"\n⚡ ULTRA-FAST APPROACH WORKS!")
            return True
            
        else:
            print("❌ Ultra-fast navigation also failed")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    finally:
        time.sleep(3)
        driver.quit()

if __name__ == "__main__":
    success = ultra_fast_navigation_test()
    if success:
        print("\n⚡ SOLUTION: Ultra-fast navigation beats the logout!")
    else:
        print("\n❌ Even ultra-fast navigation fails - server-side change")