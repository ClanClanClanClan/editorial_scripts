#!/usr/bin/env python3
"""
Test MOR extractor on a single manuscript only
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from extractors.mor_extractor import MORExtractor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

print("="*60)
print("🔬 SINGLE MANUSCRIPT TEST")
print("="*60)

mor = None
try:
    # Setup
    print("\n1. Setting up...")
    mor = MORExtractor(use_cache=False)
    mor.driver = webdriver.Chrome(options=mor.chrome_options)
    mor.driver.set_page_load_timeout(30)
    mor.driver.implicitly_wait(10)
    mor.wait = WebDriverWait(mor.driver, 10)
    mor.original_window = mor.driver.current_window_handle
    print("   ✅ Setup complete")

    # Login
    print("\n2. Logging in...")
    if not mor.login():
        raise Exception("Login failed")
    print("   ✅ Login successful")

    # Navigate
    print("\n3. Navigating...")
    if not mor.navigate_to_ae_center():
        raise Exception("Navigation failed")
    print("   ✅ In AE Center")

    # Process just one manuscript
    print("\n4. Processing ONE manuscript...")

    # Click on first category
    category = "Awaiting Reviewer Reports"
    try:
        link = mor.driver.find_element(By.LINK_TEXT, category)
        mor.safe_click(link)
        mor.smart_wait(3)
        print(f"   ✅ Opened category: {category}")
    except:
        # Try any available category
        links = mor.driver.find_elements(By.XPATH, "//a[contains(text(), 'Awaiting') or contains(text(), 'Overdue')]")
        if links:
            mor.safe_click(links[0])
            mor.smart_wait(3)
            print("   ✅ Opened first available category")

    # Get manuscripts
    manuscript_rows = mor.driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
    print(f"   Found {len(manuscript_rows)} manuscripts")

    if manuscript_rows:
        # Process just the FIRST manuscript
        row = manuscript_rows[0]

        # Extract manuscript ID
        ms_id = ""
        id_match = mor.driver.find_elements(By.XPATH, ".//a[contains(text(), 'MOR-')]")
        if id_match:
            ms_id = mor.safe_get_text(id_match[0])
        print(f"\n5. Processing manuscript: {ms_id}")

        # Click on it
        try:
            check = row.find_element(By.XPATH, ".//img[contains(@src, 'check')]")
            parent = check.find_element(By.XPATH, "./parent::*")
            mor.safe_click(parent)
        except:
            ms_link = row.find_element(By.XPATH, ".//a[contains(text(), 'MOR-')]")
            mor.safe_click(ms_link)
        mor.smart_wait(3)
        print("   ✅ Opened manuscript")

        # Extract basic info
        print("\n6. Extracting manuscript data...")
        manuscript_data = {
            'manuscript_id': ms_id,
            'referees': []
        }

        # Navigate to referee tab
        referee_tabs = mor.driver.find_elements(By.XPATH,
            "//a[contains(text(), 'Referee') or contains(text(), 'Reviewer') or contains(text(), 'Review')]")
        if referee_tabs:
            mor.safe_click(referee_tabs[0])
            mor.smart_wait(2)
            print("   ✅ Navigated to referee tab")

        # Extract referees using the enhanced method
        print("\n7. Extracting referees...")
        try:
            referees = mor.extract_referees_enhanced()
            manuscript_data['referees'] = referees
            print(f"   ✅ Extracted {len(referees)} referees")

            # Display referee details
            for i, ref in enumerate(referees, 1):
                print(f"\n   Referee {i}:")
                print(f"      Name: {ref.get('name', 'Unknown')}")
                print(f"      Status: {ref.get('status', 'Unknown')}")
                if ref.get('institution'):
                    print(f"      Institution: {ref['institution']}")
                if ref.get('email'):
                    print(f"      Email: {ref['email']}")

        except Exception as e:
            print(f"   ❌ Referee extraction failed: {e}")

        # Try to extract email from popup
        if referees:
            print("\n8. Testing popup email extraction...")
            try:
                # Find first referee link
                popup_links = mor.driver.find_elements(By.XPATH,
                    "//a[contains(@href, 'mailpopup')]")

                if popup_links:
                    print(f"   Found {len(popup_links)} popup links")
                    # Click first one
                    mor.safe_click(popup_links[0])
                    mor.smart_wait(2)

                    # Switch to popup
                    windows = mor.driver.window_handles
                    if len(windows) > 1:
                        mor.driver.switch_to.window(windows[-1])
                        print("   ✅ Switched to popup")

                        # Extract email
                        email_elem = mor.driver.find_elements(By.XPATH,
                            "//*[contains(text(), '@')]")
                        if email_elem:
                            email_text = mor.safe_get_text(email_elem[0])
                            print(f"   ✅ Found email in popup: {email_text[:50]}")

                        # Close popup
                        mor.driver.close()
                        mor.driver.switch_to.window(mor.original_window)
                        print("   ✅ Closed popup")
                else:
                    print("   No popup links found")

            except Exception as e:
                print(f"   Popup test error: {e}")
                # Make sure we're back on main window
                mor.driver.switch_to.window(mor.original_window)

        print("\n" + "="*40)
        print("✅ SINGLE MANUSCRIPT TEST COMPLETE")
        print(f"   Manuscript: {ms_id}")
        print(f"   Referees found: {len(manuscript_data['referees'])}")
        print("="*40)

    else:
        print("   ❌ No manuscripts found")

except KeyboardInterrupt:
    print("\n⚠️ Interrupted")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if mor and hasattr(mor, 'driver'):
        try:
            mor.driver.quit()
            print("\n🧹 Driver closed")
        except:
            pass