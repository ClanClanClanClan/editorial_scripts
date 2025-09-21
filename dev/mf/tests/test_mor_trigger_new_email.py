#!/usr/bin/env python3
"""
Try to trigger a new MOR verification email
"""

import sys
import os
import time
import re

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

print("="*60)
print("🔄 TRIGGERING NEW MOR VERIFICATION EMAIL")
print("="*60)

# Gmail setup
token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')
with open(token_file, 'r') as f:
    creds = Credentials.from_authorized_user_info(json.load(f))

if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build('gmail', 'v1', credentials=creds)

# Get baseline
print("\n1. Getting baseline emails...")
baseline_query = 'from:onbehalfof@manuscriptcentral.com subject:"Verification Code"'
baseline = service.users().messages().list(
    userId='me',
    q=baseline_query,
    maxResults=10
).execute()

baseline_ids = {msg['id'] for msg in baseline.get('messages', [])}
print(f"   Baseline: {len(baseline_ids)} existing emails")

# Try multiple strategies
strategies = [
    ("Incognito mode", ["--incognito"]),
    ("Clear cookies", ["--disable-features=SameSiteByDefaultCookies"]),
    ("New user profile", ["--user-data-dir=/tmp/chrome-mor-test"])
]

for strategy_name, extra_args in strategies:
    print(f"\n2. Trying strategy: {strategy_name}")

    driver = None
    try:
        # Setup Chrome with strategy
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        for arg in extra_args:
            chrome_options.add_argument(arg)

        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)

        # Navigate
        print("   Navigating to MOR...")
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
        print("   Logging in...")
        driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
        driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

        login_time = int(time.time())
        driver.find_element(By.ID, "logInButton").click()

        # Wait for 2FA
        time.sleep(5)

        # Check if 2FA appeared
        try:
            token_field = driver.find_element(By.ID, "TOKEN_VALUE")
            print("   ✅ 2FA page appeared")

            # Wait for email
            print("   Waiting 15 seconds for email...")
            time.sleep(15)

            # Check for new email
            current = service.users().messages().list(
                userId='me',
                q=baseline_query,
                maxResults=10
            ).execute()

            current_messages = current.get('messages', [])
            new_messages = [msg for msg in current_messages if msg['id'] not in baseline_ids]

            if new_messages:
                print(f"   ✅ SUCCESS! {len(new_messages)} new emails received")

                # Get the code
                msg_data = service.users().messages().get(
                    userId='me',
                    id=new_messages[0]['id']
                ).execute()

                snippet = msg_data.get('snippet', '')
                code_match = re.search(r'\b(\d{6})\b', snippet)

                if code_match:
                    code = code_match.group(1)
                    print(f"   ✅ New code: {code}")

                    # Try to login
                    driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
                    verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
                    verify_btn.click()
                    time.sleep(8)

                    # Check result
                    if "Associate Editor" in driver.page_source:
                        print("   ✅ LOGIN SUCCESSFUL WITH NEW CODE!")
                        break
                    else:
                        print("   Login status uncertain")
            else:
                print("   ❌ No new email received")

        except Exception as e:
            print(f"   No 2FA or error: {e}")

    except Exception as e:
        print(f"   Strategy failed: {e}")
    finally:
        if driver:
            driver.quit()

    # Wait between strategies
    time.sleep(30)

# Final check
print("\n3. Final check for new emails...")
final = service.users().messages().list(
    userId='me',
    q=baseline_query,
    maxResults=10
).execute()

final_messages = final.get('messages', [])
new_total = len([msg for msg in final_messages if msg['id'] not in baseline_ids])

if new_total > 0:
    print(f"   ✅ Successfully triggered {new_total} new verification emails")
else:
    print("   ❌ Could not trigger new verification emails")
    print("   MOR appears to have strict rate limiting")
    print("   Try again later or contact support")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)