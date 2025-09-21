#!/usr/bin/env python3
"""
MOR Fresh Login Attempt - Trigger new email
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

import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

print("="*60)
print("🔄 MOR FRESH LOGIN ATTEMPT")
print("="*60)

# Gmail setup
token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')
with open(token_file, 'r') as f:
    creds = Credentials.from_authorized_user_info(json.load(f))

if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build('gmail', 'v1', credentials=creds)

# Get baseline
print("\n1. Getting email baseline...")
baseline = service.users().messages().list(
    userId='me',
    q='from:onbehalfof@manuscriptcentral.com',
    maxResults=50
).execute()

baseline_ids = {msg['id'] for msg in baseline.get('messages', [])}
print(f"   Baseline: {len(baseline_ids)} existing emails")

# Start Chrome
print("\n2. Starting Chrome (visible for debugging)...")
chrome_options = Options()
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
# Run visible for debugging
driver = webdriver.Chrome(options=chrome_options)
driver.set_page_load_timeout(30)
driver.implicitly_wait(10)
wait = WebDriverWait(driver, 10)
print("   ✅ Chrome ready")

try:
    # Navigate
    print("\n3. Navigating to MOR...")
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

    # Login
    print("\n4. Logging in...")
    email_field = driver.find_element(By.ID, "USERID")
    email_field.clear()
    email_field.send_keys(os.getenv('MOR_EMAIL'))

    password_field = driver.find_element(By.ID, "PASSWORD")
    password_field.clear()
    password_field.send_keys(os.getenv('MOR_PASSWORD'))

    login_time = int(time.time())
    print(f"   Login timestamp: {login_time}")
    print(f"   Time: {time.strftime('%H:%M:%S', time.localtime(login_time))}")

    login_btn = driver.find_element(By.ID, "logInButton")
    login_btn.click()

    print("\n5. Waiting for 2FA page...")
    time.sleep(5)

    # Check for 2FA
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("   ✅ 2FA page loaded")

        print("\n6. Monitoring for NEW verification email...")
        print("   Checking every 3 seconds for 60 seconds...")

        found_new_code = False
        for check in range(20):  # 20 checks * 3 seconds = 60 seconds
            print(f"   Check {check + 1}/20...")

            # Get current emails
            current = service.users().messages().list(
                userId='me',
                q='from:onbehalfof@manuscriptcentral.com',
                maxResults=50
            ).execute()

            current_messages = current.get('messages', [])
            new_messages = [msg for msg in current_messages if msg['id'] not in baseline_ids]

            if new_messages:
                print(f"\n   ✅ NEW EMAIL DETECTED!")

                # Get the new email
                msg_data = service.users().messages().get(
                    userId='me',
                    id=new_messages[0]['id']
                ).execute()

                internal_date = int(msg_data.get('internalDate', 0)) // 1000
                time_diff = internal_date - login_time

                snippet = msg_data.get('snippet', '')
                code_match = re.search(r'\b(\d{6})\b', snippet)

                if code_match:
                    code = code_match.group(1)
                    print(f"   ✅ NEW CODE: {code}")
                    print(f"   Email arrived {time_diff} seconds after login")

                    # Enter code
                    print("\n7. Entering fresh code...")
                    driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")

                    # Submit
                    verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
                    verify_btn.click()
                    time.sleep(8)

                    # Check result
                    print("\n8. Checking login result...")
                    if "Associate Editor" in driver.page_source:
                        print("   ✅ LOGIN SUCCESSFUL WITH FRESH CODE!")
                        found_new_code = True
                    else:
                        print("   ❌ Login failed despite fresh code")

                    break

            time.sleep(3)

        if not found_new_code:
            print("\n   ❌ No new verification email received")
            print("   MOR has rate limiting in effect")

            # Try most recent code anyway
            print("\n7. Trying most recent existing code...")
            results = service.users().messages().list(
                userId='me',
                q='from:onbehalfof@manuscriptcentral.com subject:"Verification Code"',
                maxResults=1
            ).execute()

            if results.get('messages'):
                msg_data = service.users().messages().get(
                    userId='me',
                    id=results['messages'][0]['id']
                ).execute()

                snippet = msg_data.get('snippet', '')
                code_match = re.search(r'\b(\d{6})\b', snippet)

                if code_match:
                    code = code_match.group(1)
                    print(f"   Using existing code: {code}")

                    driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
                    verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
                    verify_btn.click()
                    time.sleep(8)

                    if "Associate Editor" in driver.page_source:
                        print("   ✅ Old code still worked!")
                    else:
                        print("   ❌ Old code expired")

    except Exception as e:
        print(f"   Error or no 2FA: {e}")

    print("\n9. Final status...")
    print(f"   Current URL: {driver.current_url}")
    print(f"   Page title: {driver.title}")

    # Keep browser open for inspection
    print("\n" + "="*60)
    print("Browser will remain open for inspection")
    print("Check if login succeeded manually")
    input("Press Enter to close browser...")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    driver.quit()
    print("\n🧹 Browser closed")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)