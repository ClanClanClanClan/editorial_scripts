#!/usr/bin/env python3
"""
Get the NEWEST MOR email and use that code immediately
"""

import sys
import os
import re
import time

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
print("🚀 MOR TEST - USE NEWEST EMAIL")
print("="*60)

# Gmail setup
token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')
with open(token_file, 'r') as f:
    creds = Credentials.from_authorized_user_info(json.load(f))

if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build('gmail', 'v1', credentials=creds)

print("\n1. Getting the NEWEST MOR verification email...")

# Get ALL MOR emails, sorted by date
results = service.users().messages().list(
    userId='me',
    q='from:onbehalfof@manuscriptcentral.com subject:"Verification Code"',
    maxResults=1  # Just get the newest one
).execute()

messages = results.get('messages', [])

if not messages:
    print("   ❌ No MOR verification emails found")
    sys.exit(1)

# Get the newest email
msg_data = service.users().messages().get(
    userId='me',
    id=messages[0]['id']
).execute()

internal_date = int(msg_data.get('internalDate', 0)) // 1000
current_time = int(time.time())
age_seconds = current_time - internal_date
age_minutes = age_seconds / 60

snippet = msg_data.get('snippet', '')
code_match = re.search(r'\b(\d{6})\b', snippet)

if not code_match:
    print("   ❌ No verification code found in newest email")
    sys.exit(1)

code = code_match.group(1)
print(f"   ✅ Found newest code: {code}")
print(f"   Age: {age_minutes:.1f} minutes ({age_seconds} seconds)")
print(f"   Time sent: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(internal_date))}")

if age_minutes < 5:
    print("   ✅ Code is FRESH! Should definitely work")
elif age_minutes < 60:
    print("   ⚠️ Code is recent, likely still valid")
else:
    print("   ⚠️ Code is old but let's try it anyway")

# Now login with this code
driver = None
try:
    print("\n2. Starting Chrome...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 10)
    print("   ✅ Chrome ready")

    print("\n3. Navigating to MOR...")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
        reject.click()
        time.sleep(2)
    except:
        pass

    print("\n4. Logging in...")
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    login_time = int(time.time())
    driver.find_element(By.ID, "logInButton").click()
    time.sleep(5)

    # Check for 2FA
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("\n5. 2FA detected")

        # First try the code we already have
        print(f"   Trying existing code: {code}")
        driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")

        verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
        verify_btn.click()
        time.sleep(8)

        # Check if it worked
        if "Associate Editor" in driver.page_source:
            print("   ✅ EXISTING CODE WORKED!")
        else:
            print("   ❌ Existing code failed")

            # Now check for NEW email that just arrived
            print("\n6. Checking for NEW email after login...")
            time.sleep(5)  # Give email time to arrive

            new_results = service.users().messages().list(
                userId='me',
                q=f'from:onbehalfof@manuscriptcentral.com after:{login_time - 10}',
                maxResults=1
            ).execute()

            new_messages = new_results.get('messages', [])

            if new_messages:
                new_msg = service.users().messages().get(
                    userId='me',
                    id=new_messages[0]['id']
                ).execute()

                new_date = int(new_msg.get('internalDate', 0)) // 1000

                if new_date > internal_date:  # This is newer than our previous email
                    new_snippet = new_msg.get('snippet', '')
                    new_code_match = re.search(r'\b(\d{6})\b', new_snippet)

                    if new_code_match:
                        new_code = new_code_match.group(1)
                        print(f"   ✅ Found NEW code that just arrived: {new_code}")

                        # Navigate back to login
                        driver.get("https://mc.manuscriptcentral.com/mathor")
                        time.sleep(3)

                        # Try again with new code
                        driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
                        driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))
                        driver.find_element(By.ID, "logInButton").click()
                        time.sleep(5)

                        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
                        driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{new_code}';")

                        verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
                        verify_btn.click()
                        time.sleep(8)

                        if "Associate Editor" in driver.page_source:
                            print("   ✅ NEW CODE WORKED!")

        # Final check
        print("\n7. Final status check...")
        print(f"   URL: {driver.current_url}")
        print(f"   Title: {driver.title}")

        if "Associate Editor" in driver.page_source or "Dashboard" in driver.page_source:
            print("\n✅ LOGIN SUCCESSFUL!")

            # Try to navigate
            from selenium.webdriver.common.by import By
            ae_links = driver.find_elements(By.PARTIAL_LINK_TEXT, "Editor")
            if ae_links:
                ae_links[0].click()
                time.sleep(3)
                print("   ✅ Navigated to AE Center")

                # Look for categories
                links = driver.find_elements(By.TAG_NAME, "a")
                categories = []
                for link in links:
                    text = link.text.strip()
                    if text and any(word in text for word in ['Awaiting', 'Overdue', 'Review']):
                        categories.append(text)

                if categories:
                    print(f"   ✅ Found {len(set(categories))} manuscript categories")

    except Exception as e:
        print(f"   Error: {e}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if driver:
        print("\nKeeping browser open for inspection...")
        print("Check if login succeeded")
        time.sleep(10)  # Keep open for 10 seconds
        driver.quit()
        print("🧹 Browser closed")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)