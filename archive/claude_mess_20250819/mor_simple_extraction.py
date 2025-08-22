#!/usr/bin/env python3

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

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.gmail_verification_wrapper import fetch_latest_verification_code

def run_mor_extraction():
    """Simple direct MOR extraction that actually works."""
    
    # Setup Chrome
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1920, 1080)
    
    try:
        # Login
        print("🔐 Logging in to MOR...")
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(3)
        
        # Enter credentials
        email = os.getenv('MOR_EMAIL', 'dylan.possamai@math.ethz.ch')
        password = os.getenv('MOR_PASSWORD', '')
        
        driver.find_element(By.ID, "USERID").send_keys(email)
        driver.find_element(By.ID, "PASSWORD").send_keys(password)
        driver.find_element(By.ID, "logInButton").click()
        time.sleep(5)
        
        # Check for 2FA
        if "twoFactorAuthForm" in driver.page_source:
            print("   📱 2FA required, getting code from Gmail...")
            login_time = datetime.now()
            code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=login_time)
            if code:
                print(f"   ✅ Got code: {code[:3]}***")
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                time.sleep(5)
        
        print("   ✅ Logged in successfully!")
        
        # Navigate to journal
        print("\n📋 Navigating to journal...")
        journal_link = driver.find_element(By.LINK_TEXT, "Mathematics of Operations Research")
        driver.execute_script("arguments[0].click();", journal_link)
        time.sleep(5)
        
        # Find Associate Editor Center
        print("📋 Looking for Associate Editor Center...")
        ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Associate Editor")
        ae_link.click()
        time.sleep(5)
        
        # Now we should be on AE dashboard - find manuscripts
        print("\n🔍 Finding manuscripts...")
        manuscripts = []
        processed_ids = set()
        
        # Look for all category links
        category_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'NEXT_PAGE=') and contains(text(), 'Awaiting')]")
        print(f"   Found {len(category_links)} categories")
        
        for cat_link in category_links:
            cat_text = cat_link.text
            print(f"\n📂 Processing category: {cat_text}")
            cat_link.click()
            time.sleep(3)
            
            # Find manuscripts with Take Action buttons
            take_actions = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]/parent::a")
            print(f"   Found {len(take_actions)} manuscripts")
            
            for i in range(len(take_actions)):
                try:
                    # Re-find elements after navigation
                    take_actions = driver.find_elements(By.XPATH, "//img[contains(@src, 'check_off.gif')]/parent::a")
                    if i >= len(take_actions):
                        break
                        
                    # Get manuscript ID from row
                    row = take_actions[i].find_element(By.XPATH, "./ancestor::tr[1]")
                    cells = row.find_elements(By.TAG_NAME, "td")
                    manuscript_id = cells[0].text.strip() if cells else "UNKNOWN"
                    
                    # Skip if already processed
                    if manuscript_id in processed_ids:
                        print(f"   ⏭️ Skipping {manuscript_id} - already processed")
                        continue
                    
                    print(f"\n   📄 Processing manuscript: {manuscript_id}")
                    take_actions[i].click()
                    time.sleep(3)
                    
                    # Extract basic data
                    manuscript_data = {
                        "id": manuscript_id,
                        "category": cat_text,
                        "title": "Unknown",
                        "authors": [],
                        "referees": []
                    }
                    
                    # Try to get title
                    try:
                        title_elem = driver.find_element(By.XPATH, "//td[contains(text(), 'Title:')]/following-sibling::td")
                        manuscript_data["title"] = title_elem.text.strip()
                    except:
                        pass
                    
                    # Try to get referees
                    try:
                        referee_links = driver.find_elements(By.XPATH, "//a[contains(@onclick, 'popWindow') and contains(@onclick, 'referee')]")
                        for ref_link in referee_links:
                            referee_name = ref_link.text.strip()
                            if referee_name:
                                manuscript_data["referees"].append({"name": referee_name})
                    except:
                        pass
                    
                    manuscripts.append(manuscript_data)
                    processed_ids.add(manuscript_id)
                    
                    # Go back
                    driver.back()
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"   ⚠️ Error: {e}")
                    continue
            
            # Go back to AE dashboard
            driver.back()
            time.sleep(2)
            
            # Re-find category links
            category_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'NEXT_PAGE=') and contains(text(), 'Awaiting')]")
        
        # Save results
        output = {
            "extraction_time": datetime.now().isoformat(),
            "manuscripts": manuscripts,
            "total": len(manuscripts)
        }
        
        with open("mor_extraction_results.json", "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"\n✅ EXTRACTION COMPLETE!")
        print(f"   📊 Total manuscripts: {len(manuscripts)}")
        print(f"   📊 Unique IDs: {len(processed_ids)}")
        for ms in manuscripts:
            print(f"   - {ms['id']}: {ms['title'][:50]}...")
        
        return manuscripts
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return []
        
    finally:
        driver.quit()

if __name__ == "__main__":
    results = run_mor_extraction()
    print(f"\n📋 Final count: {len(results)} manuscripts extracted")