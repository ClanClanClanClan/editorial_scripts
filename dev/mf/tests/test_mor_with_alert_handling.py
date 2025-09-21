#!/usr/bin/env python3
"""
TEST MOR WITH ALERT HANDLING - Handle alerts and extract manuscripts
====================================================================
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

from mor_extractor import ComprehensiveMORExtractor

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

print("🚀 TESTING MOR WITH ALERT HANDLING")
print("=" * 70)

# Create output directory
output_dir = Path(__file__).parent.parent / 'outputs'
output_dir.mkdir(exist_ok=True)

extraction_results = {
    'timestamp': datetime.now().isoformat(),
    'extractor': 'MOR',
    'categories': [],
    'manuscripts': [],
    'errors': []
}

mor = ComprehensiveMORExtractor()

try:
    print("🔐 Logging in to MOR...")
    if not mor.login():
        print("❌ Login failed!")
        extraction_results['errors'].append("Login failed")
    else:
        print("✅ Login successful!")
        print(f"   📍 Current URL: {mor.driver.current_url}")

        # Handle any alerts after login
        print("\n🔍 Checking for alerts...")
        for _ in range(3):
            if handle_alert(mor.driver):
                time.sleep(2)

        # Take screenshot after handling alerts
        debug_dir = Path(__file__).parent.parent / 'debug'
        debug_dir.mkdir(exist_ok=True)
        screenshot = debug_dir / 'mor_after_alert.png'
        mor.driver.save_screenshot(str(screenshot))
        print(f"   📸 Screenshot: {screenshot}")

        # Look for navigation with alert handling
        print("\n🔍 Looking for navigation options...")
        try:
            links = mor.driver.find_elements(By.TAG_NAME, "a")
            nav_links = []
            for link in links[:30]:  # Limit to first 30
                try:
                    text = link.text.strip()
                    if text and len(text) > 2:
                        nav_links.append(text)
                        if any(word in text.lower() for word in ['associate', 'editor', 'author', 'manuscript']):
                            print(f"   ⭐ {text}")
                except:
                    pass
        except Exception as e:
            handle_alert(mor.driver)
            print(f"   ❌ Error getting links: {e}")

        # Try to find and click on Associate Editor Center
        print("\n🎯 Looking for Associate Editor Center...")
        try:
            ae_link = mor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            print("   ✅ Found Associate Editor Center link")
            ae_link.click()
            time.sleep(5)
            handle_alert(mor.driver)

            print(f"   📍 Navigated to: {mor.driver.current_url}")

            # Look for manuscript categories
            print("\n📊 Looking for manuscript categories...")

            # Get all text
            page_text = mor.driver.find_element(By.TAG_NAME, "body").text

            # Look for category patterns
            categories_found = []
            category_patterns = [
                r'Awaiting.*?(\d+)',
                r'Review.*?(\d+)',
                r'Decision.*?(\d+)',
                r'Overdue.*?(\d+)',
                r'(\d+).*?Manuscript',
                r'(\d+).*?Submission'
            ]

            for pattern in category_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    if match.isdigit() and int(match) > 0:
                        categories_found.append(f"Category with {match} items")

            if categories_found:
                print(f"   ✅ Found {len(categories_found)} categories with manuscripts")
                extraction_results['categories'] = categories_found

            # Look for manuscript IDs
            print("\n📄 Looking for manuscript IDs...")

            # MOR patterns
            ms_patterns = [
                r'MOR-\d{4}-\d+',
                r'MOR\d{6}',
                r'mathor-\d+-\d+',
                r'Manuscript\s+#?\d{4,}'
            ]

            all_ms_ids = []
            for pattern in ms_patterns:
                ms_ids = re.findall(pattern, page_text, re.IGNORECASE)
                all_ms_ids.extend(ms_ids)

            if all_ms_ids:
                print(f"   ✅ Found {len(set(all_ms_ids))} unique manuscript IDs")
                for ms_id in set(all_ms_ids):
                    extraction_results['manuscripts'].append({
                        'id': ms_id,
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"      • {ms_id}")

            # If no manuscripts, try clicking on a category
            if not extraction_results['manuscripts']:
                print("\n🔍 Trying to click on a category...")

                # Look for links with numbers
                links = mor.driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    try:
                        text = link.text.strip()
                        if text.isdigit() and int(text) > 0:
                            print(f"   Clicking on link with text '{text}'...")
                            link.click()
                            time.sleep(3)
                            handle_alert(mor.driver)

                            # Look for manuscripts on the new page
                            page_text = mor.driver.find_element(By.TAG_NAME, "body").text
                            for pattern in ms_patterns:
                                ms_ids = re.findall(pattern, page_text, re.IGNORECASE)
                                for ms_id in ms_ids:
                                    if ms_id not in [m['id'] for m in extraction_results['manuscripts']]:
                                        extraction_results['manuscripts'].append({
                                            'id': ms_id,
                                            'timestamp': datetime.now().isoformat()
                                        })
                                        print(f"      ✅ Found: {ms_id}")

                            if extraction_results['manuscripts']:
                                break

                            mor.driver.back()
                            time.sleep(2)
                    except:
                        pass

        except Exception as e:
            print(f"   ❌ Could not find Associate Editor Center: {e}")
            extraction_results['errors'].append(f"Navigation failed: {str(e)}")

            # Save page for debugging
            extraction_results['page_snapshot'] = mor.driver.find_element(By.TAG_NAME, "body").text[:1500]

except Exception as e:
    print(f"\n❌ Fatal error: {e}")
    extraction_results['errors'].append(f"Fatal: {str(e)}")

finally:
    print("\n🧹 Cleaning up...")
    mor.cleanup()

# Save results
output_file = output_dir / f"mor_alert_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w') as f:
    json.dump(extraction_results, f, indent=2)

print("\n" + "=" * 70)
print(f"💾 Results saved to: {output_file}")
print(f"✅ Manuscripts found: {len(extraction_results['manuscripts'])}")
print(f"✅ Categories found: {len(extraction_results['categories'])}")

if extraction_results['errors']:
    print(f"⚠️ Errors: {len(extraction_results['errors'])}")

# Display results
if extraction_results['manuscripts']:
    print("\n📄 MOR MANUSCRIPTS:")
    for ms in extraction_results['manuscripts']:
        print(f"   • {ms['id']}")
else:
    print("\n❌ No MOR manuscripts found")

print("\n🏁 MOR EXTRACTION COMPLETE")