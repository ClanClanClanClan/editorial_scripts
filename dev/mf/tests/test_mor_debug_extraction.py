#!/usr/bin/env python3
"""
MOR DEBUG EXTRACTION - Find exact hang point
"""

import sys
import os
import time
import re

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from core.gmail_verification import fetch_latest_verification_code

print("="*80)
print("🔍 MOR DEBUG - FIND EXACT HANG POINT")
print("="*80)

driver = None
try:
    # Setup
    print("\n1. Quick Setup & Login")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, 10)  # Shorter timeout for debugging

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
        print("   2FA detected, waiting for code...")
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

    # Click first manuscript
    print("\n4. Click First Manuscript")
    manuscript_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
    print(f"   Found {len(manuscript_rows)} manuscripts")

    if manuscript_rows:
        row = manuscript_rows[0]
        row_text = row.text

        # Extract ID
        mor_match = re.search(r'MOR-\d{4}-\d+', row_text)
        if mor_match:
            manuscript_id = mor_match.group()
            print(f"   Processing: {manuscript_id}")

        # Find clickable element
        action_button = None
        try:
            # MOR uses INPUT element
            action_button = row.find_element(By.XPATH, ".//input[@value='Take Action']")
            print("   Found INPUT Take Action button")
        except:
            try:
                # Try link
                action_button = row.find_element(By.XPATH, ".//a[contains(text(), 'Take Action')]")
                print("   Found A Take Action link")
            except:
                try:
                    # Try check icon
                    action_button = row.find_element(By.XPATH, ".//img[contains(@src, 'check')]/parent::*")
                    print("   Found check icon")
                except:
                    print("   ❌ No clickable element found!")

        if action_button:
            main_window = driver.current_window_handle
            action_button.click()
            time.sleep(5)

            # Check window state
            if len(driver.window_handles) > 1:
                print("   ✅ Opened in popup")
                for window in driver.window_handles:
                    if window != main_window:
                        driver.switch_to.window(window)
                        break
            else:
                print("   ⚠️ Opened in same window")

            print("\n5. DEBUG REFEREE EXTRACTION")
            print("-"*60)

            # Step 1: Look for referee tabs
            print("\n   Step 1: Looking for referee tabs...")
            referee_tabs = driver.find_elements(By.XPATH,
                "//a[contains(text(), 'Referee') or contains(text(), 'Reviewer')] | "
                "//img[contains(@src, 'referee')] | "
                "//td[contains(@class, 'tab') and contains(text(), 'Referee')]")

            print(f"   Found {len(referee_tabs)} referee tabs")
            for i, tab in enumerate(referee_tabs[:3]):
                print(f"      Tab {i}: {tab.tag_name} - {tab.text[:50] if tab.text else 'No text'}")

            # Step 2: Try clicking referee tab with timeout
            if referee_tabs:
                print("\n   Step 2: Clicking referee tab...")
                try:
                    # Use shorter timeout
                    referee_tabs[0].click()
                    print("   ✅ Clicked referee tab")
                    time.sleep(3)
                except Exception as e:
                    print(f"   ❌ Error clicking tab: {str(e)[:100]}")

            # Step 3: Look for ORDER selects
            print("\n   Step 3: Looking for ORDER selects...")
            order_selects = driver.find_elements(By.XPATH,
                "//select[contains(@name,'ORDER')]")
            print(f"   Found {len(order_selects)} ORDER selects")

            # Step 4: Look for referee rows
            print("\n   Step 4: Looking for referee rows...")

            # Try multiple patterns
            patterns = [
                "//tr[contains(., 'Invited') or contains(., 'Agreed') or contains(., 'Declined')]",
                "//tr[contains(@class, 'referee')]",
                "//tr[.//img[contains(@src, 'mailpopup')]]",
                "//tr[.//select[contains(@name, 'ORDER')]]"
            ]

            for pattern in patterns:
                rows = driver.find_elements(By.XPATH, pattern)
                if rows:
                    print(f"   Pattern found {len(rows)} rows: {pattern[:50]}")
                    for i, row in enumerate(rows[:2]):
                        print(f"      Row {i}: {row.text[:100] if row.text else 'No text'}")

            # Step 5: Check page source
            print("\n   Step 5: Checking page source for referee indicators...")
            page_text = driver.find_element(By.TAG_NAME, "body").text

            indicators = ['Invited', 'Agreed', 'Declined', 'Complete', 'Referee', 'Reviewer']
            for indicator in indicators:
                count = page_text.count(indicator)
                if count > 0:
                    print(f"   '{indicator}' appears {count} times")

            # Step 6: Look for email links
            print("\n   Step 6: Looking for email elements...")
            email_links = driver.find_elements(By.XPATH,
                "//a[contains(@href, 'mailpopup') or contains(@onclick, 'mailpopup')]")
            print(f"   Found {len(email_links)} email popup links")

            # Step 7: Check for iframes
            print("\n   Step 7: Checking for iframes...")
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print(f"   Found {len(iframes)} iframes")

            # Step 8: Get current URL
            print("\n   Step 8: Current state:")
            print(f"   URL: {driver.current_url}")
            print(f"   Title: {driver.title}")
            print(f"   Windows: {len(driver.window_handles)}")

            # Save screenshot
            driver.save_screenshot("/tmp/mor_debug_referee_page.png")
            print("\n   📸 Screenshot saved: /tmp/mor_debug_referee_page.png")

            # Try extracting any visible data
            print("\n   Step 9: Extracting any visible referee data...")

            # Find any table rows that might contain referee info
            all_rows = driver.find_elements(By.TAG_NAME, "tr")
            referee_count = 0
            for row in all_rows:
                row_text = row.text
                if row_text and any(status in row_text for status in ['Invited', 'Agreed', 'Declined', 'Complete']):
                    referee_count += 1
                    print(f"\n   REFEREE {referee_count}:")
                    print(f"      {row_text[:200]}")

                    # Try to extract cells
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) > 1:
                        print(f"      Name cell: {cells[1].text if len(cells) > 1 else 'N/A'}")
                        print(f"      Status cell: {cells[2].text if len(cells) > 2 else 'N/A'}")

            print(f"\n   Total referees found: {referee_count}")

except TimeoutException as e:
    print(f"\n❌ TIMEOUT: {e}")
    driver.save_screenshot("/tmp/mor_debug_timeout.png")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

    if driver:
        driver.save_screenshot("/tmp/mor_debug_error.png")

finally:
    if driver:
        print("\nClosing in 10 seconds...")
        time.sleep(10)
        driver.quit()

print("\n" + "="*80)
print("DEBUG COMPLETE")
print("="*80)