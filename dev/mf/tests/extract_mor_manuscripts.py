#!/usr/bin/env python3
"""
EXTRACT MOR MANUSCRIPTS - Successfully extract manuscripts from MOR
==================================================================
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
        alert.accept()
        time.sleep(1)
        return True
    except NoAlertPresentException:
        return False

print("🚀 EXTRACTING MOR MANUSCRIPTS")
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

        # Wait for page to stabilize
        print("\n⏳ Waiting for page to stabilize...")
        time.sleep(5)

        # Handle any alerts
        for _ in range(3):
            if handle_alert(mor.driver):
                time.sleep(1)

        # Take screenshot of dashboard
        debug_dir = Path(__file__).parent.parent / 'debug'
        debug_dir.mkdir(exist_ok=True)
        screenshot = debug_dir / 'mor_dashboard.png'
        mor.driver.save_screenshot(str(screenshot))
        print(f"📸 Dashboard screenshot: {screenshot}")

        # Click on Associate Editor Center
        print("\n🎯 Navigating to Associate Editor Center...")
        try:
            # Try different methods to find and click the link
            ae_link = None

            # Method 1: By link text
            try:
                ae_link = mor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                print("   ✅ Found AE Center by link text")
            except:
                pass

            # Method 2: By partial link text
            if not ae_link:
                try:
                    ae_link = mor.driver.find_element(By.PARTIAL_LINK_TEXT, "Associate Editor")
                    print("   ✅ Found AE Center by partial link text")
                except:
                    pass

            # Method 3: By looking for the checkbox and its label
            if not ae_link:
                try:
                    # The checkbox seems to be associated with the link
                    checkbox = mor.driver.find_element(By.XPATH, "//input[@type='checkbox' and contains(@id, 'Associate')]")
                    # Get the parent element which should contain the link
                    parent = checkbox.find_element(By.XPATH, "..")
                    ae_link = parent.find_element(By.TAG_NAME, "a")
                    print("   ✅ Found AE Center via checkbox")
                except:
                    pass

            if ae_link:
                print(f"   📍 Clicking on Associate Editor Center...")
                ae_link.click()
                time.sleep(5)

                # Handle any alerts after navigation
                for _ in range(3):
                    if handle_alert(mor.driver):
                        time.sleep(1)

                print(f"   📍 Current URL: {mor.driver.current_url}")
                print(f"   📄 Page title: {mor.driver.title}")

                # Take screenshot after navigation
                screenshot = debug_dir / 'mor_ae_center.png'
                mor.driver.save_screenshot(str(screenshot))
                print(f"   📸 AE Center screenshot: {screenshot}")

                # Look for manuscript categories
                print("\n📊 FINDING MANUSCRIPT CATEGORIES...")

                # Get page text
                page_text = mor.driver.find_element(By.TAG_NAME, "body").text

                # Look for category patterns
                category_patterns = [
                    (r'Awaiting.*?Scores?\s*\(?\s*(\d+)\s*\)?', 'Awaiting Scores'),
                    (r'Overdue.*?Scores?\s*\(?\s*(\d+)\s*\)?', 'Overdue Scores'),
                    (r'With.*?Review.*?\(?\s*(\d+)\s*\)?', 'With Review'),
                    (r'Awaiting.*?Decision.*?\(?\s*(\d+)\s*\)?', 'Awaiting Decision'),
                    (r'Under.*?Review.*?\(?\s*(\d+)\s*\)?', 'Under Review'),
                    (r'(\d+)\s*[Mm]anuscript', 'Manuscripts'),
                ]

                for pattern, category_name in category_patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    for match in matches:
                        if match.isdigit() and int(match) > 0:
                            category = {
                                'name': category_name,
                                'count': int(match)
                            }
                            extraction_results['categories'].append(category)
                            print(f"   ✅ Found category: {category_name} ({match} items)")

                # Look for manuscript IDs
                print("\n📄 EXTRACTING MANUSCRIPT IDS...")

                # MOR patterns - they might use different formats
                ms_patterns = [
                    r'mathor-\d{4}-\d+',       # mathor-2024-123
                    r'MOR-\d{4}-\d+',           # MOR-2024-123
                    r'MORS-\d{4}-\d+',          # MORS-2024-123
                    r'mathor\d{6,}',            # mathor123456
                    r'\d{4}\.\d{4}',            # 2024.1234
                    r'MS\d{5,}',                # MS12345
                    r'Manuscript\s+#?\d{4,}'   # Manuscript #1234
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
                            'found_in': 'AE Center',
                            'timestamp': datetime.now().isoformat()
                        })
                        print(f"      • {ms_id}")

                # If no manuscripts found, try clicking on a category
                if not extraction_results['manuscripts'] and extraction_results['categories']:
                    print("\n🔍 No manuscript IDs visible, clicking on a category...")

                    # Find and click on a link with a number
                    links = mor.driver.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        try:
                            text = link.text.strip()
                            # Look for links that are just numbers (category counts)
                            if text.isdigit() and int(text) > 0:
                                print(f"   📍 Clicking on count link: {text}")
                                link.click()
                                time.sleep(3)

                                # Handle alerts
                                handle_alert(mor.driver)

                                # Get manuscript IDs from the new page
                                page_text = mor.driver.find_element(By.TAG_NAME, "body").text

                                for pattern in ms_patterns:
                                    ms_ids = re.findall(pattern, page_text, re.IGNORECASE)
                                    for ms_id in ms_ids:
                                        if ms_id not in [m['id'] for m in extraction_results['manuscripts']]:
                                            extraction_results['manuscripts'].append({
                                                'id': ms_id,
                                                'found_in': 'Category list',
                                                'timestamp': datetime.now().isoformat()
                                            })
                                            print(f"      ✅ Found: {ms_id}")

                                if extraction_results['manuscripts']:
                                    break

                                # Go back
                                mor.driver.back()
                                time.sleep(2)
                        except:
                            pass

                # If still no manuscripts, save page content for debugging
                if not extraction_results['manuscripts']:
                    print("\n⚠️ No manuscript IDs found, saving page content...")
                    extraction_results['page_snapshot'] = page_text[:2000]

            else:
                print("   ❌ Could not find Associate Editor Center link")
                extraction_results['errors'].append("Could not find AE Center link")

        except Exception as e:
            print(f"   ❌ Error navigating to AE Center: {e}")
            extraction_results['errors'].append(f"Navigation error: {str(e)}")

except Exception as e:
    print(f"\n❌ Fatal error: {e}")
    extraction_results['errors'].append(f"Fatal: {str(e)}")

finally:
    print("\n🧹 Cleaning up...")
    mor.cleanup()

# Save results
output_file = output_dir / f"mor_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
    print("\n📊 CATEGORIES:")
    for cat in extraction_results['categories']:
        print(f"   • {cat['name']}: {cat['count']} items")

if extraction_results['manuscripts']:
    print("\n📄 MANUSCRIPTS:")
    for ms in extraction_results['manuscripts']:
        print(f"   • {ms['id']}")
    print(f"\n✅ SUCCESS: Extracted {len(extraction_results['manuscripts'])} manuscripts from MOR!")
else:
    print("\n❌ No manuscripts extracted")
    if 'page_snapshot' in extraction_results:
        print("\n📸 Page content (first 500 chars):")
        print(extraction_results['page_snapshot'][:500])

print("\n🏁 MOR EXTRACTION COMPLETE")