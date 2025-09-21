#!/usr/bin/env python3
"""
MOR PROPER CLICK - Actually click Take Action button
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
from selenium.webdriver.common.action_chains import ActionChains

from core.gmail_verification import fetch_latest_verification_code

print("="*80)
print("🎯 MOR PROPER CLICK - GET INTO MANUSCRIPT")
print("="*80)

driver = None
try:
    # Quick setup
    print("\n1. Quick Setup & Login")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, 10)
    actions = ActionChains(driver)

    # Navigate and login
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
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
        print("   2FA detected...")
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
            try:
                driver.find_element(By.ID, "VERIFY_BTN").click()
            except:
                driver.execute_script("document.getElementById('VERIFY_BTN').click();")
            time.sleep(10)

    print("   ✅ Logged in")

    # Navigate to AE Center
    print("\n2. Navigate to AE Center")
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if "associate editor" in link.text.lower():
            link.click()
            time.sleep(5)
            print("   ✅ In AE Center")
            break

    # Go to Awaiting Reviewer Reports
    print("\n3. Go to Awaiting Reviewer Reports")
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if "Awaiting Reviewer Reports" in link.text:
            link.click()
            time.sleep(5)
            print("   ✅ In category")
            break

    # Save screenshot before clicking
    driver.save_screenshot("/tmp/mor_before_click.png")
    print("   📸 Before click: /tmp/mor_before_click.png")

    # Find manuscript rows
    print("\n4. Find and Click Manuscript")
    manuscript_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
    print(f"   Found {len(manuscript_rows)} manuscripts")

    # Get first manuscript row
    if manuscript_rows:
        row = manuscript_rows[0]

        # Extract manuscript ID
        row_text = row.text
        mor_match = re.search(r'MOR-\d{4}-\d+', row_text)
        if mor_match:
            manuscript_id = mor_match.group()
            print(f"   Processing: {manuscript_id}")

        # Print referee info from the table
        print("\n   📊 REFEREE INFO FROM TABLE:")
        lines = row_text.split('\n')
        for line in lines:
            if 'active' in line or 'invited' in line or 'agreed' in line:
                print(f"      {line}")

        print("\n   🔍 FINDING CLICKABLE ELEMENT:")

        # Strategy 1: Look for the checkbox with Take Action
        checkboxes = row.find_elements(By.XPATH, ".//input[@type='checkbox']")
        print(f"   Found {len(checkboxes)} checkboxes")

        if checkboxes:
            checkbox = checkboxes[0]
            print("   ✅ Clicking checkbox...")

            # Scroll to element
            driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
            time.sleep(1)

            # Try JavaScript click
            driver.execute_script("arguments[0].click();", checkbox)
            time.sleep(3)

            print("   Checkbox clicked, checking page change...")

        # After clicking checkbox, look for Take Action button
        take_action_buttons = driver.find_elements(By.XPATH, "//input[@value='Take Action']")
        print(f"   Found {len(take_action_buttons)} Take Action buttons on page")

        if take_action_buttons:
            # Find the enabled one
            for button in take_action_buttons:
                if button.is_enabled():
                    print("   ✅ Found enabled Take Action button")

                    # Scroll to button
                    driver.execute_script("arguments[0].scrollIntoView(true);", button)
                    time.sleep(1)

                    # Store windows before click
                    main_window = driver.current_window_handle
                    windows_before = len(driver.window_handles)

                    # Click the button
                    print("   Clicking Take Action...")
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(5)

                    # Check what happened
                    windows_after = len(driver.window_handles)

                    if windows_after > windows_before:
                        print("   ✅ NEW WINDOW OPENED!")
                        for window in driver.window_handles:
                            if window != main_window:
                                driver.switch_to.window(window)
                                break
                    else:
                        print("   ⚠️ Same window navigation")

                    break

        # Check where we are now
        print("\n5. CHECK CURRENT STATE:")
        print(f"   URL: {driver.current_url}")
        print(f"   Title: {driver.title}")
        print(f"   Windows: {len(driver.window_handles)}")

        # Save screenshot after clicking
        driver.save_screenshot("/tmp/mor_after_click.png")
        print("   📸 After click: /tmp/mor_after_click.png")

        # Check page content
        page_text = driver.find_element(By.TAG_NAME, "body").text

        # Look for manuscript details
        if manuscript_id in page_text:
            print(f"   ✅ Manuscript {manuscript_id} found in page")

        # Look for tabs
        print("\n   📑 LOOKING FOR TABS:")
        tabs = driver.find_elements(By.XPATH, "//a[contains(@class, 'tab') or contains(@href, 'tab')]")
        for i, tab in enumerate(tabs[:10]):
            print(f"      Tab {i}: {tab.text}")

        # Look for referee information
        print("\n   👥 LOOKING FOR REFEREE DETAILS:")

        # Try to find referee tab
        referee_tabs = driver.find_elements(By.XPATH,
            "//a[contains(text(), 'Referee') or contains(text(), 'Reviewer')]")

        if referee_tabs:
            print(f"   Found {len(referee_tabs)} referee tabs")
            print("   Clicking first referee tab...")
            referee_tabs[0].click()
            time.sleep(3)

            # Now look for referee details
            referee_rows = driver.find_elements(By.XPATH,
                "//tr[contains(., 'Invited') or contains(., 'Agreed') or contains(., 'Declined')]")

            print(f"   Found {len(referee_rows)} referee rows")

            for i, row in enumerate(referee_rows[:5]):
                print(f"\n   REFEREE {i+1}:")
                print(f"      {row.text[:200]}")

                # Try to extract cells
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells:
                    for j, cell in enumerate(cells[:5]):
                        if cell.text:
                            print(f"      Cell {j}: {cell.text[:50]}")

        # Final screenshot
        driver.save_screenshot("/tmp/mor_final_state.png")
        print("\n   📸 Final state: /tmp/mor_final_state.png")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

    if driver:
        driver.save_screenshot("/tmp/mor_error.png")

finally:
    if driver:
        print("\nClosing in 15 seconds...")
        time.sleep(15)
        driver.quit()

print("\n" + "="*80)
print("PROPER CLICK TEST COMPLETE")
print("="*80)