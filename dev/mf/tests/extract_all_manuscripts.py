#!/usr/bin/env python3
"""
EXTRACT ALL MANUSCRIPTS - Get ALL 3 manuscripts from MF
========================================================
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

# Add the production path
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

    # Handle 2FA
    try:
        token_field = mf.driver.find_element(By.ID, "TOKEN_VALUE")
        print("   📱 2FA required...")

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

print("🚀 EXTRACTING ALL MANUSCRIPTS FROM MF")
print("=" * 70)

output_dir = Path(__file__).parent.parent / 'outputs'
output_dir.mkdir(exist_ok=True)

extraction_results = {
    'timestamp': datetime.now().isoformat(),
    'manuscripts': []
}

mf = ComprehensiveMFExtractor()

try:
    # Login
    print("🔐 Logging in...")
    simple_login(mf)

    # Navigate to Associate Editor Center
    print("🎯 Navigating to AE Center...")
    ae_link = mf.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
    ae_link.click()
    time.sleep(5)

    # Track all manuscripts found
    all_manuscripts = []

    # Check "Awaiting Reviewer Scores" (2 manuscripts)
    print("\n📊 Category 1: Awaiting Reviewer Scores...")
    try:
        links = mf.driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            if "Awaiting Reviewer Scores" in link.text:
                link.click()
                time.sleep(3)

                # Extract manuscript IDs
                page_text = mf.driver.find_element(By.TAG_NAME, "body").text
                ms_ids = re.findall(r'MAFI-\d{4}-\d{4}', page_text)

                for ms_id in set(ms_ids):
                    if ms_id not in [m['id'] for m in all_manuscripts]:
                        all_manuscripts.append({
                            'id': ms_id,
                            'category': 'Awaiting Reviewer Scores',
                            'found_in': 'page_text'
                        })
                        print(f"   ✅ Found: {ms_id}")

                mf.driver.back()
                time.sleep(2)
                break
    except:
        pass

    # Check "Overdue Reviewer Scores" (1 manuscript)
    print("\n📊 Category 2: Overdue Reviewer Scores...")
    try:
        # Find the cell with "1" and "Overdue Reviewer Scores"
        rows = mf.driver.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            if "Overdue Reviewer Scores" in row.text and "1" in row.text:
                # Click on the number link
                links_in_row = row.find_elements(By.TAG_NAME, "a")
                for link in links_in_row:
                    if link.text.strip() == "1":
                        print(f"   Clicking on count link: {link.text}")
                        link.click()
                        time.sleep(3)

                        # Extract manuscript IDs
                        page_text = mf.driver.find_element(By.TAG_NAME, "body").text
                        ms_ids = re.findall(r'MAFI-\d{4}-\d{4}', page_text)

                        for ms_id in set(ms_ids):
                            if ms_id not in [m['id'] for m in all_manuscripts]:
                                all_manuscripts.append({
                                    'id': ms_id,
                                    'category': 'Overdue Reviewer Scores',
                                    'found_in': 'page_text'
                                })
                                print(f"   ✅ Found: {ms_id}")

                        mf.driver.back()
                        time.sleep(2)
                        break
                break
    except Exception as e:
        print(f"   ❌ Could not access Overdue category: {e}")

    # If we still don't have 3, look for any other manuscripts
    if len(all_manuscripts) < 3:
        print("\n📊 Looking for other manuscripts...")

        # Get all text from the main page
        page_text = mf.driver.find_element(By.TAG_NAME, "body").text
        all_ms_ids = re.findall(r'MAFI-\d{4}-\d{4}', page_text)

        for ms_id in set(all_ms_ids):
            if ms_id not in [m['id'] for m in all_manuscripts]:
                all_manuscripts.append({
                    'id': ms_id,
                    'category': 'Unknown',
                    'found_in': 'main_page'
                })
                print(f"   ✅ Found additional: {ms_id}")

    extraction_results['manuscripts'] = all_manuscripts

except Exception as e:
    print(f"❌ Error: {e}")
    extraction_results['error'] = str(e)

finally:
    print("\n🧹 Cleaning up...")
    mf.cleanup()

# Save results
output_file = output_dir / f"all_manuscripts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w') as f:
    json.dump(extraction_results, f, indent=2)

print("\n" + "=" * 70)
print(f"💾 Results saved to: {output_file}")
print(f"\n📄 MANUSCRIPTS FOUND: {len(extraction_results['manuscripts'])}")

for ms in extraction_results['manuscripts']:
    print(f"   • {ms['id']} ({ms['category']})")

if len(extraction_results['manuscripts']) == 3:
    print("\n✅ SUCCESS: All 3 manuscripts extracted!")
else:
    print(f"\n⚠️ Found {len(extraction_results['manuscripts'])} manuscripts (expected 3)")

print("\n🏁 EXTRACTION COMPLETE")