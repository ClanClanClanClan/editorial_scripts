#!/usr/bin/env python3
"""
TEST MOR EXTRACTION - Extract real manuscripts from MOR
=======================================================
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

from mor_extractor import ComprehensiveMORExtractor

print("🚀 TESTING MOR MANUSCRIPT EXTRACTION")
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
        print(f"   📄 Page title: {mor.driver.title}")

        # Take screenshot after login
        debug_dir = Path(__file__).parent.parent / 'debug'
        debug_dir.mkdir(exist_ok=True)
        screenshot = debug_dir / 'mor_after_login.png'
        mor.driver.save_screenshot(str(screenshot))
        print(f"   📸 Screenshot: {screenshot}")

        # Look for navigation options
        print("\n🔍 Looking for navigation options...")
        links = mor.driver.find_elements(By.TAG_NAME, "a")
        nav_links = []
        for link in links:
            text = link.text.strip()
            if text and any(word in text.lower() for word in ['editor', 'manuscript', 'review', 'author', 'dashboard']):
                nav_links.append(text)
                print(f"   • {text}")

        # Try to navigate to Editor Center
        print("\n🎯 Looking for Editor/Author navigation...")

        # Common patterns for MOR navigation
        nav_attempts = [
            ("Associate Editor", "Associate Editor Center"),
            ("Editor", "Editor Center"),
            ("Author", "Author Dashboard"),
            ("Manuscript", "Manuscripts"),
            ("Dashboard", "Dashboard")
        ]

        for search_text, description in nav_attempts:
            try:
                nav_link = mor.driver.find_element(By.PARTIAL_LINK_TEXT, search_text)
                print(f"   ✅ Found '{search_text}' link")
                nav_link.click()
                time.sleep(5)

                print(f"   📍 Navigated to: {mor.driver.current_url}")

                # Look for manuscripts
                page_text = mor.driver.find_element(By.TAG_NAME, "body").text

                # MOR uses different ID format than MF
                # Look for patterns like MOR-2024-XXX or similar
                ms_patterns = [
                    r'MOR-\d{4}-\d+',
                    r'MOR\d{6}',
                    r'\d{4}-MOR-\d+',
                    r'Manuscript\s+#?\d+'
                ]

                all_ms_ids = []
                for pattern in ms_patterns:
                    ms_ids = re.findall(pattern, page_text, re.IGNORECASE)
                    all_ms_ids.extend(ms_ids)

                if all_ms_ids:
                    print(f"   ✅ Found {len(set(all_ms_ids))} manuscript IDs")
                    for ms_id in set(all_ms_ids):
                        extraction_results['manuscripts'].append({
                            'id': ms_id,
                            'found_in': description
                        })
                        print(f"      • {ms_id}")
                    break
                else:
                    # Look for manuscript counts/categories
                    print("   🔍 Looking for manuscript categories...")

                    # Find rows with counts
                    rows = mor.driver.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        row_text = row.text
                        if any(word in row_text.lower() for word in ['awaiting', 'review', 'decision', 'manuscript']):
                            # Look for numbers
                            numbers = re.findall(r'\b(\d+)\b', row_text)
                            if numbers:
                                category = {
                                    'text': row_text[:200],
                                    'count': numbers[0]
                                }
                                extraction_results['categories'].append(category)
                                print(f"      📊 Found category with {numbers[0]} items")

                mor.driver.back()
                time.sleep(2)

            except Exception as e:
                print(f"   ❌ Could not find '{search_text}': {e}")
                continue

        # If no manuscripts found, get page snapshot
        if not extraction_results['manuscripts']:
            print("\n⚠️ No manuscripts found yet, checking page content...")

            # Get all text
            page_text = mor.driver.find_element(By.TAG_NAME, "body").text
            extraction_results['page_snapshot'] = page_text[:1500]

            # Save screenshot
            screenshot = debug_dir / f'mor_no_manuscripts_{datetime.now().strftime("%H%M%S")}.png'
            mor.driver.save_screenshot(str(screenshot))
            print(f"   📸 Screenshot saved: {screenshot}")

            # Check if we're still on login page
            if "password" in page_text.lower() and "login" in page_text.lower():
                print("   ❌ Still on login page - login may have failed")
                extraction_results['errors'].append("Still on login page")

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
print(f"✅ Manuscripts found: {len(extraction_results['manuscripts'])}")
print(f"✅ Categories found: {len(extraction_results['categories'])}")

if extraction_results['errors']:
    print(f"⚠️ Errors: {len(extraction_results['errors'])}")
    for error in extraction_results['errors']:
        print(f"   • {error}")

# Display results
if extraction_results['manuscripts']:
    print("\n📄 MANUSCRIPTS:")
    for ms in extraction_results['manuscripts']:
        print(f"   • {ms['id']} (found in {ms['found_in']})")
else:
    print("\n❌ No manuscripts found")
    if 'page_snapshot' in extraction_results:
        print("\n📸 Page snapshot (first 500 chars):")
        print(extraction_results['page_snapshot'][:500])

print("\n🏁 MOR EXTRACTION COMPLETE")