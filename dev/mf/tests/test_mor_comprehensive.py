#!/usr/bin/env python3
"""
COMPREHENSIVE MOR TEST - Actually test everything
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from extractors.mor_extractor import MORExtractor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

print("="*60)
print("🔬 COMPREHENSIVE MOR EXTRACTOR TEST")
print("="*60)

results = {
    'test_timestamp': datetime.now().isoformat(),
    'tests_passed': [],
    'tests_failed': [],
    'manuscripts': [],
    'errors': []
}

mor = None
try:
    # Test 1: Instance creation
    print("\n✅ TEST 1: Creating MOR instance")
    mor = MORExtractor(use_cache=False)
    results['tests_passed'].append('Instance creation')

    # Test 2: Driver initialization
    print("\n✅ TEST 2: Initializing Chrome driver")
    mor.driver = webdriver.Chrome(options=mor.chrome_options)
    mor.driver.set_page_load_timeout(30)
    mor.driver.implicitly_wait(10)
    mor.wait = WebDriverWait(mor.driver, 10)
    mor.original_window = mor.driver.current_window_handle
    results['tests_passed'].append('Chrome driver initialization')

    # Test 3: Manual login (bypass Gmail API issue)
    print("\n✅ TEST 3: Testing login")
    print("   Attempting login...")

    mor.driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookie banner
    try:
        reject_btn = mor.driver.find_element(By.ID, "onetrust-reject-all-handler")
        mor.safe_click(reject_btn)
        time.sleep(2)
    except:
        pass

    # Enter credentials
    try:
        userid_field = mor.driver.find_element(By.ID, "USERID")
        userid_field.clear()
        userid_field.send_keys(os.getenv('MOR_EMAIL'))

        password_field = mor.driver.find_element(By.ID, "PASSWORD")
        password_field.clear()
        password_field.send_keys(os.getenv('MOR_PASSWORD'))

        login_btn = mor.driver.find_element(By.ID, "logInButton")
        mor.safe_click(login_btn)
        time.sleep(5)

        # Check if 2FA is needed
        try:
            token_field = mor.driver.find_element(By.ID, "TOKEN_VALUE")
            print("   ⚠️  2FA required - manual intervention needed")
            print("   Please enter 2FA code manually in browser...")
            print("   Waiting 30 seconds for manual 2FA entry...")
            time.sleep(30)
        except:
            print("   No 2FA required or already completed")

        # Check if login successful
        if "manuscriptcentral.com/mathor" in mor.driver.current_url:
            print("   ✅ Login successful!")
            results['tests_passed'].append('Login')
        else:
            print("   ❌ Login failed")
            results['tests_failed'].append('Login')

    except Exception as e:
        print(f"   ❌ Login error: {e}")
        results['tests_failed'].append(f'Login: {str(e)[:50]}')

    # Test 4: Navigate to AE Center
    print("\n✅ TEST 4: Navigating to AE Center")
    try:
        ae_link = mor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        mor.safe_click(ae_link)
        time.sleep(3)
        print("   ✅ Navigation successful")
        results['tests_passed'].append('AE Center navigation')
    except Exception as e:
        print(f"   ❌ Navigation failed: {e}")
        results['tests_failed'].append(f'Navigation: {str(e)[:50]}')

    # Test 5: Find manuscripts
    print("\n✅ TEST 5: Finding manuscripts")
    category = "Awaiting Reviewer Reports"

    try:
        category_link = mor.driver.find_element(By.LINK_TEXT, category)
        mor.safe_click(category_link)
        time.sleep(3)

        manuscript_rows = mor.driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
        print(f"   ✅ Found {len(manuscript_rows)} manuscripts")
        results['tests_passed'].append(f'Found {len(manuscript_rows)} manuscripts')

        # Test 6: Process first manuscript
        if manuscript_rows:
            print("\n✅ TEST 6: Processing first manuscript")
            row = manuscript_rows[0]

            # Get manuscript ID
            ms_id_elem = row.find_element(By.XPATH, ".//a[contains(text(), 'MOR-')]")
            ms_id = mor.safe_get_text(ms_id_elem)
            print(f"   Processing: {ms_id}")

            manuscript_data = {
                'manuscript_id': ms_id,
                'referees': [],
                'popup_emails': [],
                'errors': []
            }

            # Click on manuscript
            try:
                check_icon = row.find_element(By.XPATH, ".//img[contains(@src, 'check')]")
                parent_link = check_icon.find_element(By.XPATH, "./parent::*")
                mor.safe_click(parent_link)
            except:
                ms_link = row.find_element(By.XPATH, ".//a[contains(text(), 'MOR-')]")
                mor.safe_click(ms_link)
            time.sleep(3)

            # Test 7: Find and click referee tab
            print("\n✅ TEST 7: Finding referee tab")
            referee_tab_found = False

            # Try multiple selectors
            tab_selectors = [
                "//a[contains(text(), 'Review')]",
                "//a[contains(text(), 'Referee')]",
                "//a[contains(text(), 'Reviewer')]",
                "//a[contains(@href, 'TAB_REVIEWER')]"
            ]

            for selector in tab_selectors:
                try:
                    tab = mor.driver.find_element(By.XPATH, selector)
                    mor.safe_click(tab)
                    time.sleep(3)
                    referee_tab_found = True
                    print(f"   ✅ Clicked referee tab")
                    results['tests_passed'].append('Referee tab navigation')
                    break
                except:
                    continue

            if not referee_tab_found:
                print("   ❌ Could not find referee tab")
                results['tests_failed'].append('Referee tab not found')

            # Test 8: Extract referees
            print("\n✅ TEST 8: Extracting referees")
            try:
                referees = mor.extract_referees_enhanced()
                manuscript_data['referees'] = referees
                print(f"   ✅ Extracted {len(referees)} referees")
                results['tests_passed'].append(f'Extracted {len(referees)} referees')

                # Display referee details
                for i, ref in enumerate(referees[:5], 1):
                    print(f"\n   Referee {i}:")
                    print(f"      Name: {ref.get('name', 'Unknown')}")
                    print(f"      Status: {ref.get('status', 'Unknown')}")
                    if ref.get('institution'):
                        print(f"      Institution: {ref['institution']}")
                    if ref.get('email'):
                        print(f"      Email: {ref['email']}")

            except Exception as e:
                print(f"   ❌ Referee extraction failed: {e}")
                results['tests_failed'].append(f'Referee extraction: {str(e)[:50]}')
                manuscript_data['errors'].append(str(e))

            # Test 9: Test popup email extraction
            print("\n✅ TEST 9: Testing popup email extraction")
            try:
                popup_links = mor.driver.find_elements(By.XPATH, "//a[contains(@href, 'mailpopup')]")
                print(f"   Found {len(popup_links)} popup links")

                if popup_links:
                    # Test first popup
                    mor.safe_click(popup_links[0])
                    time.sleep(2)

                    # Switch to popup
                    windows = mor.driver.window_handles
                    if len(windows) > 1:
                        mor.driver.switch_to.window(windows[-1])

                        # Extract email
                        page_text = mor.driver.find_element(By.TAG_NAME, "body").text
                        import re
                        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                        emails = re.findall(email_pattern, page_text)

                        if emails:
                            print(f"   ✅ Found emails in popup: {emails[0]}")
                            manuscript_data['popup_emails'] = emails
                            results['tests_passed'].append('Popup email extraction')
                        else:
                            print("   ⚠️  No emails found in popup")

                        # Close popup
                        mor.driver.close()
                        mor.driver.switch_to.window(mor.original_window)
                    else:
                        print("   ⚠️  Popup did not open")
                else:
                    print("   ⚠️  No popup links found")

            except Exception as e:
                print(f"   ❌ Popup test failed: {e}")
                results['tests_failed'].append(f'Popup test: {str(e)[:50]}')
                # Make sure we're back on main window
                try:
                    mor.driver.switch_to.window(mor.original_window)
                except:
                    pass

            # Add manuscript data to results
            results['manuscripts'].append(manuscript_data)

        else:
            print("   ❌ No manuscripts found to test")
            results['tests_failed'].append('No manuscripts found')

    except Exception as e:
        print(f"   ❌ Error: {e}")
        results['errors'].append(str(e))

except KeyboardInterrupt:
    print("\n⚠️ Test interrupted by user")
    results['errors'].append('User interrupted')
except Exception as e:
    print(f"\n❌ Fatal error: {e}")
    results['errors'].append(f'Fatal: {str(e)}')
finally:
    # Clean up
    if mor and hasattr(mor, 'driver'):
        try:
            mor.driver.quit()
            print("\n🧹 Driver closed")
        except:
            pass

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = Path(f'/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/dev/mf/outputs/mor_comprehensive_test_{timestamp}.json')
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"\n✅ Tests Passed: {len(results['tests_passed'])}")
    for test in results['tests_passed']:
        print(f"   - {test}")

    print(f"\n❌ Tests Failed: {len(results['tests_failed'])}")
    for test in results['tests_failed']:
        print(f"   - {test}")

    if results['manuscripts']:
        ms = results['manuscripts'][0]
        print(f"\n📝 Manuscript tested: {ms['manuscript_id']}")
        print(f"   Referees extracted: {len(ms['referees'])}")
        print(f"   Popup emails found: {len(ms['popup_emails'])}")

    print(f"\n📄 Full results saved to: {output_file.name}")
    print("="*60)