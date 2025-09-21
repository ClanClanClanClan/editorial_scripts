#!/usr/bin/env python3
"""
MOR Login with FRESH 2FA code - wait for email AFTER login
"""

import sys
import os
import time

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.gmail_verification import fetch_latest_verification_code

print("="*60)
print("🔐 MOR LOGIN WITH FRESH 2FA")
print("="*60)

driver = None
try:
    print("\n1. Starting Chrome...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 10)
    print("   ✅ Chrome ready")

    print("\n2. Navigating to MOR...")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
        reject.click()
        time.sleep(2)
        print("   ✅ Cookies rejected")
    except:
        pass

    print("\n3. Recording timestamp BEFORE login...")
    before_login = time.time()
    print(f"   Timestamp: {before_login}")
    print(f"   Time: {time.strftime('%H:%M:%S', time.localtime(before_login))}")

    print("\n4. Entering credentials...")
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    print("\n5. Submitting login (will trigger 2FA email)...")
    driver.find_element(By.ID, "logInButton").click()
    login_time = time.time()

    print("   Waiting for 2FA page to load...")
    time.sleep(5)

    # Check for 2FA
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("   ✅ 2FA page detected")

        print("\n6. Waiting for FRESH verification email...")
        print(f"   Looking for emails after timestamp: {login_time}")

        # Use the fixed gmail_verification function with the login timestamp
        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_time
        )

        if code:
            print(f"\n7. ✅ FRESH CODE RECEIVED: {code}")
            print("   Entering code...")

            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")

            print("   Submitting...")
            verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
            verify_btn.click()

            print("\n8. Waiting for login to complete...")
            time.sleep(10)

            print("\n9. Checking login status...")
            print(f"   Current URL: {driver.current_url}")
            print(f"   Page title: {driver.title}")

            if "Dashboard" in driver.page_source or "Associate Editor" in driver.page_source:
                print("\n✅ LOGIN SUCCESSFUL WITH FRESH CODE!")

                # Try to navigate to AE Center
                print("\n10. Testing navigation...")
                try:
                    ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Editor")
                    ae_link.click()
                    time.sleep(3)
                    print("   ✅ Navigated to AE Center")

                    # Look for manuscript categories
                    links = driver.find_elements(By.TAG_NAME, "a")
                    categories = []
                    for link in links:
                        text = link.text.strip()
                        if text and any(word in text for word in ['Awaiting', 'Overdue', 'Review']):
                            categories.append(text)

                    if categories:
                        print(f"   ✅ Found {len(set(categories))} manuscript categories")
                        for cat in set(categories):
                            print(f"      - {cat}")

                        # Try to open first category
                        print("\n11. Opening first category...")
                        cat_link = driver.find_element(By.LINK_TEXT, list(set(categories))[0])
                        cat_link.click()
                        time.sleep(3)

                        # Check for manuscripts
                        ms_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
                        if ms_rows:
                            print(f"   ✅ Found {len(ms_rows)} manuscripts!")
                            print("\n✨ FULL SUCCESS - Ready for extraction!")
                        else:
                            print("   ⚠️ No manuscripts found in this category")
                    else:
                        print("   ⚠️ No manuscript categories found")
                except Exception as e:
                    print(f"   Navigation error: {e}")
            else:
                print("   ❌ Login failed - not on dashboard")
                print(f"   Page source snippet: {driver.page_source[:500]}")
        else:
            print("\n❌ No verification code received within timeout")
            print("   MOR may have rate limiting or email delay")

    except Exception as e:
        print(f"\n❌ 2FA error: {e}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if driver:
        print("\n" + "="*60)
        print("Keeping browser open for 30 seconds...")
        time.sleep(30)
        driver.quit()
        print("🧹 Browser closed")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)