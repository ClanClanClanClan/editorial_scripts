#!/usr/bin/env python3
"""
Fixed MOR Extractor - Proper device verification handling
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

def extract_mor_with_fixed_verification():
    """Extract MOR manuscripts with properly fixed device verification."""
    
    # Setup Chrome - visible for debugging
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)  # Longer wait times
    
    manuscripts = []
    processed_ids = set()
    
    try:
        # Step 1: Login
        print("🔐 FIXED Login Process...")
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)
        
        email = os.getenv('MOR_EMAIL', 'dylan.possamai@math.ethz.ch')
        password = os.getenv('MOR_PASSWORD', '')
        
        # Enter credentials
        email_field = wait.until(EC.element_to_be_clickable((By.ID, "USERID")))
        email_field.send_keys(email)
        driver.find_element(By.ID, "PASSWORD").send_keys(password)
        driver.find_element(By.ID, "logInButton").click()
        time.sleep(5)
        
        # Step 2: Handle 2FA if needed
        if "twoFactorAuthForm" in driver.page_source:
            print("   📱 2FA verification...")
            login_time = datetime.now()
            code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=login_time)
            if code:
                print(f"   ✅ Got 2FA code: {code[:3]}***")
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                time.sleep(5)
        
        # Step 3: Handle device verification with proper form submission
        if "Unrecognized Device" in driver.page_source:
            print("   🔐 Device verification with proper form handling...")
            
            # Get verification code
            device_time = datetime.now()
            device_code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=device_time)
            
            if device_code:
                print(f"   ✅ Got device code: {device_code}")
                
                # Wait for modal to be fully loaded
                token_field = wait.until(EC.element_to_be_clickable((By.ID, "TOKEN_VALUE")))
                
                # Clear and enter code
                token_field.clear()
                token_field.send_keys(device_code)
                print("   ✅ Entered device verification code")
                
                # Optional: Check "Remember this device"
                try:
                    remember_checkbox = driver.find_element(By.ID, "REMEMBER_THIS_DEVICE")
                    if not remember_checkbox.is_selected():
                        remember_checkbox.click()
                        print("   ✅ Checked 'Remember this device'")
                except:
                    pass
                
                # Click Verify button with proper wait
                verify_btn = wait.until(EC.element_to_be_clickable((By.ID, "VERIFY_BTN")))
                verify_btn.click()
                print("   🔄 Clicked Verify button, waiting for processing...")
                
                # Wait for the modal to disappear (indicating successful verification)
                try:
                    wait.until(EC.invisibility_of_element_located((By.ID, "unrecognizedDeviceModal")))
                    print("   ✅ Device verification modal closed")
                except TimeoutException:
                    print("   ⚠️ Modal didn't close, but continuing...")
                
                # Wait for page to redirect/reload
                time.sleep(10)
                
                final_url = driver.current_url
                print(f"   📍 After device verification: {final_url}")
                
                # Check if we're properly logged in
                if "login" not in final_url.lower():
                    print("   🎉 Device verification successful - logged in!")
                else:
                    print("   ⚠️ Still on login page, checking page content...")
                    
                    # Check if page content indicates we're logged in
                    page_body = driver.find_element(By.TAG_NAME, "body").text
                    if "Dylan Possamaï" in page_body or "Associate Editor" in page_body:
                        print("   ✅ Found user content - actually logged in")
                    else:
                        print("   ❌ Device verification may have failed")
                        
                        # Save debug page
                        with open("post_device_verification.html", "w") as f:
                            f.write(driver.page_source)
                        print("   💾 Saved post-verification page for debugging")
            else:
                print("   ❌ No device verification code received")
                return manuscripts
        
        # Step 4: Navigate to AE Center
        print("\n📋 Navigating to AE Center...")
        
        # Try multiple navigation strategies
        success = False
        
        # Strategy 1: Direct URL
        try:
            ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
            driver.get(ae_url)
            time.sleep(5)
            
            if "Associate Editor" in driver.page_source or "ASSOCIATE_EDITOR" in driver.current_url:
                print("   ✅ Direct URL navigation successful")
                success = True
        except:
            pass
        
        # Strategy 2: Look for journal and AE links
        if not success:
            try:
                # Look for journal link first
                journal_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Mathematics")
                if journal_links:
                    journal_links[0].click()
                    time.sleep(5)
                    print("   ✅ Clicked journal link")
                
                # Look for AE Center link
                ae_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Associate Editor")
                if ae_links:
                    ae_links[0].click()
                    time.sleep(5)
                    print("   ✅ Clicked AE Center link")
                    success = True
                    
            except Exception as e:
                print(f"   ⚠️ Link navigation failed: {e}")
        
        if not success:
            print("   ⚠️ Navigation uncertain, checking current page...")
            
        # Debug current page
        current_url = driver.current_url
        page_preview = driver.find_element(By.TAG_NAME, "body").text[:300]
        print(f"   📍 Current URL: {current_url}")
        print(f"   📄 Page preview: {page_preview[:100]}...")
        
        # Step 5: Look for category or manuscripts
        print("\n📊 Looking for manuscripts...")
        
        # Look for Awaiting Reviewer Reports category
        category_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Awaiting Reviewer Reports")
        if category_links:
            print("   ✅ Found 'Awaiting Reviewer Reports' category")
            category_links[0].click()
            time.sleep(5)
        else:
            print("   ⚠️ No category link found, looking for manuscripts directly")
        
        # Look for Take Action buttons
        take_action_images = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
        print(f"   📄 Found {len(take_action_images)} Take Action buttons")
        
        # Get manuscript rows
        manuscript_rows = []
        for img in take_action_images:
            try:
                row = img.find_element(By.XPATH, "./ancestor::tr[1]")
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells:
                    manuscript_id = cells[0].text.strip()
                    if manuscript_id and "MOR-" in manuscript_id:
                        manuscript_rows.append((manuscript_id, row, img))
                        print(f"   📋 Found manuscript: {manuscript_id}")
            except Exception as e:
                print(f"   ⚠️ Row processing error: {e}")
        
        print(f"\n🎯 PROCESSING {len(manuscript_rows)} MOR MANUSCRIPTS")
        
        # Process each manuscript
        for i, (manuscript_id, row, take_action_img) in enumerate(manuscript_rows):
            if manuscript_id in processed_ids:
                print(f"   ⏭️ Skipping {manuscript_id} - already processed")
                continue
            
            print(f"\n📄 Processing {i+1}/{len(manuscript_rows)}: {manuscript_id}")
            
            try:
                # Click Take Action
                original_window = driver.current_window_handle
                take_action_link = take_action_img.find_element(By.XPATH, "./parent::a")
                take_action_link.click()
                time.sleep(5)
                
                # Extract data
                manuscript_data = {
                    'id': manuscript_id,
                    'title': '',
                    'authors': [],
                    'referees': [],
                    'status': '',
                    'extracted_at': datetime.now().isoformat()
                }
                
                # Get title
                try:
                    title_elem = driver.find_element(By.XPATH, "//td[contains(text(), 'Title:')]/following-sibling::td")
                    manuscript_data['title'] = title_elem.text.strip()
                    print(f"   📄 Title: {manuscript_data['title'][:50]}...")
                except:
                    print("   ⚠️ Could not extract title")
                
                # Get referees safely
                try:
                    referee_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'referee') or contains(text(), 'Reviewer')]")[:3]
                    for link in referee_links:
                        referee_name = link.text.strip()
                        if referee_name and len(referee_name) > 3:
                            manuscript_data['referees'].append({'name': referee_name})
                    print(f"   👥 Found {len(manuscript_data['referees'])} referees")
                except:
                    print("   ⚠️ Could not extract referees")
                
                manuscripts.append(manuscript_data)
                processed_ids.add(manuscript_id)
                print(f"   ✅ Successfully processed {manuscript_id}")
                
                # Cleanup and go back
                try:
                    all_windows = driver.window_handles
                    if len(all_windows) > 1:
                        for window in all_windows:
                            if window != original_window:
                                driver.switch_to.window(window)
                                driver.close()
                        driver.switch_to.window(original_window)
                except:
                    pass
                
                driver.back()
                time.sleep(3)
                
            except Exception as e:
                print(f"   ❌ Processing error for {manuscript_id}: {e}")
                try:
                    driver.switch_to.window(original_window)
                    driver.back()
                    time.sleep(2)
                except:
                    pass
        
        # Save results
        output = {
            "extraction_time": datetime.now().isoformat(),
            "manuscripts": manuscripts,
            "total_unique": len(processed_ids),
            "processed_ids": list(processed_ids)
        }
        
        with open("mor_fixed_results.json", "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"\n🎉 FIXED EXTRACTION COMPLETE!")
        print(f"   📊 Total manuscripts: {len(manuscripts)}")
        print(f"   📋 Processed IDs: {list(processed_ids)}")
        
        for manuscript in manuscripts:
            print(f"   ✅ {manuscript['id']}: {manuscript['title'][:50]}...")
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        input("\n⏸️ Press Enter to close browser...")
        driver.quit()
    
    return manuscripts

if __name__ == "__main__":
    results = extract_mor_with_fixed_verification()
    print(f"\n📊 FINAL: {len(results)} manuscripts extracted")