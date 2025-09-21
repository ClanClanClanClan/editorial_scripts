#!/usr/bin/env python3
"""
Proper Gmail debug with correct parameters
"""

import sys
import time
import os
import re

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

print("="*60)
print("🔍 PROPER GMAIL DEBUG")
print("="*60)

# Import the correct function
from core.gmail_verification import fetch_latest_verification_code

# Test 1: Check recent emails (both read and unread)
print("\n1. Checking ALL recent emails (read and unread)...")
try:
    import json
    from pathlib import Path
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    # Load and refresh token if needed
    token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')
    with open(token_file, 'r') as token:
        creds = Credentials.from_authorized_user_info(json.load(token))

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    # Build service
    service = build('gmail', 'v1', credentials=creds)

    # Search for ALL MOR emails from today
    current_time = int(time.time())
    query = f'from:manuscriptcentral-noreply@clarivate.com after:{current_time - 3600}'  # Last hour
    print(f"   Query: {query}")

    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])
    print(f"   Found {len(messages)} MOR emails in last hour")

    # Check each message
    for i, msg in enumerate(messages[:10], 1):
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()

        # Get details
        internal_date = int(msg_data['internalDate']) // 1000
        snippet = msg_data.get('snippet', '')

        # Check if unread
        labels = msg_data.get('labelIds', [])
        is_unread = 'UNREAD' in labels

        print(f"\n   Email {i}:")
        print(f"      Time: {time.strftime('%H:%M:%S', time.localtime(internal_date))}")
        print(f"      Unread: {'Yes' if is_unread else 'No'}")
        print(f"      Snippet: {snippet[:80]}...")

        # Look for verification code
        code_match = re.search(r'\b(\d{6})\b', snippet)
        if code_match:
            print(f"      ✅ Code found: {code_match.group(1)}")

except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Live test with proper parameters
print("\n2. Testing live MOR login with correct fetch...")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

driver = None
try:
    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)

    # Navigate to MOR
    print("   Navigating to MOR...")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Reject cookies
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
        reject.click()
        time.sleep(2)
    except:
        pass

    # Login
    print("   Logging in...")
    email_field = driver.find_element(By.ID, "USERID")
    email_field.send_keys(os.getenv('MOR_EMAIL'))

    password_field = driver.find_element(By.ID, "PASSWORD")
    password_field.send_keys(os.getenv('MOR_PASSWORD'))

    # Record login time
    login_time = time.time()
    print(f"   Login time: {time.strftime('%H:%M:%S', time.localtime(login_time))}")

    login_btn = driver.find_element(By.ID, "logInButton")
    login_btn.click()
    time.sleep(5)

    # Check for 2FA
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("   ✅ 2FA page reached")

        # Try fetching with correct parameter
        print("   Fetching code with correct parameters...")
        print(f"   Using start_timestamp={int(login_time)}")

        code = fetch_latest_verification_code(
            journal_code='MOR',
            max_wait=30,
            poll_interval=3,
            start_timestamp=login_time
        )

        if code:
            print(f"   ✅ SUCCESS! Got code: {code}")

            # Enter and submit
            token_field.send_keys(code)
            submit = driver.find_element(By.ID, "submitButton")
            submit.click()
            time.sleep(5)

            # Check if login succeeded
            if "Associate Editor" in driver.page_source:
                print("   ✅ Login successful!")
            else:
                print("   ⚠️  Login status uncertain")
        else:
            print("   ❌ No code fetched")
            print("   Checking manually for any codes...")

            # Manual check
            service = build('gmail', 'v1', credentials=creds)
            query = f'from:manuscriptcentral-noreply@clarivate.com after:{int(login_time)}'
            results = service.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])
            print(f"   Found {len(messages)} emails since login")

            if messages:
                msg_data = service.users().messages().get(userId='me', id=messages[0]['id']).execute()
                snippet = msg_data.get('snippet', '')
                code_match = re.search(r'\b(\d{6})\b', snippet)
                if code_match:
                    print(f"   Manual check found code: {code_match.group(1)}")

    except Exception as e:
        print(f"   No 2FA or error: {e}")

except Exception as e:
    print(f"   ❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
finally:
    if driver:
        driver.quit()
        print("   🧹 Browser closed")

print("\n" + "="*60)
print("DEBUG COMPLETE")
print("="*60)