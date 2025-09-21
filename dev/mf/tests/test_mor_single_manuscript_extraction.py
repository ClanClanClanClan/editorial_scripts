#!/usr/bin/env python3
"""
MOR SINGLE MANUSCRIPT EXTRACTION - GET ONE MANUSCRIPT PROPERLY
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
print("🎯 MOR SINGLE MANUSCRIPT - EXTRACT ONE PROPERLY")
print("="*80)

driver = None
try:
    # Setup
    print("\n1. Browser Setup")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, 15)
    print("   ✅ Chrome ready")

    # Navigate
    print("\n2. Navigate to MOR")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
        reject.click()
        time.sleep(2)
        print("   ✅ Cookies handled")
    except:
        pass

    # Login
    print("\n3. Login")
    wait.until(EC.presence_of_element_located((By.ID, "USERID")))
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    login_time = time.time()
    driver.find_element(By.ID, "logInButton").click()
    print("   ✅ Login submitted")

    # 2FA
    time.sleep(5)
    if "TOKEN_VALUE" in driver.page_source or "verification" in driver.page_source.lower():
        print("\n4. 2FA Handling")
        print("   ⏳ Waiting 15 seconds for NEW email...")
        time.sleep(15)

        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_time + 5
        )

        if code:
            print(f"   ✅ Got code: {code}")
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")

            try:
                driver.find_element(By.ID, "VERIFY_BTN").click()
            except:
                driver.execute_script("document.getElementById('VERIFY_BTN').click();")

            time.sleep(10)

    # Navigate to AE Center
    print("\n5. Navigate to AE Center")
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if "associate editor" in link.text.lower():
            link.click()
            time.sleep(5)
            print("   ✅ In AE Center")
            break

    # Click on "Awaiting Reviewer Reports"
    print("\n6. Navigate to 'Awaiting Reviewer Reports'")
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if "Awaiting Reviewer Reports" in link.text:
            link.click()
            time.sleep(5)
            print("   ✅ In category")
            break

    # Find first manuscript
    print("\n7. Extract First Manuscript")
    manuscript_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
    print(f"   Found {len(manuscript_rows)} manuscripts")

    if manuscript_rows:
        row = manuscript_rows[0]
        row_text = row.text

        # Extract ID
        mor_match = re.search(r'MOR-\d{4}-\d+', row_text)
        if mor_match:
            manuscript_id = mor_match.group()
            print(f"\n   📄 Manuscript: {manuscript_id}")

            # Find Take Action button
            take_action = None
            try:
                take_action = row.find_element(By.XPATH, ".//a[contains(text(), 'Take Action')]")
            except:
                # Try check icon
                try:
                    take_action = row.find_element(By.XPATH, ".//img[contains(@src, 'check')]/parent::*")
                except:
                    pass

            if take_action:
                # Store main window
                main_window = driver.current_window_handle

                # Click manuscript
                take_action.click()
                time.sleep(5)

                # Extract data
                data = {"manuscript_id": manuscript_id}

                # Check if popup opened
                if len(driver.window_handles) > 1:
                    print("      ✅ Opened in popup")
                    for window in driver.window_handles:
                        if window != main_window:
                            driver.switch_to.window(window)
                            break
                else:
                    print("      ⚠️ Opened in same window")

                # Get page text
                page_text = driver.find_element(By.TAG_NAME, "body").text

                # Extract title
                title_match = re.search(r'Title[:\s]+(.+?)[\n\r]', page_text, re.IGNORECASE)
                if title_match:
                    data["title"] = title_match.group(1).strip()
                    print(f"      Title: {data['title'][:100]}...")

                # Extract authors/emails
                emails = re.findall(r'[\w.+-]+@[\w.-]+\.[a-z]+', page_text, re.IGNORECASE)
                if emails:
                    data["emails"] = list(set(emails))
                    print(f"      Emails: {len(data['emails'])} found")
                    for email in data["emails"][:3]:
                        print(f"         - {email}")

                # Look for referees
                print("\n      📋 REFEREES:")

                # Click on Referee tab if available
                for link in driver.find_elements(By.TAG_NAME, "a"):
                    if "Referee" in link.text or "Reviewer" in link.text:
                        link.click()
                        time.sleep(3)
                        print("         ✅ Clicked referee tab")
                        break

                # Find referee rows
                referee_rows = driver.find_elements(By.XPATH,
                    "//tr[contains(., 'Invited') or contains(., 'Agreed') or contains(., 'Declined')]")

                data["referees"] = []
                for i, ref_row in enumerate(referee_rows[:5], 1):
                    ref_text = ref_row.text
                    ref_data = {"row": i, "text": ref_text[:200]}

                    # Extract status
                    for status in ['Invited', 'Agreed', 'Declined', 'Complete']:
                        if status in ref_text:
                            ref_data["status"] = status
                            break

                    # Extract name from cells
                    cells = ref_row.find_elements(By.TAG_NAME, "td")
                    if len(cells) > 1:
                        ref_data["name"] = cells[1].text.strip()

                    data["referees"].append(ref_data)
                    print(f"         Referee {i}: {ref_data.get('name', 'Unknown')} - {ref_data.get('status', 'Unknown')}")

                # Save results
                print("\n   📊 EXTRACTION RESULTS:")
                print(json.dumps(data, indent=2))

                output_file = f"/tmp/mor_single_manuscript_{int(time.time())}.json"
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"\n   💾 Saved to: {output_file}")

                # Close popup if open
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(main_window)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

    if driver:
        driver.save_screenshot("/tmp/mor_single_error.png")

finally:
    if driver:
        print("\nClosing in 10 seconds...")
        time.sleep(10)
        driver.quit()

print("\n" + "="*80)
print("SINGLE MANUSCRIPT EXTRACTION COMPLETE")
print("="*80)