#!/usr/bin/env python3
"""
Test live Gmail checking during MOR login
"""

import sys
import os
import time
import re

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# Setup Gmail service
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

print("="*60)
print("🔍 LIVE GMAIL TEST DURING LOGIN")
print("="*60)

# Load Gmail credentials
token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')
with open(token_file, 'r') as f:
    creds = Credentials.from_authorized_user_info(json.load(f))

if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(token_file, 'w') as f:
        f.write(creds.to_json())

service = build('gmail', 'v1', credentials=creds)

# First, mark all existing MOR emails as read to clear the slate
print("\n1. Marking existing MOR emails as read...")
try:
    results = service.users().messages().list(
        userId='me',
        q='from:onbehalfof@manuscriptcentral.com is:unread',
        maxResults=100
    ).execute()

    messages = results.get('messages', [])
    if messages:
        print(f"   Found {len(messages)} unread MOR emails, marking as read...")
        for msg in messages:
            service.users().messages().modify(
                userId='me',
                id=msg['id'],
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
        print("   ✅ All marked as read")
    else:
        print("   No unread MOR emails")
except Exception as e:
    print(f"   Error: {e}")

# Now start the login process
print("\n2. Starting MOR login...")
driver = None

try:
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)

    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Reject cookies
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
        reject.click()
        time.sleep(2)
    except:
        pass

    # Enter credentials
    print("   Entering credentials...")
    email_field = driver.find_element(By.ID, "USERID")
    email_field.send_keys(os.getenv('MOR_EMAIL'))

    password_field = driver.find_element(By.ID, "PASSWORD")
    password_field.send_keys(os.getenv('MOR_PASSWORD'))

    login_time = int(time.time())
    print(f"   Login timestamp: {login_time}")

    login_btn = driver.find_element(By.ID, "logInButton")
    login_btn.click()

    print("\n3. Waiting for 2FA page...")
    time.sleep(5)

    # Check if 2FA page appears
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("   ✅ 2FA page loaded")

        print("\n4. Monitoring Gmail for new emails...")
        found_code = None
        max_attempts = 20

        for attempt in range(max_attempts):
            print(f"   Attempt {attempt + 1}/{max_attempts}...")

            # Search for NEW emails (using is:unread to only get new ones)
            query = f'from:onbehalfof@manuscriptcentral.com is:unread after:{login_time - 10}'
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=5
            ).execute()

            messages = results.get('messages', [])
            print(f"      Found {len(messages)} new unread emails")

            if messages:
                for msg in messages:
                    msg_data = service.users().messages().get(
                        userId='me',
                        id=msg['id']
                    ).execute()

                    snippet = msg_data.get('snippet', '')
                    print(f"      Email snippet: {snippet[:80]}...")

                    # Look for verification code
                    code_match = re.search(r'\b(\d{6})\b', snippet)
                    if code_match:
                        found_code = code_match.group(1)
                        print(f"      ✅ FOUND CODE: {found_code}")
                        break

                if found_code:
                    break

            time.sleep(3)

        if found_code:
            print(f"\n5. Entering 2FA code: {found_code}")
            token_field.send_keys(found_code)

            submit_btn = driver.find_element(By.ID, "submitButton")
            submit_btn.click()
            time.sleep(5)

            print("\n6. Checking login success...")
            print(f"   Current URL: {driver.current_url}")
            print(f"   Page title: {driver.title}")

            # Check page content
            page_text = driver.find_element(By.TAG_NAME, "body").text
            if "Associate Editor" in page_text:
                print("   ✅ LOGIN SUCCESSFUL! Found Associate Editor")
            elif "Dashboard" in page_text:
                print("   ✅ LOGIN SUCCESSFUL! Found Dashboard")
            else:
                print("   ⚠️  Login status uncertain")
        else:
            print("\n   ❌ No verification code found")

    except Exception as e:
        print(f"   No 2FA or error: {e}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if driver:
        driver.quit()
        print("\n🧹 Browser closed")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)