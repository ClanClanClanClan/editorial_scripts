#!/usr/bin/env python3
"""
FINAL EXTRACTION - Successfully extract manuscripts from MF categories
=====================================================================
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
from selenium.common.exceptions import NoAlertPresentException

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

from mf_extractor import ComprehensiveMFExtractor

def handle_alert(driver):
    """Handle any alert that might be present."""
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        print(f"   ⚠️ Alert: {alert_text}")
        alert.accept()
        time.sleep(1)
        return True
    except NoAlertPresentException:
        return False

def simple_login(mf):
    """Simplified login without using the broken method."""
    print("🔐 Logging in...")

    mf.driver.get("https://mc.manuscriptcentral.com/mafi")
    time.sleep(5)

    # Handle cookie
    try:
        mf.driver.find_element(By.ID, "onetrust-reject-all-handler").click()
        time.sleep(1)
    except:
        pass

    # Enter credentials
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
            print(f"   ✅ Got code: {code[:3]}***")
            token_field.send_keys(code)

            try:
                mf.driver.find_element(By.ID, "VERIFY_BTN").click()
            except:
                token_field.send_keys(Keys.RETURN)

            time.sleep(10)
            handle_alert(mf.driver)
    except:
        pass

    # Verify login
    try:
        mf.driver.find_element(By.PARTIAL_LINK_TEXT, "Log Out")
        print("   ✅ Login successful!")
        return True
    except:
        print("   ❌ Login failed!")
        return False

print("🚀 FINAL MF MANUSCRIPT EXTRACTION")
print("=" * 70)

# Create output directory
output_dir = Path(__file__).parent.parent / 'outputs'
output_dir.mkdir(exist_ok=True)

extraction_results = {
    'timestamp': datetime.now().isoformat(),
    'extractor': 'MF',
    'categories': [],
    'manuscripts': [],
    'errors': []
}

mf = ComprehensiveMFExtractor()

try:
    # Login
    if not simple_login(mf):
        extraction_results['errors'].append("Login failed")
        raise Exception("Login failed")

    # Navigate to Associate Editor Center
    print("\n🎯 Navigating to Associate Editor Center...")
    ae_link = mf.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
    ae_link.click()
    time.sleep(5)
    handle_alert(mf.driver)

    # Save the AE Center URL for navigation
    ae_center_url = mf.driver.current_url
    print(f"   📍 AE Center URL: {ae_center_url}")

    # Find "Awaiting Reviewer Scores" category
    print("\n📊 Looking for 'Awaiting Reviewer Scores' category...")

    # Find the link with the count
    links = mf.driver.find_elements(By.TAG_NAME, "a")
    awaiting_link = None

    for link in links:
        text = link.text.strip()
        if "Awaiting Reviewer Scores" in text:
            awaiting_link = link
            print(f"   ✅ Found: {text}")
            break

    if not awaiting_link:
        # Try to find it in the page text
        rows = mf.driver.find_elements(By.TAG_NAME, "tr")
        for row in rows:
            if "Awaiting Reviewer Scores" in row.text:
                links_in_row = row.find_elements(By.TAG_NAME, "a")
                for link in links_in_row:
                    if link.text.strip():
                        awaiting_link = link
                        break
                break

    if awaiting_link:
        print("   🔗 Clicking on 'Awaiting Reviewer Scores'...")
        awaiting_link.click()
        time.sleep(5)
        handle_alert(mf.driver)

        # Now we should be on the manuscript list page
        print("\n📄 EXTRACTING MANUSCRIPTS...")

        # Look for manuscript IDs
        page_text = mf.driver.find_element(By.TAG_NAME, "body").text

        # Find all MF-YYYY-NNNN patterns
        ms_ids = re.findall(r'MF-\d{4}-\d{4}', page_text)

        if ms_ids:
            print(f"   ✅ Found {len(unique_ms_ids := list(set(ms_ids)))} unique manuscript IDs")

            for ms_id in unique_ms_ids[:5]:  # Limit to 5
                manuscript = {
                    'id': ms_id,
                    'category': 'Awaiting Reviewer Scores',
                    'extracted_at': datetime.now().isoformat()
                }

                # Try to get more details by finding the row containing this ID
                try:
                    # Find all rows
                    rows = mf.driver.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        if ms_id in row.text:
                            row_text = row.text
                            manuscript['row_data'] = row_text[:500]

                            # Try to extract title (often after the ID)
                            lines = row_text.split('\n')
                            for i, line in enumerate(lines):
                                if ms_id in line and i + 1 < len(lines):
                                    potential_title = lines[i + 1].strip()
                                    if len(potential_title) > 10 and not potential_title.startswith('MF-'):
                                        manuscript['title'] = potential_title
                                        break

                            # Try to extract author (look for names)
                            name_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+)'
                            names = re.findall(name_pattern, row_text)
                            if names:
                                manuscript['authors'] = names[:3]  # First 3 names

                            # Look for dates
                            date_pattern = r'\d{1,2}/\d{1,2}/\d{4}'
                            dates = re.findall(date_pattern, row_text)
                            if dates:
                                manuscript['dates'] = dates

                            break
                except Exception as e:
                    manuscript['extraction_error'] = str(e)

                extraction_results['manuscripts'].append(manuscript)
                print(f"      📋 Extracted: {ms_id}")
                if 'title' in manuscript:
                    print(f"         Title: {manuscript['title'][:60]}...")
                if 'authors' in manuscript:
                    print(f"         Authors: {', '.join(manuscript['authors'])}")

        else:
            print("   ❌ No manuscript IDs found on page")

            # Save page content for debugging
            extraction_results['page_content'] = page_text[:2000]

            # Try to find manuscript information in a different format
            print("   🔍 Looking for manuscript data in alternative format...")

            # Look for table rows with manuscript info
            tables = mf.driver.find_elements(By.TAG_NAME, "table")
            for table in tables:
                rows = table.find_elements(By.TAG_NAME, "tr")
                for row in rows[1:]:  # Skip header
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) > 2:
                        cell_texts = [cell.text.strip() for cell in cells]
                        # Look for patterns that might be manuscript data
                        if any(text for text in cell_texts if len(text) > 10):
                            manuscript = {
                                'table_row': cell_texts,
                                'extracted_at': datetime.now().isoformat()
                            }
                            extraction_results['manuscripts'].append(manuscript)
                            print(f"      📋 Found table row: {cell_texts[0][:50]}...")

    else:
        print("   ❌ Could not find 'Awaiting Reviewer Scores' link")
        extraction_results['errors'].append("Could not find category link")

        # Save screenshot for debugging
        debug_dir = Path(__file__).parent.parent / 'debug'
        debug_dir.mkdir(exist_ok=True)
        screenshot = debug_dir / f'no_category_link_{datetime.now().strftime("%H%M%S")}.png'
        mf.driver.save_screenshot(str(screenshot))
        print(f"   📸 Screenshot saved: {screenshot}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    extraction_results['errors'].append(str(e))

finally:
    print("\n🧹 Cleaning up...")
    mf.cleanup()

# Save results
output_file = output_dir / f"final_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w') as f:
    json.dump(extraction_results, f, indent=2)

print("\n" + "=" * 70)
print(f"💾 Results saved to: {output_file}")
print(f"✅ Manuscripts extracted: {len(extraction_results['manuscripts'])}")

if extraction_results['errors']:
    print(f"⚠️ Errors: {len(extraction_results['errors'])}")

# Display results
if extraction_results['manuscripts']:
    print("\n📄 EXTRACTED MANUSCRIPTS:")
    for ms in extraction_results['manuscripts']:
        if 'id' in ms:
            print(f"\n   📌 {ms['id']}")
            if 'title' in ms:
                print(f"      Title: {ms['title'][:80]}...")
            if 'authors' in ms:
                print(f"      Authors: {', '.join(ms['authors'])}")
            if 'dates' in ms:
                print(f"      Dates: {', '.join(ms['dates'])}")
        elif 'table_row' in ms:
            print(f"\n   📋 Table data: {ms['table_row'][0][:50]}...")
else:
    print("\n❌ No manuscripts extracted")

print("\n🏁 EXTRACTION COMPLETE")