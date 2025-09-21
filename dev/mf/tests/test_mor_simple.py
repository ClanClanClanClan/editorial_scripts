#!/usr/bin/env python3
"""
TEST MOR SIMPLE - Get MOR manuscripts without complex navigation
================================================================
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
from selenium.common.exceptions import NoAlertPresentException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))
from mor_extractor import ComprehensiveMORExtractor

def handle_alert(driver):
    """Handle any alert."""
    try:
        alert = driver.switch_to.alert
        alert.accept()
        time.sleep(1)
        return True
    except:
        return False

print("🚀 SIMPLE MOR MANUSCRIPT EXTRACTION")
print("=" * 70)

mor = ComprehensiveMORExtractor()
manuscripts = []

try:
    print("🔐 Logging in to MOR...")
    if mor.login():
        print("✅ Login successful!")

        # Handle alerts
        for _ in range(3):
            handle_alert(mor.driver)
            time.sleep(1)

        # Wait for page to stabilize
        print("\n⏳ Waiting for page to load...")
        time.sleep(5)

        # Take screenshot
        debug_dir = Path(__file__).parent.parent / 'debug'
        debug_dir.mkdir(exist_ok=True)
        screenshot = debug_dir / 'mor_logged_in.png'
        mor.driver.save_screenshot(str(screenshot))
        print(f"📸 Screenshot: {screenshot}")

        # Check if we need to select a role
        print("\n🔍 Checking for role selection...")
        page_text = mor.driver.find_element(By.TAG_NAME, "body").text

        # Try to find any links with manuscript-related text
        print("\n🔍 Looking for manuscript links...")
        links = mor.driver.find_elements(By.TAG_NAME, "a")

        for link in links:
            try:
                text = link.text.strip()
                href = link.get_attribute('href') or ''

                # Look for AE Center or manuscript-related links
                if text and any(word in text.lower() for word in ['associate', 'editor', 'manuscript', 'author']):
                    print(f"   Found: {text}")

                    # If it's AE Center, click it
                    if 'associate' in text.lower() and 'editor' in text.lower():
                        print(f"   ✅ Clicking on: {text}")
                        link.click()
                        time.sleep(5)
                        handle_alert(mor.driver)

                        # Now look for manuscripts
                        page_text = mor.driver.find_element(By.TAG_NAME, "body").text

                        # Look for manuscript IDs
                        patterns = [
                            r'mathor-\d+-\d+',
                            r'MOR-\d{4}-\d+',
                            r'MORS-\d{4}-\d+',
                            r'\d{4}\.\d{4}',  # MOR might use this format
                            r'MS\d{5,}'  # Generic manuscript pattern
                        ]

                        for pattern in patterns:
                            ms_ids = re.findall(pattern, page_text, re.IGNORECASE)
                            for ms_id in ms_ids:
                                if ms_id not in [m['id'] for m in manuscripts]:
                                    manuscripts.append({'id': ms_id})
                                    print(f"      ✅ Found manuscript: {ms_id}")

                        # Also look for categories with counts
                        count_patterns = [
                            r'(\d+)\s*manuscript',
                            r'awaiting.*?(\d+)',
                            r'review.*?(\d+)',
                            r'(\d+)\s*submission'
                        ]

                        for pattern in count_patterns:
                            matches = re.findall(pattern, page_text, re.IGNORECASE)
                            for match in matches:
                                if match.isdigit() and int(match) > 0:
                                    print(f"      📊 Found category with {match} items")

                        # If we found manuscripts or categories, we're done
                        if manuscripts or matches:
                            break

            except Exception as e:
                continue

        # If no manuscripts yet, try clicking on any number links
        if not manuscripts:
            print("\n🔍 Looking for count links to click...")
            for link in links:
                try:
                    text = link.text.strip()
                    if text.isdigit() and int(text) > 0:
                        print(f"   Clicking on '{text}'...")
                        link.click()
                        time.sleep(3)
                        handle_alert(mor.driver)

                        # Look for manuscripts
                        page_text = mor.driver.find_element(By.TAG_NAME, "body").text

                        patterns = [
                            r'mathor-\d+-\d+',
                            r'MOR-\d{4}-\d+',
                            r'\d{4}\.\d{4}'
                        ]

                        for pattern in patterns:
                            ms_ids = re.findall(pattern, page_text, re.IGNORECASE)
                            for ms_id in ms_ids:
                                if ms_id not in [m['id'] for m in manuscripts]:
                                    manuscripts.append({'id': ms_id})
                                    print(f"      ✅ Found: {ms_id}")

                        if manuscripts:
                            break

                        mor.driver.back()
                        time.sleep(2)
                except:
                    continue

except Exception as e:
    print(f"❌ Error: {e}")

finally:
    print("\n🧹 Cleaning up...")
    mor.cleanup()

print("\n" + "=" * 70)
print(f"\n📄 MOR MANUSCRIPTS FOUND: {len(manuscripts)}")

if manuscripts:
    for ms in manuscripts:
        print(f"   • {ms['id']}")
else:
    print("   ❌ No manuscripts found")

print("\n🏁 DONE")