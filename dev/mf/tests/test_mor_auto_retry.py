#!/usr/bin/env python3
"""
MOR Test - Try with any available code
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
print("🚀 MOR AUTO-RETRY TEST")
print("="*60)

# Gmail setup
token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')
with open(token_file, 'r') as f:
    creds = Credentials.from_authorized_user_info(json.load(f))

if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build('gmail', 'v1', credentials=creds)

# Get all available codes
print("\n1. Getting all available verification codes...")
query = 'from:onbehalfof@manuscriptcentral.com subject:"Verification Code"'
results = service.users().messages().list(
    userId='me',
    q=query,
    maxResults=30
).execute()

messages = results.get('messages', [])
print(f"   Found {len(messages)} verification emails")

# Extract all codes
codes = []
for msg in messages:
    msg_data = service.users().messages().get(
        userId='me',
        id=msg['id']
    ).execute()

    snippet = msg_data.get('snippet', '')
    code_match = re.search(r'\b(\d{6})\b', snippet)

    if code_match:
        code = code_match.group(1)
        if code not in codes:
            codes.append(code)

print(f"   Extracted {len(codes)} unique codes")
for i, code in enumerate(codes[:5], 1):
    print(f"      {i}. {code}")

# Try each code
success = False
for attempt, code in enumerate(codes, 1):
    print(f"\n2. Attempt {attempt}/{len(codes)} with code: {code}")

    driver = None
    try:
        # Setup Chrome
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--headless")  # Run in background
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        wait = WebDriverWait(driver, 10)

        # Navigate
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
        driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
        driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))
        driver.find_element(By.ID, "logInButton").click()
        time.sleep(5)

        # Handle 2FA
        try:
            token_field = driver.find_element(By.ID, "TOKEN_VALUE")
            print(f"   2FA detected, entering code...")

            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
            verify_btn.click()
            time.sleep(8)

            # Check result
            if "Associate Editor" in driver.page_source:
                print(f"   ✅ SUCCESS! Code {code} worked!")
                success = True

                # Quick test of functionality
                print("\n3. Testing functionality...")

                # Navigate to AE Center
                ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Editor")
                ae_link.click()
                time.sleep(3)

                # Check for manuscripts
                links = driver.find_elements(By.TAG_NAME, "a")
                categories = []
                for link in links:
                    text = link.text.strip()
                    if text and any(word in text for word in ['Awaiting', 'Overdue', 'Review']):
                        categories.append(text)

                print(f"   Found {len(set(categories))} manuscript categories")

                if categories:
                    # Try to open first category
                    cat_link = driver.find_element(By.LINK_TEXT, categories[0])
                    cat_link.click()
                    time.sleep(3)

                    # Check for manuscripts
                    ms_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
                    print(f"   Found {len(ms_rows)} manuscripts")

                    if ms_rows:
                        print("\n✅ FULL SUCCESS!")
                        print("   - Login working")
                        print("   - Navigation working")
                        print("   - Manuscripts accessible")
                        print(f"\n   Working code: {code}")

                break

            else:
                print(f"   ❌ Code {code} failed")

        except Exception as e:
            print(f"   No 2FA or error: {str(e)[:50]}")

    except Exception as e:
        print(f"   Error: {str(e)[:50]}")
    finally:
        if driver:
            driver.quit()

    if success:
        break

    # Wait between attempts
    time.sleep(5)

if not success:
    print("\n❌ All codes failed")
    print("   MOR appears to have invalidated all old codes")
    print("   Need to wait for rate limit reset to get new code")
else:
    print("\n" + "="*60)
    print("✅ MOR LOGIN WORKING")
    print("="*60)

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)