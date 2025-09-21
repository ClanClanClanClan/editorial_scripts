#!/usr/bin/env python3
"""
EXTRACT REAL MANUSCRIPTS - Actually get manuscript data from MF
===============================================================
"""

import sys
import json
import time
import os
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
    print("🔐 Logging in manually...")

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

print("🚀 EXTRACTING REAL MANUSCRIPTS FROM MF")
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
    try:
        ae_link = mf.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        print(f"   ✅ Found AE Center link")
        ae_link.click()
        time.sleep(5)
        handle_alert(mf.driver)

        print(f"   📍 Current URL: {mf.driver.current_url}")

    except Exception as e:
        print(f"   ❌ Could not find AE Center link: {e}")
        # Try to find any manuscript-related links
        print("   🔍 Looking for alternative navigation...")

        all_links = mf.driver.find_elements(By.TAG_NAME, "a")
        for link in all_links:
            text = link.text.strip().lower()
            if any(word in text for word in ['manuscript', 'editor', 'review', 'awaiting']):
                print(f"   📎 Found: {link.text}")
                extraction_results['categories'].append({
                    'name': link.text,
                    'href': link.get_attribute('href')
                })

    # Look for manuscript categories
    print("\n📊 FINDING MANUSCRIPT CATEGORIES...")

    # Get all table rows that might contain categories
    rows = mf.driver.find_elements(By.TAG_NAME, "tr")

    for row in rows:
        try:
            row_text = row.text.strip()
            if not row_text or len(row_text) > 500:
                continue

            # Look for patterns that indicate manuscript categories
            if any(pattern in row_text.lower() for pattern in ['awaiting', 'review', 'decision', 'score', 'manuscripts']):
                # Try to extract count
                import re
                count_match = re.search(r'\b(\d+)\b', row_text)
                count = int(count_match.group(1)) if count_match else 0

                # Find the link in this row
                links = row.find_elements(By.TAG_NAME, "a")
                for link in links:
                    link_text = link.text.strip()
                    if link_text and len(link_text) > 3:
                        category = {
                            'name': link_text,
                            'count': count,
                            'row_text': row_text[:100]
                        }

                        if link_text not in [c['name'] for c in extraction_results['categories']]:
                            extraction_results['categories'].append(category)
                            print(f"   ✅ Found category: {link_text} ({count} items)")
                        break
        except:
            continue

    print(f"\n✅ Found {len(extraction_results['categories'])} categories")

    # Try to extract manuscripts from a category with items
    print("\n📄 EXTRACTING MANUSCRIPTS...")

    for category in extraction_results['categories']:
        if category.get('count', 0) > 0 or 'manuscript' in category['name'].lower():
            print(f"\n   🔍 Checking category: {category['name']}")

            try:
                # Click on the category
                cat_link = mf.driver.find_element(By.LINK_TEXT, category['name'])
                cat_link.click()
                time.sleep(3)
                handle_alert(mf.driver)

                # Look for manuscript IDs (MF-YYYY-NNNN pattern)
                page_text = mf.driver.find_element(By.TAG_NAME, "body").text
                import re
                ms_ids = re.findall(r'MF-\d{4}-\d{4}', page_text)

                if ms_ids:
                    print(f"   ✅ Found {len(ms_ids)} manuscript IDs")
                    for ms_id in ms_ids[:3]:  # Limit to first 3
                        manuscript = {
                            'id': ms_id,
                            'category': category['name'],
                            'extracted_at': datetime.now().isoformat()
                        }

                        # Try to get more details
                        try:
                            ms_link = mf.driver.find_element(By.PARTIAL_LINK_TEXT, ms_id)
                            # Get the row containing this link
                            row = ms_link.find_element(By.XPATH, "./ancestor::tr[1]")
                            manuscript['row_data'] = row.text[:200]
                        except:
                            pass

                        extraction_results['manuscripts'].append(manuscript)
                        print(f"      📋 Extracted: {ms_id}")

                # Go back
                mf.driver.back()
                time.sleep(2)

                if len(extraction_results['manuscripts']) >= 3:
                    break

            except Exception as e:
                print(f"   ❌ Error with category: {e}")
                extraction_results['errors'].append(f"Category error: {str(e)}")

    # If no manuscripts found, get page snapshot
    if not extraction_results['manuscripts']:
        print("\n   ⚠️ No manuscripts found, saving page snapshot...")
        page_text = mf.driver.find_element(By.TAG_NAME, "body").text
        extraction_results['page_snapshot'] = page_text[:1000]

        # Save screenshot
        debug_dir = Path(__file__).parent.parent / 'debug'
        debug_dir.mkdir(exist_ok=True)
        screenshot = debug_dir / f'no_manuscripts_{datetime.now().strftime("%H%M%S")}.png'
        mf.driver.save_screenshot(str(screenshot))
        print(f"   📸 Screenshot saved: {screenshot}")

except Exception as e:
    print(f"\n❌ Fatal error: {e}")
    extraction_results['errors'].append(f"Fatal: {str(e)}")

finally:
    print("\n🧹 Cleaning up...")
    mf.cleanup()

# Save results
output_file = output_dir / f"manuscript_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w') as f:
    json.dump(extraction_results, f, indent=2)

print("\n" + "=" * 70)
print(f"💾 Results saved to: {output_file}")
print(f"✅ Categories found: {len(extraction_results['categories'])}")
print(f"✅ Manuscripts extracted: {len(extraction_results['manuscripts'])}")

if extraction_results['errors']:
    print(f"⚠️ Errors: {len(extraction_results['errors'])}")

# Display results
if extraction_results['categories']:
    print("\n📋 CATEGORIES:")
    for cat in extraction_results['categories'][:5]:
        print(f"   • {cat['name']} ({cat.get('count', '?')} items)")

if extraction_results['manuscripts']:
    print("\n📄 MANUSCRIPTS:")
    for ms in extraction_results['manuscripts']:
        print(f"   • {ms['id']} in {ms['category']}")
        if 'row_data' in ms:
            print(f"     Data: {ms['row_data'][:80]}...")
else:
    print("\n❌ No manuscripts extracted")
    if 'page_snapshot' in extraction_results:
        print("\n📸 Page snapshot:")
        print(extraction_results['page_snapshot'][:500])

print("\n🏁 EXTRACTION COMPLETE")