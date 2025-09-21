#!/usr/bin/env python3
"""
MOR CLICK FIXED - Test the fixed clicking strategy
"""

import sys
import os
import time
import re
import json

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.gmail_verification import fetch_latest_verification_code

print("="*80)
print("🎯 MOR CLICK FIXED - Test fixed strategy")
print("="*80)

driver = None
try:
    # Quick setup
    print("\n1. Quick Setup & Login")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(60)
    wait = WebDriverWait(driver, 20)

    # Navigate and login
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        reject = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler")))
        reject.click()
        time.sleep(2)
    except:
        pass

    # Login
    wait.until(EC.presence_of_element_located((By.ID, "USERID")))
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    login_time = time.time()
    driver.find_element(By.ID, "logInButton").click()

    # 2FA
    time.sleep(5)
    if "TOKEN_VALUE" in driver.page_source:
        print("   2FA detected, waiting for new email...")
        time.sleep(15)

        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_time + 5
        )

        if code:
            print(f"   Got code: {code}")
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            driver.execute_script("document.getElementById('VERIFY_BTN').click();")
            time.sleep(10)

    print("   ✅ Logged in")

    # Navigate to AE Center
    print("\n2. Navigate to AE Center")
    ae_link = None
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if "associate editor" in link.text.lower():
            ae_link = link
            break

    if ae_link:
        driver.execute_script("arguments[0].click();", ae_link)
        time.sleep(5)
        print("   ✅ In AE Center")

    # Go to Awaiting Reviewer Reports
    print("\n3. Go to Awaiting Reviewer Reports")
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if "Awaiting Reviewer Reports" in link.text:
            driver.execute_script("arguments[0].click();", link)
            time.sleep(5)
            print("   ✅ In category")
            break

    # Find and click manuscript using fixed strategy
    print("\n4. TEST FIXED CLICKING STRATEGY")
    manuscript_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
    print(f"   Found {len(manuscript_rows)} manuscripts")

    if manuscript_rows:
        row = manuscript_rows[0]
        row_text = row.text

        # Extract ID
        mor_match = re.search(r'MOR-\d{4}-\d+', row_text)
        manuscript_id = mor_match.group() if mor_match else "Unknown"
        print(f"   Processing: {manuscript_id}")

        # FIXED STRATEGY - prioritize manuscript ID link
        action_button = None

        # Strategy 1: Click manuscript ID link directly (most reliable)
        try:
            action_button = row.find_element(By.XPATH, f".//a[contains(text(), '{manuscript_id}')]")
            print("   ✅ Found manuscript ID link")
        except:
            pass

        # Strategy 2: Click action image/icon
        if not action_button:
            try:
                action_button = row.find_element(By.XPATH,
                    ".//img[contains(@src, 'check') or contains(@src, 'action')]/parent::*")
                print("   ✅ Found action image")
            except:
                pass

        if action_button:
            # Store current state
            main_window = driver.current_window_handle
            original_url = driver.current_url

            # Use JavaScript click
            print("   Clicking element with JavaScript...")
            driver.execute_script("arguments[0].scrollIntoView(true);", action_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", action_button)
            time.sleep(5)

            # Check navigation
            current_url = driver.current_url
            if current_url != original_url:
                print(f"   ✅ NAVIGATION SUCCESSFUL!")
                print(f"   Original URL: {original_url[:50]}...")
                print(f"   Current URL: {current_url[:50]}...")

                # Check window state
                if len(driver.window_handles) > 1:
                    print("   📑 Opened in popup window")
                    for window in driver.window_handles:
                        if window != main_window:
                            driver.switch_to.window(window)
                            break
                else:
                    print("   📑 Navigated in same window")

                # Extract some data to prove we're in the manuscript
                print("\n5. VERIFY WE'RE IN MANUSCRIPT DETAILS:")

                # Look for manuscript info
                if manuscript_id in driver.page_source:
                    print(f"   ✅ Manuscript {manuscript_id} found in page")

                # Look for referee rows
                referee_rows = driver.find_elements(By.XPATH,
                    "//tr[contains(., 'Invited') or contains(., 'Agreed') or contains(., 'Declined')]")
                print(f"   ✅ Found {len(referee_rows)} referee rows")

                # Extract first few referees
                for i, ref_row in enumerate(referee_rows[:3]):
                    cells = ref_row.find_elements(By.TAG_NAME, "td")
                    if len(cells) > 1:
                        name = cells[1].text if cells[1].text else "Unknown"
                        status = cells[2].text if len(cells) > 2 else "Unknown"
                        print(f"      Referee {i+1}: {name} - {status}")

                # Save success result
                result = {
                    "success": True,
                    "manuscript_id": manuscript_id,
                    "navigation_type": "popup" if len(driver.window_handles) > 1 else "same_window",
                    "referee_count": len(referee_rows)
                }

                output_file = f"/tmp/mor_click_success_{int(time.time())}.json"
                with open(output_file, "w") as f:
                    json.dump(result, f, indent=2)
                print(f"\n   ✅ SUCCESS! Results saved to: {output_file}")

            else:
                print(f"   ❌ Click didn't navigate")
        else:
            print("   ❌ No clickable element found")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

finally:
    if driver:
        print("\nClosing in 10 seconds...")
        time.sleep(10)
        driver.quit()

print("\n" + "="*80)
print("CLICK TEST COMPLETE")
print("="*80)