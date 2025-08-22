#!/usr/bin/env python3
"""
MOR Extractor with Session Persistence Fix
Handles the logout-after-device-verification issue
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

def extract_mor_with_session_fix():
    """MOR extraction with session persistence fix."""
    
    # Setup Chrome with session persistence
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
    options.add_argument('--window-size=1920,1080')
    # Add session persistence
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--keep-alive-for-test')
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 30)
    
    manuscripts = []
    
    try:
        print("🔐 MOR EXTRACTOR with Session Persistence...")
        
        # Step 1: Login with immediate post-verification handling
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)
        
        # Handle cookies
        try:
            driver.find_element(By.ID, "onetrust-reject-all-handler").click()
            time.sleep(1)
        except:
            pass
        
        # Enter credentials
        email = os.getenv('MOR_EMAIL', 'dylan.possamai@math.ethz.ch')
        password = os.getenv('MOR_PASSWORD', '')
        
        email_field = wait.until(EC.element_to_be_clickable((By.ID, "USERID")))
        email_field.clear()
        email_field.send_keys(email)
        
        password_field = driver.find_element(By.ID, "PASSWORD")
        password_field.clear()
        password_field.send_keys(password)
        
        login_button = driver.find_element(By.ID, "logInButton")
        login_button.click()
        print("   ✅ Login submitted")
        time.sleep(8)
        
        # Handle 2FA
        if "twoFactorAuthForm" in driver.page_source:
            print("   📱 2FA required...")
            login_time = datetime.now()
            code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=login_time)
            
            if code:
                print(f"   ✅ Got 2FA code: {code[:3]}***")
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                time.sleep(8)
        
        # Handle device verification with immediate session preservation
        try:
            modal = driver.find_element(By.ID, "unrecognizedDeviceModal")
            if modal.is_displayed():
                print("   🔐 Device verification with session preservation...")
                
                device_time = datetime.now()
                device_code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=device_time)
                
                if device_code:
                    print(f"   ✅ Got device code: {device_code[:3]}***")
                    
                    # Enter code
                    token_field = modal.find_element(By.ID, "TOKEN_VALUE")
                    token_field.clear()
                    token_field.send_keys(device_code)
                    
                    # Always check remember device
                    try:
                        remember_checkbox = modal.find_element(By.ID, "REMEMBER_THIS_DEVICE")
                        if not remember_checkbox.is_selected():
                            remember_checkbox.click()
                            print("   ✅ Remember device checked")
                    except:
                        pass
                    
                    # Submit verification
                    verify_btn = modal.find_element(By.ID, "VERIFY_BTN")
                    verify_btn.click()
                    print("   ✅ Device verification submitted")
                    
                    # CRITICAL: Wait for modal to close AND immediately navigate
                    try:
                        wait.until(EC.invisibility_of_element_located((By.ID, "unrecognizedDeviceModal")))
                        print("   ✅ Modal closed")
                        
                        # IMMEDIATE navigation to prevent session timeout
                        time.sleep(2)  # Brief wait
                        print("   🚀 Immediate navigation to preserve session...")
                        
                        # Try to navigate to AE dashboard immediately
                        ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
                        driver.get(ae_url)
                        time.sleep(5)
                        
                        current_url = driver.current_url
                        print(f"   📍 Immediate navigation result: {current_url}")
                        
                        # Check if navigation was successful
                        page_content = driver.page_source
                        if "logged out" in page_content.lower() or "inactivity" in page_content.lower():
                            print("   ⚠️ Session expired despite immediate navigation")
                            print("   🔄 Attempting re-authentication...")
                            
                            # Try to re-authenticate by going back to login
                            driver.get("https://mc.manuscriptcentral.com/mathor")
                            time.sleep(3)
                            
                            # Check if we're auto-logged in (due to remember device)
                            if "login" not in driver.current_url.lower():
                                print("   ✅ Auto-login successful!")
                                # Navigate to AE dashboard
                                driver.get(ae_url)
                                time.sleep(5)
                            else:
                                print("   ❌ Re-authentication required")
                                return manuscripts
                        else:
                            print("   ✅ Session preserved!")
                            
                    except TimeoutException:
                        print("   ⚠️ Modal timeout")
                        time.sleep(5)
                        
                else:
                    print("   ❌ No device verification code")
                    return manuscripts
        except NoSuchElementException:
            print("   ✅ No device verification needed")
        
        # Check final login status
        current_url = driver.current_url
        page_content = driver.page_source
        
        print(f"   📍 Final URL: {current_url}")
        
        if "Associate Editor" in page_content or "ASSOCIATE_EDITOR" in current_url:
            print("   🎉 Successfully reached AE Center!")
        else:
            print("   📄 Current page preview:")
            page_preview = driver.find_element(By.TAG_NAME, "body").text[:200]
            print(f"      {page_preview}...")
            
            # Try one more navigation attempt
            print("   🔄 Final navigation attempt...")
            
            # Look for any navigation links
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                link_text = link.text.strip()
                if any(word in link_text.lower() for word in ['mathematics', 'associate editor', 'dashboard']):
                    print(f"   🔗 Found navigation link: {link_text}")
                    try:
                        link.click()
                        time.sleep(5)
                        break
                    except:
                        continue
        
        # Look for manuscripts
        print("\n📊 Looking for manuscripts...")
        
        # First try to find category
        category_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Awaiting Reviewer Reports")
        if category_links:
            print("   📂 Found category")
            category_links[0].click()
            time.sleep(5)
        
        # Look for Take Action buttons
        take_action_images = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
        print(f"   🔍 Found {len(take_action_images)} Take Action buttons")
        
        if len(take_action_images) == 0:
            # Debug: save current page
            with open("session_debug_page.html", "w") as f:
                f.write(driver.page_source)
            print("   💾 Saved current page for debugging")
            
            # Look for any manuscript-related text
            page_text = driver.find_element(By.TAG_NAME, "body").text
            if "manuscript" in page_text.lower() or "MOR-" in page_text:
                print("   📄 Found manuscript-related content")
                
                # Look for manuscript IDs in page text
                import re
                manuscript_matches = re.findall(r'MOR-\d{4}-\d{3,4}(?:\.R\d+)?', page_text)
                if manuscript_matches:
                    print(f"   📋 Found manuscript IDs in text: {manuscript_matches}")
            else:
                print("   ⚠️ No manuscript content found")
        
        # Extract manuscript IDs from Take Action buttons
        manuscript_rows = []
        for img in take_action_images:
            try:
                row = img.find_element(By.XPATH, "./ancestor::tr[1]")
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells:
                    manuscript_id = cells[0].text.strip()
                    if manuscript_id and "MOR-" in manuscript_id:
                        manuscript_rows.append((manuscript_id, row, img))
                        print(f"   📋 Found: {manuscript_id}")
            except:
                continue
        
        print(f"\n🎯 FOUND {len(manuscript_rows)} MANUSCRIPTS")
        
        # Process manuscripts (simplified for debugging)
        for i, (manuscript_id, row, img) in enumerate(manuscript_rows):
            print(f"   📄 {manuscript_id}")
            manuscripts.append({
                'id': manuscript_id,
                'title': 'Title extraction pending',
                'extraction_time': datetime.now().isoformat()
            })
        
        # Save results
        results = {
            "extraction_time": datetime.now().isoformat(),
            "session_fix_version": "v1.0",
            "manuscripts": manuscripts,
            "total_found": len(manuscripts),
            "session_preserved": len(manuscripts) > 0
        }
        
        output_file = f"mor_session_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n🎉 SESSION FIX EXTRACTION COMPLETE!")
        print(f"   📊 Total manuscripts: {len(manuscripts)}")
        print(f"   💾 Results: {output_file}")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        input("\n⏸️ Press Enter to close...")
        driver.quit()
    
    return manuscripts

if __name__ == "__main__":
    results = extract_mor_with_session_fix()
    print(f"\n📊 FINAL: {len(results)} manuscripts found")