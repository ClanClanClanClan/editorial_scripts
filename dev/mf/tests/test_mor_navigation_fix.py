#!/usr/bin/env python3
"""
Fix and test MOR navigation after login
"""

import sys
import os
import time
from pathlib import Path

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from extractors.mor_extractor import MORExtractor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

print("="*60)
print("🔧 MOR NAVIGATION FIX TEST")
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
    userid_field = mor.driver.find_element(By.ID, "USERID")
    userid_field.clear()
    userid_field.send_keys(os.getenv('MOR_EMAIL'))

    password_field = mor.driver.find_element(By.ID, "PASSWORD")
    password_field.clear()
    password_field.send_keys(os.getenv('MOR_PASSWORD'))

    login_btn = mor.driver.find_element(By.ID, "logInButton")
    mor.safe_click(login_btn)
    time.sleep(5)

    # Check for 2FA
    try:
        token_field = mor.driver.find_element(By.ID, "TOKEN_VALUE")
        print("   🔑 2FA required, fetching code from Gmail...")

        # Import and use gmail verification
        from core.gmail_verification import fetch_latest_verification_code

        # Get the 2FA code
        code = fetch_latest_verification_code('MOR', timestamp_after=int(time.time()))

        if code:
            print(f"   ✅ Got 2FA code: {code}")
            token_field.clear()
            token_field.send_keys(code)

            # Submit the 2FA
            submit_btn = mor.driver.find_element(By.ID, "submitButton")
            mor.safe_click(submit_btn)
            time.sleep(5)
        else:
            print("   ❌ Could not fetch 2FA code")
            print("   Waiting 30 seconds for manual entry...")
            time.sleep(30)
    except:
        pass

    print("   ✅ Login complete")

    # Analyze the page after login
    print("\n3. Analyzing page after login...")
    print(f"   Current URL: {mor.driver.current_url}")
    print(f"   Page title: {mor.driver.title}")

    # Find all links on the page
    all_links = mor.driver.find_elements(By.TAG_NAME, "a")
    print(f"\n   Found {len(all_links)} total links")

    # Look for relevant navigation links
    relevant_keywords = ['Associate', 'Editor', 'Center', 'Dashboard', 'Manuscript', 'Review', 'Awaiting']
    relevant_links = []

    for link in all_links:
        link_text = mor.safe_get_text(link)
        if link_text:
            for keyword in relevant_keywords:
                if keyword.lower() in link_text.lower():
                    relevant_links.append((link_text, link))
                    break

    print(f"\n4. Found {len(relevant_links)} relevant links:")
    for i, (text, link) in enumerate(relevant_links[:20], 1):
        print(f"   {i}. {text}")

    # Try to find and click AE Center
    print("\n5. Attempting navigation...")
    nav_success = False

    # Try different link texts
    nav_attempts = [
        "Associate Editor Center",
        "Associate Editor Dashboard",
        "AE Center",
        "Editor Center"
    ]

    for attempt in nav_attempts:
        try:
            print(f"   Trying: {attempt}")
            nav_link = mor.driver.find_element(By.PARTIAL_LINK_TEXT, attempt)
            mor.safe_click(nav_link)
            time.sleep(3)
            nav_success = True
            print(f"   ✅ Clicked on: {attempt}")
            break
        except:
            continue

    if not nav_success:
        print("   ⚠️  Could not find standard AE Center link")
        print("   Trying alternative navigation...")

        # Look for any link with 'Editor' in it
        for text, link in relevant_links:
            if 'editor' in text.lower() and 'center' in text.lower():
                try:
                    mor.safe_click(link)
                    time.sleep(3)
                    nav_success = True
                    print(f"   ✅ Clicked on: {text}")
                    break
                except:
                    continue

    # Check where we are now
    print("\n6. Checking current location...")
    print(f"   Current URL: {mor.driver.current_url}")
    print(f"   Page title: {mor.driver.title}")

    # Look for manuscript categories
    print("\n7. Looking for manuscript categories...")
    category_keywords = ['Awaiting', 'Overdue', 'Review', 'Decision', 'Pending']
    category_links = []

    all_links = mor.driver.find_elements(By.TAG_NAME, "a")
    for link in all_links:
        link_text = mor.safe_get_text(link)
        if link_text:
            for keyword in category_keywords:
                if keyword in link_text:
                    category_links.append(link_text)
                    break

    print(f"   Found {len(category_links)} category links:")
    for i, text in enumerate(set(category_links)[:10], 1):
        print(f"   {i}. {text}")

    # Try to click on first category
    if category_links:
        print("\n8. Testing category navigation...")
        try:
            first_category = category_links[0]
            cat_link = mor.driver.find_element(By.LINK_TEXT, first_category)
            mor.safe_click(cat_link)
            time.sleep(3)
            print(f"   ✅ Clicked on: {first_category}")

            # Look for manuscripts
            manuscript_rows = mor.driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
            print(f"   Found {len(manuscript_rows)} manuscripts")

            if manuscript_rows:
                print("\n9. ✅ SUCCESS! Can access manuscripts")

                # Get first manuscript details
                row = manuscript_rows[0]
                row_text = mor.safe_get_text(row)[:100]
                print(f"   First manuscript: {row_text}...")

        except Exception as e:
            print(f"   ❌ Category navigation failed: {e}")

except KeyboardInterrupt:
    print("\n⚠️ Interrupted")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if mor and hasattr(mor, 'driver'):
        try:
            input("\n🔍 Press Enter to close browser...")
            mor.driver.quit()
            print("🧹 Driver closed")
        except:
            pass