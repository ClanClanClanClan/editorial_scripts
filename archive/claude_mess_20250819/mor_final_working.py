#!/usr/bin/env python3
"""
FINAL WORKING MOR EXTRACTOR
Combines all fixes: device verification, navigation, popup management
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

def extract_mor_final():
    """Final working MOR extraction with all fixes applied."""
    
    # Setup Chrome with stealth options
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 30)
    
    manuscripts = []
    processed_ids = set()
    
    try:
        print("🔐 FINAL MOR EXTRACTOR - Starting login...")
        
        # Step 1: Navigate and login
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
        
        print(f"   📧 Using email: {email}")
        
        email_field = wait.until(EC.element_to_be_clickable((By.ID, "USERID")))
        email_field.clear()
        email_field.send_keys(email)
        
        password_field = driver.find_element(By.ID, "PASSWORD")
        password_field.clear()
        password_field.send_keys(password)
        
        # Submit login
        login_button = driver.find_element(By.ID, "logInButton")
        login_button.click()
        print("   ✅ Login form submitted")
        time.sleep(8)
        
        # Step 2: Handle 2FA if needed
        if "twoFactorAuthForm" in driver.page_source:
            print("   📱 2FA required...")
            login_time = datetime.now()
            code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=login_time)
            
            if code:
                print(f"   ✅ Got 2FA code: {code[:3]}***")
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                time.sleep(8)
                print("   ✅ 2FA submitted")
        
        # Step 3: Handle device verification (FIXED VERSION)
        try:
            modal = driver.find_element(By.ID, "unrecognizedDeviceModal")
            if modal.is_displayed():
                print("   🔐 Device verification required...")
                
                # Get verification code
                device_time = datetime.now()
                device_code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=device_time)
                
                if device_code:
                    print(f"   ✅ Got device code: {device_code[:3]}***")
                    
                    # Enter code
                    token_field = modal.find_element(By.ID, "TOKEN_VALUE")
                    token_field.clear()
                    token_field.send_keys(device_code)
                    
                    # Remember device
                    try:
                        remember_checkbox = modal.find_element(By.ID, "REMEMBER_THIS_DEVICE")
                        if not remember_checkbox.is_selected():
                            remember_checkbox.click()
                            print("   ✅ Checked remember device")
                    except:
                        pass
                    
                    # Submit verification
                    verify_btn = modal.find_element(By.ID, "VERIFY_BTN")
                    verify_btn.click()
                    print("   ✅ Device verification submitted")
                    
                    # Wait for processing and modal to close
                    try:
                        wait.until(EC.invisibility_of_element_located((By.ID, "unrecognizedDeviceModal")))
                        print("   ✅ Device verification modal closed")
                    except TimeoutException:
                        print("   ⚠️ Modal timeout, but continuing...")
                    
                    time.sleep(10)  # Additional wait for processing
                else:
                    print("   ❌ No device verification code - aborting")
                    return manuscripts
        except NoSuchElementException:
            print("   ✅ No device verification needed")
        except Exception as e:
            print(f"   ⚠️ Device verification error: {e}")
        
        # Step 4: Verify login success
        current_url = driver.current_url
        page_content = driver.page_source
        
        print(f"   📍 Current URL: {current_url}")
        
        login_success_indicators = [
            "Dylan Possamaï" in page_content,
            "Associate Editor" in page_content, 
            "ASSOCIATE_EDITOR" in current_url,
            "logout" in page_content.lower(),
            "log out" in page_content.lower()
        ]
        
        if any(login_success_indicators):
            print("   🎉 LOGIN SUCCESSFUL!")
        else:
            print("   ❌ Login may have failed")
            # Save debug page
            with open("final_login_debug.html", "w") as f:
                f.write(page_content)
            print("   💾 Saved debug page")
        
        # Step 5: Navigate to AE Center (Multiple strategies)
        print("\n📋 Navigating to AE Center...")
        
        success = False
        
        # Strategy 1: Direct URL
        try:
            ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
            driver.get(ae_url)
            time.sleep(8)
            
            current_url = driver.current_url
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            if "Associate Editor" in page_text or "ASSOCIATE_EDITOR" in current_url:
                print("   ✅ Direct URL navigation successful")
                success = True
            else:
                print(f"   📄 Page preview: {page_text[:200]}...")
                
        except Exception as e:
            print(f"   ⚠️ Direct navigation failed: {e}")
        
        # Strategy 2: Look for navigation links
        if not success:
            try:
                # Look for journal link
                journal_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Mathematics')]")
                if journal_links:
                    journal_links[0].click()
                    time.sleep(5)
                    print("   ✅ Clicked journal link")
                
                # Look for AE Center link  
                ae_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Associate Editor')]")
                if ae_links:
                    ae_links[0].click()
                    time.sleep(5)
                    print("   ✅ Clicked AE Center link")
                    success = True
                    
            except Exception as e:
                print(f"   ⚠️ Link navigation failed: {e}")
        
        # Step 6: Look for manuscripts
        print("\n📊 Looking for manuscripts...")
        
        # Try to find category first
        category_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Awaiting Reviewer Reports")
        if category_links:
            print("   📂 Found category link")
            category_links[0].click()
            time.sleep(5)
        else:
            print("   ℹ️ No category link found")
        
        # Look for Take Action buttons
        take_action_images = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
        print(f"   🔍 Found {len(take_action_images)} Take Action buttons")
        
        # Extract manuscript IDs
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
                # Store original window
                original_window = driver.current_window_handle
                
                # Click Take Action
                take_action_link = take_action_img.find_element(By.XPATH, "./parent::a")
                take_action_link.click()
                time.sleep(5)
                
                # Extract manuscript data
                manuscript_data = {
                    'id': manuscript_id,
                    'title': '',
                    'authors': [],
                    'referees': [],
                    'status': 'Unknown',
                    'extraction_time': datetime.now().isoformat()
                }
                
                # Extract title
                try:
                    title_selectors = [
                        "//td[contains(text(), 'Title:')]/following-sibling::td",
                        "//td[contains(text(), 'Title')]/following-sibling::td[1]",
                        "//tr[td[contains(text(), 'Title')]]/td[2]"
                    ]
                    
                    for selector in title_selectors:
                        try:
                            title_elem = driver.find_element(By.XPATH, selector)
                            manuscript_data['title'] = title_elem.text.strip()
                            if manuscript_data['title']:
                                break
                        except:
                            continue
                    
                    if manuscript_data['title']:
                        print(f"   📄 Title: {manuscript_data['title'][:50]}...")
                    else:
                        print("   ⚠️ Could not extract title")
                        
                except Exception as e:
                    print(f"   ⚠️ Title extraction error: {e}")
                
                # Extract referees (safe approach)
                try:
                    referee_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'referee') or contains(text(), 'Reviewer')]")
                    for link in referee_links[:5]:  # Limit to prevent issues
                        referee_name = link.text.strip()
                        if referee_name and len(referee_name) > 3:
                            manuscript_data['referees'].append({
                                'name': referee_name,
                                'status': 'Unknown'
                            })
                    
                    print(f"   👥 Found {len(manuscript_data['referees'])} referees")
                    
                except Exception as e:
                    print(f"   ⚠️ Referee extraction error: {e}")
                
                # Add to results
                manuscripts.append(manuscript_data)
                processed_ids.add(manuscript_id)
                print(f"   ✅ Successfully processed {manuscript_id}")
                
                # Cleanup popups and return
                try:
                    all_windows = driver.window_handles
                    if len(all_windows) > 1:
                        for window in all_windows:
                            if window != original_window:
                                driver.switch_to.window(window)
                                driver.close()
                        driver.switch_to.window(original_window)
                        print("   🧹 Cleaned up popup windows")
                except:
                    pass
                
                # Return to list
                driver.back()
                time.sleep(3)
                
            except Exception as e:
                print(f"   ❌ Processing error for {manuscript_id}: {e}")
                try:
                    # Ensure we're back in original window
                    driver.switch_to.window(original_window)
                    driver.back()
                    time.sleep(2)
                except:
                    pass
        
        # Save final results
        final_results = {
            "extraction_time": datetime.now().isoformat(), 
            "extractor_version": "final_working_v1.0",
            "manuscripts": manuscripts,
            "total_found": len(manuscripts),
            "unique_ids": list(processed_ids),
            "login_successful": len(manuscripts) > 0
        }
        
        output_file = f"mor_final_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(final_results, f, indent=2)
        
        print(f"\n🎉 FINAL EXTRACTION COMPLETE!")
        print(f"   📊 Total manuscripts found: {len(manuscripts)}")
        print(f"   📋 Manuscript IDs: {list(processed_ids)}")
        print(f"   💾 Results saved to: {output_file}")
        
        for manuscript in manuscripts:
            print(f"   ✅ {manuscript['id']}: {manuscript['title'][:50]}...")
        
        if len(manuscripts) == 0:
            print("\n⚠️ NO MANUSCRIPTS FOUND")
            print("   This could indicate:")
            print("   - Login failed")
            print("   - Navigation to AE Center failed") 
            print("   - No manuscripts in the category")
            print("   - Different page structure than expected")
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
        # Save error state
        try:
            with open("final_error_debug.html", "w") as f:
                f.write(driver.page_source)
            print("💾 Saved error state for debugging")
        except:
            pass
            
    finally:
        input("\n⏸️ Press Enter to close browser...")
        driver.quit()
    
    return manuscripts

if __name__ == "__main__":
    results = extract_mor_final()
    print(f"\n📊 EXTRACTION COMPLETE: {len(results)} manuscripts found")