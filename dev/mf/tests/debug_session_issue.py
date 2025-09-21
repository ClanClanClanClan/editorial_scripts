#!/usr/bin/env python3
"""
Debug session invalidation issue
"""

import sys
import os
import time

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from extractors.mor_extractor import MORExtractor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

print("="*60)
print("🔍 DEBUGGING SESSION INVALIDATION")
print("="*60)

mor = None
try:
    # Create MOR instance
    print("\n1. Creating MOR instance...")
    mor = MORExtractor(use_cache=False)
    print("   ✅ Created")

    # Initialize driver manually to have more control
    print("\n2. Initializing driver...")
    mor.driver = webdriver.Chrome(options=mor.chrome_options)
    mor.driver.set_page_load_timeout(30)
    mor.driver.implicitly_wait(10)
    mor.wait = WebDriverWait(mor.driver, 10)
    mor.original_window = mor.driver.current_window_handle
    print("   ✅ Driver initialized")
    print(f"   Session ID: {mor.driver.session_id}")
    print(f"   Window handle: {mor.original_window}")

    # Login
    print("\n3. Logging in...")
    login_success = mor.login()

    if login_success:
        print("   ✅ Login successful")
        print(f"   Session ID after login: {mor.driver.session_id}")
        print(f"   Current URL: {mor.driver.current_url}")

        # Navigate to AE Center
        print("\n4. Navigating to AE Center...")
        nav_success = mor.navigate_to_ae_center()

        if nav_success:
            print("   ✅ Navigation successful")
            print(f"   Session ID after nav: {mor.driver.session_id}")

            # Process one category
            print("\n5. Processing category...")
            category = "Awaiting Reviewer Reports"

            try:
                # Click on category
                category_link = mor.driver.find_element(By.LINK_TEXT, category)
                mor.safe_click(category_link)
                mor.smart_wait(3)
                print(f"   ✅ Clicked on '{category}'")
                print(f"   Session ID after category: {mor.driver.session_id}")

                # Find manuscripts
                manuscript_rows = mor.driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
                print(f"   Found {len(manuscript_rows)} manuscripts")

                if manuscript_rows:
                    # Get first manuscript
                    print("\n6. Processing first manuscript...")
                    row = manuscript_rows[0]

                    # Extract manuscript ID
                    ms_link = row.find_element(By.XPATH, ".//a[contains(text(), 'MOR-')]")
                    ms_id = mor.safe_get_text(ms_link)
                    print(f"   Manuscript: {ms_id}")

                    # Click on manuscript
                    try:
                        check_icon = row.find_element(By.XPATH, ".//img[contains(@src, 'check')]")
                        parent = check_icon.find_element(By.XPATH, "./parent::*")
                        mor.safe_click(parent)
                    except:
                        mor.safe_click(ms_link)

                    mor.smart_wait(3)
                    print(f"   ✅ Clicked on manuscript")
                    print(f"   Session ID after click: {mor.driver.session_id}")

                    # Check windows
                    print("\n7. Checking windows...")
                    windows = mor.driver.window_handles
                    print(f"   Number of windows: {len(windows)}")
                    print(f"   Window handles: {windows}")
                    print(f"   Current window: {mor.driver.current_window_handle}")

                    # Make sure we're on the right window
                    if len(windows) > 1:
                        print("   ⚠️  Multiple windows detected!")
                        # Switch to the new window
                        for window in windows:
                            if window != mor.original_window:
                                mor.driver.switch_to.window(window)
                                print(f"   Switched to window: {window}")
                                break

                    # Try to extract referees
                    print("\n8. Extracting referees...")
                    try:
                        print(f"   Session before extraction: {mor.driver.session_id}")
                        referees = mor.extract_referees_enhanced()
                        print(f"   ✅ Extracted {len(referees)} referees")
                        print(f"   Session after extraction: {mor.driver.session_id}")

                        for i, ref in enumerate(referees[:3], 1):
                            print(f"\n   Referee {i}:")
                            print(f"      Name: {ref.get('name', 'Unknown')}")
                            print(f"      Status: {ref.get('status', 'Unknown')}")

                    except Exception as e:
                        print(f"   ❌ Referee extraction failed: {e}")
                        print(f"   Session at error: {mor.driver.session_id if mor.driver else 'Driver is None'}")

                    # Check if driver is still alive
                    print("\n9. Driver status check...")
                    try:
                        current_url = mor.driver.current_url
                        print(f"   ✅ Driver still alive")
                        print(f"   Current URL: {current_url}")
                    except Exception as e:
                        print(f"   ❌ Driver is dead: {e}")

                else:
                    print("   ❌ No manuscripts found")

            except Exception as e:
                print(f"   ❌ Category processing failed: {e}")

        else:
            print("   ❌ Navigation failed")
    else:
        print("   ❌ Login failed")

except Exception as e:
    print(f"\n❌ Fatal error: {e}")
    import traceback
    traceback.print_exc()

    # Check driver status
    print("\n🔍 Final driver check...")
    if mor and hasattr(mor, 'driver'):
        try:
            print(f"   Session ID: {mor.driver.session_id}")
            print(f"   URL: {mor.driver.current_url}")
        except:
            print("   Driver is not accessible")
finally:
    # Cleanup
    if mor and hasattr(mor, 'driver'):
        try:
            mor.driver.quit()
            print("\n🧹 Driver closed")
        except:
            print("\n⚠️  Driver already closed")

print("\n" + "="*60)
print("DEBUG COMPLETE")
print("="*60)