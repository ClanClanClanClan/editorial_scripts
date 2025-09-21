#!/usr/bin/env python3
"""
GET THIRD MANUSCRIPT - Click directly on the "1" link for Overdue
=================================================================
"""

import sys
import json
import time
import os
import re
from pathlib import Path
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))
from mf_extractor import ComprehensiveMFExtractor

def simple_login(mf):
    """Quick login."""
    mf.driver.get("https://mc.manuscriptcentral.com/mafi")
    time.sleep(5)

    try:
        mf.driver.find_element(By.ID, "onetrust-reject-all-handler").click()
        time.sleep(1)
    except:
        pass

    email = os.getenv('MF_EMAIL')
    password = os.getenv('MF_PASSWORD')

    userid = mf.driver.find_element(By.ID, "USERID")
    passwd = mf.driver.find_element(By.ID, "PASSWORD")

    userid.clear()
    userid.send_keys(email)
    passwd.clear()
    passwd.send_keys(password)

    login_time = time.time()
    mf.driver.find_element(By.ID, "logInButton").click()
    time.sleep(3)

    try:
        token_field = mf.driver.find_element(By.ID, "TOKEN_VALUE")
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src'))
        from core.gmail_verification_wrapper import fetch_latest_verification_code

        time.sleep(10)
        code = fetch_latest_verification_code('MF', max_wait=30, poll_interval=2, start_timestamp=login_time)

        if code:
            token_field.send_keys(code)
            try:
                mf.driver.find_element(By.ID, "VERIFY_BTN").click()
            except:
                token_field.send_keys(Keys.RETURN)
            time.sleep(10)
    except:
        pass

    return True

print("🚀 GETTING THE THIRD MANUSCRIPT")
print("=" * 70)

mf = ComprehensiveMFExtractor()
all_manuscripts = []

try:
    print("🔐 Logging in...")
    simple_login(mf)

    print("🎯 Navigating to AE Center...")
    ae_link = mf.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
    ae_link.click()
    time.sleep(5)

    print("\n📊 Looking for the Overdue manuscript...")

    # Find ALL links with text "1" and check their context
    all_links = mf.driver.find_elements(By.TAG_NAME, "a")

    for link in all_links:
        try:
            link_text = link.text.strip()
            if link_text == "1":
                # Get parent row to check context
                parent_row = link.find_element(By.XPATH, "./ancestor::tr[1]")
                row_text = parent_row.text

                print(f"   Found '1' link in row: {row_text[:100]}...")

                if "Overdue" in row_text:
                    print("   ✅ This is the Overdue link! Clicking...")
                    link.click()
                    time.sleep(5)

                    # Get manuscript IDs
                    page_text = mf.driver.find_element(By.TAG_NAME, "body").text
                    ms_ids = re.findall(r'MAFI-\d{4}-\d{4}', page_text)

                    print(f"   Found manuscript IDs: {ms_ids}")

                    for ms_id in set(ms_ids):
                        all_manuscripts.append({
                            'id': ms_id,
                            'category': 'Overdue Reviewer Scores'
                        })

                    # Take screenshot
                    debug_dir = Path(__file__).parent.parent / 'debug'
                    debug_dir.mkdir(exist_ok=True)
                    screenshot = debug_dir / 'overdue_manuscript.png'
                    mf.driver.save_screenshot(str(screenshot))
                    print(f"   📸 Screenshot: {screenshot}")

                    mf.driver.back()
                    break
        except:
            pass

    # Also get the 2 from Awaiting
    print("\n📊 Getting the 2 Awaiting manuscripts...")
    links = mf.driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        if "Awaiting Reviewer Scores" in link.text:
            link.click()
            time.sleep(3)

            page_text = mf.driver.find_element(By.TAG_NAME, "body").text
            ms_ids = re.findall(r'MAFI-\d{4}-\d{4}', page_text)

            for ms_id in set(ms_ids):
                if ms_id not in [m['id'] for m in all_manuscripts]:
                    all_manuscripts.append({
                        'id': ms_id,
                        'category': 'Awaiting Reviewer Scores'
                    })
            break

finally:
    print("\n🧹 Cleaning up...")
    mf.cleanup()

print("\n" + "=" * 70)
print(f"\n📄 ALL MANUSCRIPTS FOUND: {len(all_manuscripts)}")

for ms in all_manuscripts:
    print(f"   • {ms['id']} ({ms['category']})")

if len(all_manuscripts) == 3:
    print("\n✅ SUCCESS: All 3 manuscripts found!")
else:
    print(f"\n❌ Only found {len(all_manuscripts)} manuscripts")

print("\n🏁 DONE")