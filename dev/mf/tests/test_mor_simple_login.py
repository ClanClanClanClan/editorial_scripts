#!/usr/bin/env python3
"""
Simple MOR login test - use ANY recent code
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
from selenium.webdriver.support import expected_conditions as EC

import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

print("="*60)
print("🚀 SIMPLE MOR LOGIN TEST")
print("="*60)

# Gmail setup
token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')
with open(token_file, 'r') as f:
    creds = Credentials.from_authorized_user_info(json.load(f))

if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(token_file, 'w') as f:
        f.write(creds.to_json())

service = build('gmail', 'v1', credentials=creds)

driver = None
try:
    # First, check if we have ANY verification emails
    print("\n1. Checking for ANY MOR verification emails...")
    query = 'from:onbehalfof@manuscriptcentral.com subject:"Verification Code"'
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=5
    ).execute()

    messages = results.get('messages', [])
    print(f"   Found {len(messages)} total MOR verification emails")

    latest_code = None
    if messages:
        # Get the most recent one
        msg_data = service.users().messages().get(
            userId='me',
            id=messages[0]['id']
        ).execute()

        internal_date = int(msg_data.get('internalDate', 0)) // 1000
        age_minutes = (time.time() - internal_date) / 60

        snippet = msg_data.get('snippet', '')
        code_match = re.search(r'\b(\d{6})\b', snippet)

        if code_match:
            latest_code = code_match.group(1)
            print(f"   Latest code: {latest_code} ({age_minutes:.1f} minutes old)")

    # Setup Chrome
    print("\n2. Starting Chrome...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 10)
    print("   ✅ Chrome ready")

    # Navigate
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

    # Login
    print("\n4. Logging in...")
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    login_time = int(time.time())
    driver.find_element(By.ID, "logInButton").click()
    time.sleep(5)

    # Handle 2FA
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("\n5. 2FA page detected")

        # Wait a bit for email to arrive
        print("   Waiting 10 seconds for new email...")
        time.sleep(10)

        # Check for NEW emails
        print("\n6. Checking for NEW verification emails...")
        new_results = service.users().messages().list(
            userId='me',
            q=f'from:onbehalfof@manuscriptcentral.com subject:"Verification Code" after:{login_time - 10}',
            maxResults=1
        ).execute()

        new_messages = new_results.get('messages', [])

        code_to_use = None
        if new_messages:
            # Get the new email
            new_msg = service.users().messages().get(
                userId='me',
                id=new_messages[0]['id']
            ).execute()

            snippet = new_msg.get('snippet', '')
            code_match = re.search(r'\b(\d{6})\b', snippet)

            if code_match:
                code_to_use = code_match.group(1)
                print(f"   ✅ NEW code found: {code_to_use}")
        else:
            print("   No new email found")

            if latest_code and age_minutes < 60:
                print(f"   Using existing code: {latest_code}")
                code_to_use = latest_code
            else:
                print("   ❌ No usable code available")

        if code_to_use:
            print(f"\n7. Entering code: {code_to_use}")
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code_to_use}';")

            # Submit
            verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
            verify_btn.click()
            time.sleep(8)

            print("\n8. Checking login result...")
            print(f"   URL: {driver.current_url}")
            print(f"   Title: {driver.title}")

            # Check for success
            try:
                # Look for Associate Editor link
                ae_link = wait.until(
                    EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Editor"))
                )
                print("   ✅ LOGIN SUCCESSFUL!")

                # Click on AE Center
                ae_link.click()
                time.sleep(3)

                # Check for manuscripts
                links = driver.find_elements(By.TAG_NAME, "a")
                categories = []
                for link in links:
                    text = link.text.strip()
                    if text and any(word in text for word in ['Awaiting', 'Overdue', 'Review']):
                        categories.append(text)

                print(f"\n   Found {len(set(categories))} manuscript categories")
                for cat in set(categories):
                    print(f"      - {cat}")

                # Click on first category
                if categories:
                    print("\n9. Opening first category...")
                    cat_link = driver.find_element(By.LINK_TEXT, categories[0])
                    cat_link.click()
                    time.sleep(3)

                    # Check for manuscripts
                    ms_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
                    print(f"   Found {len(ms_rows)} manuscripts")

                    if ms_rows:
                        print("   ✅ FULL SUCCESS! Can access manuscripts")

            except Exception as e:
                print(f"   Login uncertain: {e}")

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