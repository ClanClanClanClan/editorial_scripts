#!/usr/bin/env python3

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.gmail_verification_wrapper import fetch_latest_verification_code

def extract_two_manuscripts():
    """Quick test to extract the 2 manuscripts."""
    
    options = webdriver.ChromeOptions()
    # Visible mode for debugging
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1920, 1080)
    
    try:
        # Login
        print("🔐 Logging in...")
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(3)
        
        email = os.getenv('MOR_EMAIL', 'dylan.possamai@math.ethz.ch')
        password = os.getenv('MOR_PASSWORD', '')
        
        driver.find_element(By.ID, "USERID").send_keys(email)
        driver.find_element(By.ID, "PASSWORD").send_keys(password)
        driver.find_element(By.ID, "logInButton").click()
        time.sleep(5)
        
        # Handle 2FA if needed
        if "twoFactorAuthForm" in driver.page_source:
            print("   📱 2FA required...")
            login_time = datetime.now()
            code = fetch_latest_verification_code('MOR', max_wait=30, poll_interval=2, start_timestamp=login_time)
            if code:
                print(f"   ✅ Got code: {code[:3]}***")
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                time.sleep(5)
        
        print("   ✅ Logged in!")
        
        # Click journal link
        try:
            journal_link = driver.find_element(By.LINK_TEXT, "Mathematics of Operations Research")
            journal_link.click()
            time.sleep(5)
            print("   ✅ Clicked journal link")
        except:
            print("   ℹ️ No journal link needed")
        
        # Go to AE Center
        ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Associate Editor")
        ae_link.click()
        time.sleep(5)
        print("   ✅ In AE Center")
        
        # Click on "Awaiting Reviewer Reports" category
        awaiting_link = driver.find_element(By.LINK_TEXT, "Awaiting Reviewer Reports")
        awaiting_link.click()
        time.sleep(3)
        print("   ✅ In Awaiting Reviewer Reports category")
        
        # Get all manuscript IDs from the table
        print("\n📊 Finding manuscripts in table...")
        manuscript_ids = []
        
        # Find all rows with Take Action buttons
        take_action_links = driver.find_elements(By.XPATH, "//a[.//img[contains(@src, 'check_off.gif')]]")
        print(f"   Found {len(take_action_links)} Take Action links")
        
        for link in take_action_links:
            try:
                # Get the row
                row = link.find_element(By.XPATH, "./ancestor::tr[1]")
                # Get first cell (manuscript ID)
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells:
                    manuscript_id = cells[0].text.strip()
                    manuscript_ids.append(manuscript_id)
                    print(f"   📄 Found manuscript: {manuscript_id}")
            except Exception as e:
                print(f"   ⚠️ Error getting manuscript ID: {e}")
        
        print(f"\n✅ FOUND {len(manuscript_ids)} MANUSCRIPTS:")
        for mid in manuscript_ids:
            print(f"   - {mid}")
        
        # Process each manuscript
        for i, manuscript_id in enumerate(manuscript_ids):
            print(f"\n📄 Processing manuscript {i+1}/{len(manuscript_ids)}: {manuscript_id}")
            
            # Click the Take Action for this manuscript
            if i > 0:
                # Go back to list
                driver.back()
                time.sleep(3)
                
                # Find the right Take Action link
                take_action_links = driver.find_elements(By.XPATH, "//a[.//img[contains(@src, 'check_off.gif')]]")
                for link in take_action_links:
                    try:
                        row = link.find_element(By.XPATH, "./ancestor::tr[1]")
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if cells and cells[0].text.strip() == manuscript_id:
                            link.click()
                            time.sleep(5)
                            break
                    except:
                        continue
            else:
                # First manuscript - just click first link
                take_action_links[0].click()
                time.sleep(5)
            
            # Get title
            try:
                title_elem = driver.find_element(By.XPATH, "//td[contains(text(), 'Title:')]/following-sibling::td")
                title = title_elem.text.strip()
                print(f"   Title: {title[:60]}...")
            except:
                print("   ⚠️ Could not get title")
        
        return manuscript_ids
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []
        
    finally:
        input("\n⏸️ Press Enter to close browser...")
        driver.quit()

if __name__ == "__main__":
    results = extract_two_manuscripts()
    print(f"\n📊 FINAL RESULT: {len(results)} manuscripts found")
    for r in results:
        print(f"   - {r}")