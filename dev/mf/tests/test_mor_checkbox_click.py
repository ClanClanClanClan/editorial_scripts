#!/usr/bin/env python3
"""
MOR CHECKBOX + TAKE ACTION - Two-step clicking process
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from core.gmail_verification import fetch_latest_verification_code

print("="*80)
print("🎯 MOR CHECKBOX + TAKE ACTION - PROPER TWO-STEP PROCESS")
print("="*80)

driver = None
results = []

try:
    # Setup with stealth mode
    print("\n1. Setup & Login")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(60)
    wait = WebDriverWait(driver, 20)
    actions = ActionChains(driver)

    # Navigate and login
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        reject = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler")))
        reject.click()
        time.sleep(2)
        print("   Cookies rejected")
    except:
        print("   No cookie banner")

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
        time.sleep(15)  # Wait for NEW email

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

    # Method 1: Direct link click with JavaScript
    ae_link = None
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if "associate editor" in link.text.lower():
            ae_link = link
            break

    if ae_link:
        # Use JavaScript to click
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

    # Process manuscripts
    print("\n4. PROCESS MANUSCRIPTS WITH CHECKBOX METHOD")

    manuscript_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
    print(f"   Found {len(manuscript_rows)} manuscripts")

    for idx, row in enumerate(manuscript_rows[:2]):  # Process first 2 only
        print(f"\n   === MANUSCRIPT {idx+1} ===")

        try:
            # Extract manuscript ID
            row_text = row.text
            mor_match = re.search(r'MOR-\d{4}-\d+', row_text)
            manuscript_id = mor_match.group() if mor_match else f"Unknown_{idx}"
            print(f"   ID: {manuscript_id}")

            # Extract referee summary from table
            lines = row_text.split('\n')
            for line in lines:
                if 'active' in line or 'invited' in line or 'agreed' in line or 'declined' in line:
                    print(f"   Table summary: {line}")

            # Step 1: Find and click checkbox
            checkboxes = row.find_elements(By.XPATH, ".//input[@type='checkbox']")

            if checkboxes:
                print(f"   Found {len(checkboxes)} checkboxes")
                checkbox = checkboxes[0]

                # Scroll to checkbox
                driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                time.sleep(1)

                # Click checkbox with JavaScript
                driver.execute_script("arguments[0].click();", checkbox)
                print("   ✅ Checkbox clicked")
                time.sleep(2)

                # Step 2: Find and click Take Action button
                # The button should now be enabled
                take_action_buttons = driver.find_elements(By.XPATH, "//input[@value='Take Action']")

                for button in take_action_buttons:
                    if button.is_enabled():
                        print("   Found enabled Take Action button")

                        # Store current windows
                        main_window = driver.current_window_handle
                        windows_before = len(driver.window_handles)

                        # Click button with JavaScript
                        driver.execute_script("arguments[0].click();", button)
                        print("   ✅ Take Action clicked")
                        time.sleep(5)

                        # Check if new window opened
                        windows_after = len(driver.window_handles)

                        if windows_after > windows_before:
                            print("   ✅ NEW WINDOW OPENED!")

                            # Switch to new window
                            for window in driver.window_handles:
                                if window != main_window:
                                    driver.switch_to.window(window)
                                    break

                            print(f"   In manuscript window: {driver.title}")

                            # Extract referee data
                            print("\n   EXTRACTING REFEREE DATA:")

                            # Look for referee tab
                            referee_tabs = driver.find_elements(By.XPATH,
                                "//a[contains(text(), 'Referee') or contains(text(), 'Reviewer')]")

                            if referee_tabs:
                                print(f"   Found referee tab, clicking...")
                                driver.execute_script("arguments[0].click();", referee_tabs[0])
                                time.sleep(3)

                            # Extract referee information
                            referee_data = []

                            # Look for referee rows
                            referee_rows = driver.find_elements(By.XPATH,
                                "//tr[contains(., 'Invited') or contains(., 'Agreed') or contains(., 'Declined')]")

                            for i, ref_row in enumerate(referee_rows[:5]):
                                ref_text = ref_row.text
                                if ref_text:
                                    referee_info = {
                                        "index": i+1,
                                        "text": ref_text[:200]
                                    }

                                    # Extract cells
                                    cells = ref_row.find_elements(By.TAG_NAME, "td")
                                    if len(cells) > 2:
                                        referee_info["name"] = cells[1].text if cells[1].text else "Unknown"
                                        referee_info["status"] = cells[2].text if cells[2].text else "Unknown"

                                    referee_data.append(referee_info)
                                    print(f"      Referee {i+1}: {referee_info.get('name', 'Unknown')} - {referee_info.get('status', 'Unknown')}")

                            # Save result
                            manuscript_result = {
                                "manuscript_id": manuscript_id,
                                "referees": referee_data,
                                "referee_count": len(referee_data)
                            }
                            results.append(manuscript_result)

                            # Close popup and return to main window
                            driver.close()
                            driver.switch_to.window(main_window)
                            print(f"   ✅ Extracted {len(referee_data)} referees")
                            time.sleep(2)

                        else:
                            print("   ⚠️ No new window - same page navigation")

                        break  # Exit button loop
            else:
                print("   ❌ No checkbox found in row")

        except Exception as e:
            print(f"   ❌ Error processing manuscript: {str(e)[:100]}")

            # Return to main window if needed
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[0])

    # Save results
    print("\n5. SAVING RESULTS")
    output_file = f"/tmp/mor_checkbox_results_{int(time.time())}.json"
    with open(output_file, "w") as f:
        json.dump({
            "total_manuscripts": len(manuscript_rows),
            "processed": len(results),
            "manuscripts": results
        }, f, indent=2)
    print(f"   ✅ Results saved to: {output_file}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

    if driver:
        driver.save_screenshot("/tmp/mor_checkbox_error.png")

finally:
    if driver:
        print("\nClosing in 10 seconds...")
        time.sleep(10)
        driver.quit()

print("\n" + "="*80)
print("CHECKBOX TEST COMPLETE")
print("="*80)