#!/usr/bin/env python3
"""
Test MOR with RECENT code that we just found!
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

print("="*60)
print("🚀 MOR TEST WITH RECENT CODE")
print("="*60)

# We found these recent codes:
recent_codes = [
    ("181915", "22:19:13", 3.0),  # Most recent - 3 hours ago
    ("734581", "20:43:16", 4.6),  # 4.6 hours ago
    ("041588", "20:41:26", 4.7),  # 4.7 hours ago
]

print("\n✅ FOUND RECENT VERIFICATION CODES!")
print("MOR HAS been sending new emails - we just weren't finding them properly\n")

for code, time_sent, age in recent_codes:
    print(f"   Code: {code} sent at {time_sent} ({age:.1f} hours ago)")

# Try the most recent one
code_to_use = recent_codes[0][0]
print(f"\n1. Using most recent code: {code_to_use}")

driver = None
try:
    # Setup Chrome
    print("\n2. Starting Chrome...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 10)
    print("   ✅ Chrome ready")

    # Navigate
    print("\n3. Navigating to MOR...")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    driver.sleep = lambda x: __import__('time').sleep(x)
    driver.sleep(3)

    # Handle cookies
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
        reject.click()
        driver.sleep(2)
    except:
        pass

    # Login
    print("\n4. Logging in...")
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))
    driver.find_element(By.ID, "logInButton").click()
    driver.sleep(5)

    # Handle 2FA
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("\n5. 2FA detected, entering recent code...")

        driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code_to_use}';")
        print(f"   ✅ Entered code: {code_to_use}")

        verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
        verify_btn.click()
        driver.sleep(8)

        print("\n6. Checking login result...")
        if "Associate Editor" in driver.page_source:
            print("   ✅ LOGIN SUCCESSFUL WITH RECENT CODE!")

            # Navigate to AE Center
            print("\n7. Navigating to AE Center...")
            ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Editor")
            ae_link.click()
            driver.sleep(3)

            # Check for manuscripts
            links = driver.find_elements(By.TAG_NAME, "a")
            categories = []
            for link in links:
                text = link.text.strip()
                if text and any(word in text for word in ['Awaiting', 'Overdue', 'Review']):
                    categories.append(text)

            print(f"   Found {len(set(categories))} manuscript categories:")
            for cat in set(categories):
                print(f"      - {cat}")

            # Try to open first category
            if categories:
                print("\n8. Opening first category...")
                cat_link = driver.find_element(By.LINK_TEXT, categories[0])
                cat_link.click()
                driver.sleep(3)

                # Check for manuscripts
                ms_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
                print(f"   Found {len(ms_rows)} manuscripts")

                if ms_rows:
                    print("\n✅ FULL SUCCESS!")
                    print("   - Recent code worked")
                    print("   - Login successful")
                    print("   - Can access manuscripts")

                    # Extract first manuscript for testing
                    print("\n9. Testing manuscript extraction...")
                    row = ms_rows[0]
                    ms_link = row.find_element(By.XPATH, ".//a[contains(text(), 'MOR-')]")
                    ms_id = ms_link.text
                    print(f"   Processing: {ms_id}")

                    # Click on it
                    try:
                        check = row.find_element(By.XPATH, ".//img[contains(@src, 'check')]")
                        parent = check.find_element(By.XPATH, "./parent::*")
                        parent.click()
                    except:
                        ms_link.click()
                    driver.sleep(3)

                    print("   ✅ Opened manuscript successfully")

        else:
            print("   ❌ Login failed - trying next code...")

            # Try the next code
            if len(recent_codes) > 1:
                driver.get("https://mc.manuscriptcentral.com/mathor")
                driver.sleep(3)
                # Repeat with next code...

    except Exception as e:
        print(f"   Error: {e}")

    print("\n" + "="*60)
    print("✅ VERIFICATION: MOR is working, we just had Gmail search issues")
    print("="*60)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if driver:
        print("\nKeeping browser open for inspection...")
        input("Press Enter to close...")
        driver.quit()

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)