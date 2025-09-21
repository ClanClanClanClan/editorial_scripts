#!/usr/bin/env python3
"""
WORKING MOR Login Test
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

# Setup Gmail
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

print("="*60)
print("🚀 WORKING MOR LOGIN TEST")
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
    # Get baseline emails
    print("\n1. Getting email baseline...")
    baseline = service.users().messages().list(
        userId='me',
        q='from:onbehalfof@manuscriptcentral.com',
        maxResults=20
    ).execute()
    baseline_ids = {msg['id'] for msg in baseline.get('messages', [])}
    print(f"   Baseline: {len(baseline_ids)} existing emails")

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
    print(f"   Login at: {time.strftime('%H:%M:%S', time.localtime(login_time))}")

    login_btn = driver.find_element(By.ID, "logInButton")
    login_btn.click()
    time.sleep(5)

    # Handle 2FA
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("\n5. 2FA page detected, fetching code...")

        # Monitor for new email
        found_code = None
        for attempt in range(10):
            print(f"   Checking attempt {attempt + 1}/10...")

            current = service.users().messages().list(
                userId='me',
                q='from:onbehalfof@manuscriptcentral.com',
                maxResults=20
            ).execute()

            new_messages = [msg for msg in current.get('messages', []) if msg['id'] not in baseline_ids]

            if new_messages:
                print(f"   ✅ Found {len(new_messages)} new emails!")
                msg_data = service.users().messages().get(
                    userId='me',
                    id=new_messages[0]['id']
                ).execute()

                snippet = msg_data.get('snippet', '')
                code_match = re.search(r'\b(\d{6})\b', snippet)

                if code_match:
                    found_code = code_match.group(1)
                    print(f"   ✅ Code found: {found_code}")
                    break

            time.sleep(2)

        if found_code:
            print(f"\n6. Entering 2FA code: {found_code}")

            # Enter code using JavaScript (more reliable)
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{found_code}';")
            print("   ✅ Code entered")

            # Find and click the VERIFY button (correct ID)
            print("   Looking for verify button...")
            try:
                verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
                print("   ✅ Found VERIFY_BTN")
                verify_btn.click()
            except:
                # Try alternative button IDs
                print("   VERIFY_BTN not found, trying alternatives...")
                buttons = driver.find_elements(By.TAG_NAME, "button")
                inputs = driver.find_elements(By.XPATH, "//input[@type='submit']")

                for btn in buttons + inputs:
                    btn_text = btn.get_attribute('value') or btn.text
                    btn_id = btn.get_attribute('id')
                    btn_name = btn.get_attribute('name')
                    print(f"      Button: id={btn_id}, name={btn_name}, text={btn_text}")

                    if any(word in str(btn_text).lower() for word in ['verify', 'submit', 'continue', 'login']):
                        print(f"      ✅ Clicking: {btn_text}")
                        btn.click()
                        break

            time.sleep(8)

            print("\n7. Checking login result...")
            print(f"   Current URL: {driver.current_url}")
            print(f"   Page title: {driver.title}")

            # Check for successful login
            try:
                ae_link = wait.until(
                    EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Editor"))
                )
                print("   ✅ LOGIN SUCCESSFUL! Found Editor link")

                # Navigate to AE Center
                print("\n8. Navigating to AE Center...")
                ae_link.click()
                time.sleep(3)

                # Look for manuscripts
                print("\n9. Looking for manuscripts...")
                links = driver.find_elements(By.TAG_NAME, "a")
                category_links = []
                for link in links:
                    text = link.text.strip()
                    if text and any(word in text for word in ['Awaiting', 'Overdue', 'Review', 'Decision']):
                        category_links.append(text)

                print(f"   Found {len(set(category_links))} manuscript categories:")
                for cat in set(category_links):
                    print(f"      - {cat}")

                print("\n✅ SUCCESS! MOR login and navigation working!")

            except Exception as e:
                print(f"   ⚠️  Could not find Editor link: {e}")
                # Show what's on the page
                print("\n   Page content:")
                links = driver.find_elements(By.TAG_NAME, "a")
                for link in links[:20]:
                    text = link.text.strip()
                    if text:
                        print(f"      - {text}")

        else:
            print("   ❌ No verification code found")

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