#!/usr/bin/env python3
"""
COMPREHENSIVE Gmail Debug
"""

import sys
import os
import time
import re

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

print("="*60)
print("🔍 COMPREHENSIVE GMAIL DEBUG")
print("="*60)

# Test 1: Can we connect to Gmail?
print("\n✅ TEST 1: Gmail API Connection")
try:
    token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')
    with open(token_file, 'r') as f:
        creds = Credentials.from_authorized_user_info(json.load(f))

    if creds.expired and creds.refresh_token:
        print("   Refreshing token...")
        creds.refresh(Request())
        with open(token_file, 'w') as f:
            f.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    profile = service.users().getProfile(userId='me').execute()
    print(f"   ✅ Connected to: {profile.get('emailAddress')}")
    print(f"   Total messages: {profile.get('messagesTotal')}")
except Exception as e:
    print(f"   ❌ Connection failed: {e}")
    sys.exit(1)

# Test 2: Can we see some emails?
print("\n✅ TEST 2: Reading Recent Emails")
try:
    results = service.users().messages().list(userId='me', maxResults=5).execute()
    messages = results.get('messages', [])
    print(f"   ✅ Can read emails - found {len(messages)} recent messages")

    for i, msg in enumerate(messages[:3], 1):
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = msg_data['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
        from_addr = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        print(f"   {i}. From: {from_addr[:40]}... Subject: {subject[:40]}...")
except Exception as e:
    print(f"   ❌ Cannot read emails: {e}")

# Test 3: Can we see MOR emails specifically?
print("\n✅ TEST 3: Searching for MOR Emails")
queries_to_test = [
    ('Incorrect sender', 'from:manuscriptcentral-noreply@clarivate.com'),
    ('Correct sender', 'from:onbehalfof@manuscriptcentral.com'),
    ('By subject', 'subject:"Mathematics of Operations Research"'),
    ('By verification', 'subject:"Verification Code"'),
    ('Combined', 'from:onbehalfof@manuscriptcentral.com subject:"Verification Code"')
]

for description, query in queries_to_test:
    try:
        results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()
        count = len(results.get('messages', []))
        print(f"   {description}: {count} results")
        if count > 0 and 'Correct' in description:
            msg = service.users().messages().get(userId='me', id=results['messages'][0]['id']).execute()
            snippet = msg.get('snippet', '')
            code_match = re.search(r'\b(\d{6})\b', snippet)
            if code_match:
                print(f"      Latest code: {code_match.group(1)}")
    except Exception as e:
        print(f"   {description}: Error - {e}")

# Test 4: Monitor for NEW emails during login
print("\n✅ TEST 4: Live Email Monitoring During Login")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

driver = None
try:
    # Get baseline of existing emails
    print("   Getting baseline of existing emails...")
    baseline_query = 'from:onbehalfof@manuscriptcentral.com'
    baseline = service.users().messages().list(userId='me', q=baseline_query, maxResults=10).execute()
    baseline_ids = {msg['id'] for msg in baseline.get('messages', [])}
    print(f"   Baseline: {len(baseline_ids)} existing MOR emails")

    # Start login
    print("\n   Starting MOR login...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)

    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Reject cookies
    try:
        driver.find_element(By.ID, "onetrust-reject-all-handler").click()
        time.sleep(2)
    except:
        pass

    # Login
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    login_timestamp = int(time.time())
    print(f"   Login at: {time.strftime('%H:%M:%S', time.localtime(login_timestamp))}")

    driver.find_element(By.ID, "logInButton").click()
    time.sleep(5)

    # Check for 2FA
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("   ✅ 2FA page reached")

        print("\n   Monitoring for new emails...")
        found_code = None

        for attempt in range(15):
            print(f"\n   Check {attempt + 1}/15 at {time.strftime('%H:%M:%S')}:")

            # Get ALL emails (not just unread)
            all_query = f'from:onbehalfof@manuscriptcentral.com'
            current = service.users().messages().list(userId='me', q=all_query, maxResults=10).execute()
            current_messages = current.get('messages', [])

            # Find NEW emails (not in baseline)
            new_messages = [msg for msg in current_messages if msg['id'] not in baseline_ids]

            if new_messages:
                print(f"      ✅ Found {len(new_messages)} NEW emails!")
                for msg in new_messages:
                    msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()

                    # Check timestamp
                    internal_date = int(msg_data.get('internalDate', 0)) // 1000
                    time_diff = internal_date - login_timestamp

                    snippet = msg_data.get('snippet', '')
                    labels = msg_data.get('labelIds', [])

                    print(f"      Email arrived {time_diff} seconds after login")
                    print(f"      Labels: {labels}")
                    print(f"      Snippet: {snippet[:100]}...")

                    code_match = re.search(r'\b(\d{6})\b', snippet)
                    if code_match:
                        found_code = code_match.group(1)
                        print(f"      ✅ CODE FOUND: {found_code}")
                        break

                if found_code:
                    break
            else:
                print(f"      No new emails yet")

            # Also check with timestamp-based search
            timestamp_query = f'from:onbehalfof@manuscriptcentral.com after:{login_timestamp - 10}'
            timestamp_results = service.users().messages().list(userId='me', q=timestamp_query, maxResults=5).execute()
            timestamp_count = len(timestamp_results.get('messages', []))
            print(f"      Timestamp search found: {timestamp_count} emails after login")

            time.sleep(3)

        if found_code:
            print(f"\n   ✅ Entering code: {found_code}")
            token_field.send_keys(found_code)
            driver.find_element(By.ID, "submitButton").click()
            time.sleep(5)

            print(f"   Login result: {driver.title}")
            if "Associate Editor" in driver.page_source or "Dashboard" in driver.page_source:
                print("   ✅ LOGIN SUCCESSFUL!")
        else:
            print("\n   ❌ No new verification email detected")

    except Exception as e:
        print(f"   2FA error: {e}")

except Exception as e:
    print(f"   Test error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if driver:
        driver.quit()

print("\n" + "="*60)
print("DEBUG COMPLETE")
print("="*60)