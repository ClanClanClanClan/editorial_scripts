#!/usr/bin/env python3
"""
MOR Navigation Fix - Login works, fix AE Center navigation
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

def extract_mor_with_navigation_fix():
    """MOR extraction with navigation fix."""
    
    options = webdriver.ChromeOptions()
    options.add_argument('--window-size=1200,800')
    options.add_argument('--window-position=100,100')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)
    
    manuscripts = []
    processed_ids = set()  # Global deduplication
    
    try:
        print("🔐 MOR EXTRACTOR - Navigation Fix Version...")
        
        # WORKING LOGIN (from final test)
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)
        
        # Handle cookies
        try:
            cookie_btn = driver.find_element(By.ID, "onetrust-reject-all-handler")
            cookie_btn.click()
            time.sleep(2)
        except:
            pass
        
        # Login
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
        time.sleep(8)
        
        # Handle 2FA
        if "twoFactorAuthForm" in driver.page_source:
            print("   📱 2FA required...")
            login_time = datetime.now()
            code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=login_time)
            
            if code:
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                time.sleep(8)
        
        # Handle device verification (WORKING VERSION)
        try:
            modal = driver.find_element(By.ID, "unrecognizedDeviceModal")
            if modal.is_displayed():
                print("   🔐 Device verification...")
                
                device_time = datetime.now()
                device_code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=device_time)
                
                if device_code:
                    print(f"   ✅ Got device code: {device_code[:3]}***")
                    
                    token_field = modal.find_element(By.ID, "TOKEN_VALUE")
                    token_field.clear()
                    token_field.send_keys(device_code)
                    
                    try:
                        remember_checkbox = modal.find_element(By.ID, "REMEMBER_THIS_DEVICE")
                        if not remember_checkbox.is_selected():
                            remember_checkbox.click()
                    except:
                        pass
                    
                    verify_btn = modal.find_element(By.ID, "VERIFY_BTN")
                    verify_btn.click()
                    time.sleep(12)
                    
        except:
            pass
        
        print("   ✅ Login phase complete")
        
        # ENHANCED NAVIGATION with multiple strategies
        print("\n📋 AE Center Navigation - Multiple strategies...")
        
        navigation_success = False
        
        # Strategy 1: Wait and try direct navigation
        print("   🔄 Strategy 1: Patient direct navigation...")
        time.sleep(5)  # Give login time to settle
        
        ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
        driver.get(ae_url)
        time.sleep(8)  # Longer wait
        
        current_page = driver.page_source
        if "Associate Editor" in current_page or "ASSOCIATE_EDITOR" in driver.current_url:
            print("   ✅ Strategy 1 successful!")
            navigation_success = True
        else:
            print("   ⚠️ Strategy 1 failed, trying Strategy 2...")
            
            # Strategy 2: Look for navigation links after login
            print("   🔄 Strategy 2: Link-based navigation...")
            
            # Go back to main page first
            driver.get("https://mc.manuscriptcentral.com/mathor")
            time.sleep(5)
            
            # Look for journal/AE links
            page_links = driver.find_elements(By.TAG_NAME, "a")
            
            # Find Mathematics journal link
            for link in page_links:
                link_text = link.text.strip()
                if "Mathematics of Operations Research" in link_text:
                    print(f"   🔗 Found journal link: {link_text}")
                    try:
                        link.click()
                        time.sleep(5)
                        break
                    except:
                        continue
            
            # Now look for Associate Editor link
            ae_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Associate Editor')]")
            if ae_links:
                print(f"   🔗 Found AE link: {ae_links[0].text}")
                try:
                    ae_links[0].click()
                    time.sleep(8)
                    
                    if "Associate Editor" in driver.page_source:
                        print("   ✅ Strategy 2 successful!")
                        navigation_success = True
                except Exception as e:
                    print(f"   ⚠️ Strategy 2 failed: {e}")
        
        if not navigation_success:
            # Strategy 3: Page inspection and manual search
            print("   🔄 Strategy 3: Page inspection...")
            
            current_page_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"   📄 Current page preview: {current_page_text[:200]}...")
            
            # Look for any manuscript-related content
            if "manuscript" in current_page_text.lower() or "MOR-" in current_page_text:
                print("   📄 Found manuscript-related content!")
                
                # Try to find manuscripts directly
                take_actions = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
                if take_actions:
                    print(f"   📄 Found {len(take_actions)} Take Action buttons directly!")
                    navigation_success = True
        
        # Process manuscripts if navigation successful
        if navigation_success:
            print(f"\n📊 Navigation successful - processing manuscripts...")
            
            # Look for category first
            category_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Awaiting Reviewer Reports")
            if category_links:
                print("   📂 Found category link")
                category_links[0].click()
                time.sleep(5)
            else:
                print("   📂 No category link, looking for manuscripts directly")
            
            # Find manuscripts
            take_action_images = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]")
            print(f"   🔍 Found {len(take_action_images)} Take Action buttons")
            
            # Extract manuscript IDs with deduplication
            manuscript_rows = []
            for img in take_action_images:
                try:
                    row = img.find_element(By.XPATH, "./ancestor::tr[1]")
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        manuscript_id = cells[0].text.strip()
                        if manuscript_id and "MOR-" in manuscript_id:
                            if manuscript_id not in processed_ids:  # Deduplication
                                manuscript_rows.append((manuscript_id, img))
                                processed_ids.add(manuscript_id)
                                print(f"   📋 Found: {manuscript_id}")
                            else:
                                print(f"   ⏭️ Skipping {manuscript_id} - already processed")
                except:
                    continue
            
            # Process each manuscript
            for i, (manuscript_id, img) in enumerate(manuscript_rows):
                print(f"\n📄 Processing {i+1}/{len(manuscript_rows)}: {manuscript_id}")
                
                try:
                    # Store main window
                    main_window = driver.current_window_handle
                    
                    # Click Take Action
                    take_action_link = img.find_element(By.XPATH, "./parent::a")
                    take_action_link.click()
                    time.sleep(5)
                    
                    # Extract data
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
                            "//td[contains(text(), 'Title')]/following-sibling::td[1]"
                        ]
                        
                        for selector in title_selectors:
                            try:
                                title_elem = driver.find_element(By.XPATH, selector)
                                manuscript_data['title'] = title_elem.text.strip()
                                if manuscript_data['title']:
                                    print(f"   📄 Title: {manuscript_data['title'][:50]}...")
                                    break
                            except:
                                continue
                    except:
                        pass
                    
                    # Extract referees
                    try:
                        referee_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'referee') or contains(text(), 'Reviewer')]")
                        for link in referee_links[:5]:
                            referee_name = link.text.strip()
                            if referee_name and len(referee_name) > 3:
                                manuscript_data['referees'].append({'name': referee_name})
                        
                        print(f"   👥 Found {len(manuscript_data['referees'])} referees")
                    except:
                        pass
                    
                    manuscripts.append(manuscript_data)
                    print(f"   ✅ Extracted {manuscript_id}")
                    
                    # Clean window management - never close main window
                    try:
                        all_windows = driver.window_handles
                        if len(all_windows) > 1:
                            for window in all_windows:
                                if window != main_window:
                                    driver.switch_to.window(window)
                                    driver.close()
                            driver.switch_to.window(main_window)
                    except:
                        pass
                    
                    # Go back
                    driver.back()
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"   ❌ Error processing {manuscript_id}: {e}")
                    try:
                        driver.back()
                        time.sleep(2)
                    except:
                        pass
            
        else:
            print("   ❌ All navigation strategies failed")
            
            # Save current page for debugging
            with open("navigation_debug.html", "w") as f:
                f.write(driver.page_source)
            print("   💾 Saved navigation debug page")
        
        # Save results
        results = {
            "extraction_time": datetime.now().isoformat(),
            "navigation_fix_version": "v1.0",
            "manuscripts": manuscripts,
            "total_found": len(manuscripts),
            "processed_ids": list(processed_ids),
            "navigation_successful": navigation_success
        }
        
        output_file = f"mor_navigation_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n🎉 NAVIGATION FIX EXTRACTION COMPLETE!")
        print(f"   📊 Total manuscripts: {len(manuscripts)}")
        print(f"   📋 Processed IDs: {list(processed_ids)}")
        print(f"   💾 Results: {output_file}")
        
        for manuscript in manuscripts:
            print(f"   ✅ {manuscript['id']}: {manuscript['title'][:50]}...")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print(f"\n⏰ Closing in 5 seconds...")
        time.sleep(5)
        driver.quit()
        print("🔒 Browser closed")
    
    return manuscripts

if __name__ == "__main__":
    results = extract_mor_with_navigation_fix()
    print(f"\n🏁 EXTRACTION COMPLETE: {len(results)} manuscripts found")
    
    if results:
        print("📋 SUCCESS - MANUSCRIPTS EXTRACTED:")
        for r in results:
            print(f"   ✅ {r['id']}: {r['title'][:40]}...")
    else:
        print("⚠️ NO MANUSCRIPTS FOUND - Check navigation/extraction logic")