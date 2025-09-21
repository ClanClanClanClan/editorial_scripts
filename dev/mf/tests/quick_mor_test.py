#!/usr/bin/env python3
"""
Quick MOR test - verify login and navigation
"""

import sys
import time
import os
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

print("🚀 Starting quick MOR test...")

# Setup Chrome
chrome_options = Options()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(options=chrome_options)
driver.implicitly_wait(10)

try:
    print("📍 Navigating to MOR...")
    driver.get("https://mc.manuscriptcentral.com/mathor")

    print("⏳ Waiting for page load...")
    time.sleep(5)

    # Handle cookie banner
    try:
        reject_btn = driver.find_element(By.ID, "onetrust-reject-all-handler")
        print("🍪 Found cookie banner, rejecting...")
        reject_btn.click()
        time.sleep(2)
    except:
        print("ℹ️ No cookie banner found")

    # Check if login form exists
    try:
        userid_field = driver.find_element(By.ID, "USERID")
        print("✅ Found USERID field")

        password_field = driver.find_element(By.ID, "PASSWORD")
        print("✅ Found PASSWORD field")

        # Enter credentials
        print("📝 Entering credentials...")
        userid_field.send_keys(os.getenv('MOR_EMAIL'))
        password_field.send_keys(os.getenv('MOR_PASSWORD'))

        # Click login
        login_btn = driver.find_element(By.ID, "logInButton")
        print("🔐 Clicking login...")
        login_time = time.time()
        login_btn.click()

        print("⏳ Waiting for login response...")
        time.sleep(5)

        # Check for 2FA
        try:
            token_field = driver.find_element(By.ID, "TOKEN_VALUE")
            print("🔑 2FA required!")

            # Import 2FA handler
            sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src'))
            from core.gmail_verification_wrapper import fetch_latest_verification_code

            print("📧 Fetching 2FA code from Gmail...")
            time.sleep(5)
            code = fetch_latest_verification_code('MOR', max_wait=20, poll_interval=2, start_timestamp=login_time)

            if code:
                print(f"✅ Got code: {code}")
                driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
                driver.execute_script("document.getElementById('VERIFY_BTN').click();")
                time.sleep(8)
            else:
                print("❌ No code received")

        except Exception as e:
            print(f"ℹ️ No 2FA or error: {str(e)[:50]}")

        # Check if we're logged in
        print("🔍 Checking login status...")
        time.sleep(3)

        try:
            ae_link = driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            print("✅ Successfully logged in! Found AE Center link")
        except:
            print("❌ Login may have failed - AE Center not found")
            print(f"Current URL: {driver.current_url}")
            print(f"Page title: {driver.title}")

    except Exception as e:
        print(f"❌ Error finding login form: {e}")
        print(f"Current URL: {driver.current_url}")

except Exception as e:
    print(f"❌ Fatal error: {e}")

finally:
    print("🔚 Closing browser...")
    driver.quit()
    print("✅ Done")