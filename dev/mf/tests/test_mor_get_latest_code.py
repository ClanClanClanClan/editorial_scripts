#!/usr/bin/env python3
"""
Get latest MOR verification code regardless of new/old
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
print("🚀 MOR LOGIN - GET LATEST CODE")
print("="*60)

# Gmail setup
token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')
with open(token_file, 'r') as f:
    creds = Credentials.from_authorized_user_info(json.load(f))

if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build('gmail', 'v1', credentials=creds)

driver = None
try:
    # Setup Chrome
    print("\n1. Starting Chrome...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    print("   ✅ Chrome ready")

    # Navigate
    print("\n2. Navigating to MOR...")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        driver.find_element(By.ID, "onetrust-reject-all-handler").click()
        time.sleep(2)
    except:
        pass

    # Login
    print("\n3. Logging in...")
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    login_time = int(time.time())
    print(f"   Login at: {time.strftime('%H:%M:%S')}")

    driver.find_element(By.ID, "logInButton").click()
    time.sleep(5)

    # Handle 2FA
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("\n4. 2FA required, getting latest code...")

        # Get the LATEST verification email (regardless of when it was sent)
        query = 'from:onbehalfof@manuscriptcentral.com subject:"Verification Code"'
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

            # Get timestamp
            internal_date = int(msg_data.get('internalDate', 0)) // 1000
            age_seconds = login_time - internal_date

            snippet = msg_data.get('snippet', '')
            code_match = re.search(r'\b(\d{6})\b', snippet)

            if code_match:
                code = code_match.group(1)
                print(f"   Found code: {code}")
                print(f"   Code age: {age_seconds} seconds old")

                if age_seconds < 300:  # Less than 5 minutes old
                    print(f"   ✅ Code is fresh enough, using it")
                else:
                    print(f"   ⚠️  Code is old but trying anyway")

                # Enter code
                driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
                print("   ✅ Code entered")

                # Try to submit
                print("\n5. Submitting 2FA...")

                # Try multiple submit methods
                submit_methods = [
                    ("ID: VERIFY_BTN", lambda: driver.find_element(By.ID, "VERIFY_BTN").click()),
                    ("ID: submitButton", lambda: driver.find_element(By.ID, "submitButton").click()),
                    ("ID: logInButton", lambda: driver.find_element(By.ID, "logInButton").click()),
                    ("Enter key", lambda: token_field.send_keys("\n")),
                    ("JavaScript submit", lambda: driver.execute_script("document.forms[0].submit()"))
                ]

                for method_name, method_func in submit_methods:
                    try:
                        print(f"   Trying {method_name}...")
                        method_func()
                        print(f"   ✅ Submitted with {method_name}")
                        break
                    except Exception as e:
                        print(f"   {method_name} failed: {str(e)[:50]}")

                time.sleep(8)

                print("\n6. Checking result...")
                print(f"   URL: {driver.current_url}")
                print(f"   Title: {driver.title}")

                # Check for success
                page_text = driver.find_element(By.TAG_NAME, "body").text
                if "Associate Editor" in page_text:
                    print("   ✅ LOGIN SUCCESSFUL! Found Associate Editor")

                    # Show available links
                    links = driver.find_elements(By.TAG_NAME, "a")
                    print("\n   Available links:")
                    for link in links[:30]:
                        text = link.text.strip()
                        if text and len(text) > 3:
                            print(f"      - {text}")

                elif "Invalid" in page_text or "incorrect" in page_text.lower():
                    print("   ❌ Code was invalid or expired")
                    print("   Try running the script again for a fresh code")
                else:
                    print("   ⚠️  Login status uncertain")
                    # Show page content
                    print("   Page snippet:", page_text[:500])

            else:
                print("   ❌ No code found in latest email")
        else:
            print("   ❌ No verification emails found")

    except Exception as e:
        print(f"   No 2FA required or error: {e}")

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