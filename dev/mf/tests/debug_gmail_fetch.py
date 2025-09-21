#!/usr/bin/env python3
"""
Debug Gmail 2FA code fetching
"""

import sys
import time
import os

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

print("="*60)
print("🔍 DEBUGGING GMAIL 2FA FETCHING")
print("="*60)

from core.gmail_verification import fetch_latest_verification_code

# Test 1: Basic connectivity
print("\n1. Testing basic Gmail API connectivity...")
try:
    # Try with a very old timestamp to get any email
    code = fetch_latest_verification_code('TEST', timestamp_after=0)
    if code:
        print(f"   ✅ Found a code: {code}")
    else:
        print("   ❌ No code found (but API worked)")
except Exception as e:
    print(f"   ❌ API Error: {e}")

# Test 2: Recent emails
print("\n2. Checking recent emails...")
current_time = int(time.time())
print(f"   Current timestamp: {current_time}")
print(f"   Looking for emails after: {current_time - 300} (5 minutes ago)")

try:
    code = fetch_latest_verification_code('MOR', timestamp_after=current_time - 300)
    if code:
        print(f"   ✅ Found recent code: {code}")
    else:
        print("   No recent MOR codes found")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Debug the actual fetch function
print("\n3. Detailed Gmail fetch debug...")
try:
    import json
    from pathlib import Path
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    # Load credentials
    token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')

    if not token_file.exists():
        print("   ❌ Token file not found")
    else:
        print(f"   ✅ Token file exists")

        with open(token_file, 'r') as token:
            creds = Credentials.from_authorized_user_info(json.load(token))

        # Check if token expired
        if creds and creds.expired and creds.refresh_token:
            print("   ⚠️  Token expired, refreshing...")
            creds.refresh(Request())
            # Save refreshed token
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
            print("   ✅ Token refreshed")
        else:
            print("   ✅ Token is valid")

        # Build service
        service = build('gmail', 'v1', credentials=creds)
        print("   ✅ Gmail service built")

        # Search for MOR emails
        query = f'from:manuscriptcentral-noreply@clarivate.com is:unread'
        print(f"   Query: {query}")

        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])

        print(f"   Found {len(messages)} unread MOR emails")

        # Get details of first few messages
        for i, msg in enumerate(messages[:5], 1):
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()

            # Get timestamp
            internal_date = int(msg_data['internalDate']) // 1000

            # Get snippet
            snippet = msg_data.get('snippet', '')

            print(f"\n   Email {i}:")
            print(f"      Timestamp: {internal_date}")
            print(f"      Time ago: {current_time - internal_date} seconds")
            print(f"      Snippet: {snippet[:100]}...")

            # Look for code in snippet
            import re
            code_match = re.search(r'\b(\d{6})\b', snippet)
            if code_match:
                print(f"      ✅ Code found: {code_match.group(1)}")

except Exception as e:
    print(f"   ❌ Debug failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Live test
print("\n4. Testing with live MOR login...")
print("   Starting a Chrome session that will trigger 2FA...")
print("   (This will log in to MOR to trigger an email)")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

try:
    # Setup Chrome
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)

    # Navigate to MOR
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
    email_field = driver.find_element(By.ID, "USERID")
    email_field.send_keys(os.getenv('MOR_EMAIL'))

    password_field = driver.find_element(By.ID, "PASSWORD")
    password_field.send_keys(os.getenv('MOR_PASSWORD'))

    # Record time before login
    login_time = int(time.time())
    print(f"   Login timestamp: {login_time}")

    login_btn = driver.find_element(By.ID, "logInButton")
    login_btn.click()
    time.sleep(5)

    # Check if 2FA is needed
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("   ✅ 2FA page reached")

        # Now fetch the code
        print("   Waiting 5 seconds for email to arrive...")
        time.sleep(5)

        code = fetch_latest_verification_code('MOR', timestamp_after=login_time)
        if code:
            print(f"   ✅ SUCCESS! Got code: {code}")
            token_field.send_keys(code)

            submit = driver.find_element(By.ID, "submitButton")
            submit.click()
            time.sleep(5)
            print("   ✅ 2FA submitted")
        else:
            print("   ❌ Still couldn't fetch code")

    except Exception as e:
        print(f"   No 2FA needed or error: {e}")

    driver.quit()

except Exception as e:
    print(f"   ❌ Live test failed: {e}")
    try:
        driver.quit()
    except:
        pass

print("\n" + "="*60)
print("DEBUG COMPLETE")
print("="*60)