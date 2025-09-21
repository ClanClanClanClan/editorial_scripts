#!/usr/bin/env python3
"""
Test MOR with fixed Gmail search
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

print("="*60)
print("🚀 MOR TEST WITH GMAIL FIX")
print("="*60)

def fetch_mor_code(timestamp_after):
    """Custom function to fetch MOR verification codes"""
    try:
        import json
        from pathlib import Path
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        # Load token
        token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')
        with open(token_file, 'r') as f:
            creds = Credentials.from_authorized_user_info(json.load(f))

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

        service = build('gmail', 'v1', credentials=creds)

        # Search for MOR emails specifically
        gmail_after = int(timestamp_after)
        query = f'from:onbehalfof@manuscriptcentral.com subject:"Verification Code" after:{gmail_after}'
        print(f"   Searching with query: {query}")

        max_attempts = 10
        for attempt in range(max_attempts):
            print(f"   Attempt {attempt + 1}/{max_attempts}...")

            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=1
            ).execute()

            messages = results.get('messages', [])
            if messages:
                msg_data = service.users().messages().get(
                    userId='me',
                    id=messages[0]['id']
                ).execute()

                # Get snippet
                snippet = msg_data.get('snippet', '')

                # Extract code
                code_match = re.search(r'\b(\d{6})\b', snippet)
                if code_match:
                    code = code_match.group(1)
                    print(f"   ✅ Found code: {code}")
                    return code

            time.sleep(3)

        print("   ❌ No code found")
        return None

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

driver = None
try:
    # Setup Chrome
    print("\n1. Setting up Chrome...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 10)
    print("   ✅ Chrome ready")

    # Navigate
    print("\n2. Navigating to MOR...")
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
    print("\n3. Logging in...")
    email_field = driver.find_element(By.ID, "USERID")
    email_field.send_keys(os.getenv('MOR_EMAIL'))

    password_field = driver.find_element(By.ID, "PASSWORD")
    password_field.send_keys(os.getenv('MOR_PASSWORD'))

    login_time = time.time()
    print(f"   Login time: {time.strftime('%H:%M:%S', time.localtime(login_time))}")

    login_btn = driver.find_element(By.ID, "logInButton")
    login_btn.click()
    time.sleep(5)

    # Check for 2FA
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("\n4. 2FA required, fetching code...")

        code = fetch_mor_code(login_time)

        if code:
            print(f"   ✅ Entering code: {code}")
            token_field.send_keys(code)

            submit = driver.find_element(By.ID, "submitButton")
            submit.click()
            time.sleep(5)

            print("\n5. Checking login status...")
            print(f"   Current URL: {driver.current_url}")
            print(f"   Page title: {driver.title}")

            # Look for success indicators
            page_text = driver.find_element(By.TAG_NAME, "body").text
            if "Associate Editor" in page_text:
                print("   ✅ Login successful! Found Associate Editor text")
            elif "Dashboard" in page_text:
                print("   ✅ Login successful! Found Dashboard")
            else:
                print("   ⚠️  Login status uncertain")
                # Print what we can see
                links = driver.find_elements(By.TAG_NAME, "a")
                print(f"   Found {len(links)} links on page")
                for link in links[:10]:
                    text = link.text.strip()
                    if text:
                        print(f"      - {text}")

        else:
            print("   ❌ Could not fetch code")

    except Exception as e:
        print(f"   No 2FA or error: {e}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if driver:
        input("\n🔍 Press Enter to close browser...")
        driver.quit()

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)