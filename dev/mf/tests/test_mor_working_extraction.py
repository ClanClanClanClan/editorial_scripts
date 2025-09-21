#!/usr/bin/env python3
"""
MOR WORKING EXTRACTION - PROPERLY HANDLE 2FA AND GET MANUSCRIPTS
"""

import sys
import os
import time
import re
import json

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from core.gmail_verification import fetch_latest_verification_code

print("="*80)
print("🎯 MOR WORKING EXTRACTION - ACTUALLY GET THE DATA")
print("="*80)

RESULTS = {
    "manuscripts": [],
    "extraction_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "login_successful": False,
    "categories_found": [],
    "total_manuscripts": 0
}

driver = None
try:
    # 1. Setup
    print("\n1. Browser Setup")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 15)
    print("   ✅ Chrome ready")

    # 2. Navigate
    print("\n2. Navigate to MOR")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
        reject.click()
        time.sleep(2)
        print("   ✅ Cookies handled")
    except:
        pass

    # 3. Login
    print("\n3. Login Process")
    print("-"*40)

    # Wait for login form
    wait.until(EC.presence_of_element_located((By.ID, "USERID")))
    print("   Login form ready")

    # Enter credentials
    userid_field = driver.find_element(By.ID, "USERID")
    password_field = driver.find_element(By.ID, "PASSWORD")

    userid_field.clear()
    userid_field.send_keys(os.getenv('MOR_EMAIL'))
    password_field.clear()
    password_field.send_keys(os.getenv('MOR_PASSWORD'))
    print(f"   Credentials entered")

    # Click login
    login_timestamp = time.time()
    login_btn = driver.find_element(By.ID, "logInButton")
    login_btn.click()
    print(f"   Login clicked at {time.strftime('%H:%M:%S', time.localtime(login_timestamp))}")

    # Wait for page change
    time.sleep(5)

    # 4. Handle 2FA
    print("\n4. 2FA Handling")
    print("-"*40)

    # Check if 2FA page loaded
    current_url = driver.current_url
    page_source = driver.page_source

    if "TOKEN_VALUE" in page_source or "verification" in page_source.lower():
        print("   ✅ 2FA page detected")

        # CRITICAL: Wait for NEW email to arrive after login
        print("   ⏳ Waiting 15 seconds for NEW 2FA email to arrive...")
        time.sleep(15)

        # Fetch fresh code - ONLY codes after login
        print("   Fetching verification code...")
        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_timestamp + 5  # Add 5 seconds buffer to ensure we get NEW code
        )

        if code:
            print(f"   ✅ Got code: {code}")

            # Enter code using multiple methods
            print("   Entering code...")

            # Method 1: Direct input
            try:
                token_field = driver.find_element(By.ID, "TOKEN_VALUE")
                token_field.clear()
                token_field.send_keys(code)
                print("   Code entered in field")
            except:
                # Method 2: JavaScript
                driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
                print("   Code set via JavaScript")

            # Submit using multiple methods
            print("   Submitting code...")

            # Try clicking button
            try:
                verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
                verify_btn.click()
                print("   Clicked VERIFY_BTN")
            except:
                # Try JavaScript click
                try:
                    driver.execute_script("document.getElementById('VERIFY_BTN').click();")
                    print("   Clicked via JavaScript")
                except:
                    # Try form submit
                    driver.execute_script("document.forms[0].submit();")
                    print("   Submitted form")

            # Wait for login to complete
            print("   Waiting for login to complete...")
            time.sleep(10)
        else:
            print("   ❌ No verification code received!")
            raise Exception("2FA code not received")
    else:
        print("   No 2FA required or different page")

    # 5. Verify Login Success
    print("\n5. Login Verification")
    print("-"*40)

    current_url = driver.current_url
    page_title = driver.title
    page_text = driver.page_source[:2000]

    print(f"   Current URL: {current_url}")
    print(f"   Page title: {page_title}")

    # Check if we're logged in
    if "Log In" in driver.title or "login" in current_url.lower():
        print("   ❌ STILL ON LOGIN PAGE!")
        # Take screenshot
        driver.save_screenshot("/tmp/mor_login_failed.png")
        print("   Screenshot saved: /tmp/mor_login_failed.png")

        # Check for error messages
        try:
            error = driver.find_element(By.CLASS_NAME, "error")
            print(f"   Error message: {error.text}")
        except:
            pass

        raise Exception("Login failed - still on login page")

    print("   ✅ Login successful!")
    RESULTS["login_successful"] = True

    # 6. Navigate to AE Center
    print("\n6. Navigate to Associate Editor Center")
    print("-"*40)

    # Find AE Center link
    ae_link = None
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if "associate editor" in link.text.lower() and link.text.strip():
            ae_link = link
            print(f"   Found link: {link.text}")
            break

    if not ae_link:
        print("   ❌ No Associate Editor link found")
        print("   Available links:")
        for link in driver.find_elements(By.TAG_NAME, "a")[:20]:
            if link.text.strip():
                print(f"      - {link.text}")
        raise Exception("Cannot find AE Center")

    ae_link.click()
    time.sleep(5)
    print("   ✅ Clicked AE Center link")

    # 7. Find Manuscript Categories
    print("\n7. Find Manuscript Categories")
    print("-"*40)

    # Look for categories
    categories = []
    for link in driver.find_elements(By.TAG_NAME, "a"):
        text = link.text.strip()
        if text and any(kw in text for kw in ['Review', 'Awaiting', 'Decision', 'Assignment']):
            if 'Report' not in text or 'Reviewer' in text:
                categories.append({
                    "text": text,
                    "element": link,
                    "href": link.get_attribute("href")
                })
                print(f"   Found: {text}")

    RESULTS["categories_found"] = [c["text"] for c in categories]
    print(f"   Total categories: {len(categories)}")

    # 8. Extract Manuscripts from Each Category
    print("\n8. Extract Manuscripts")
    print("-"*40)

    for i, cat in enumerate(categories, 1):
        print(f"\n   Category {i}: {cat['text']}")
        print("   " + "-"*30)

        try:
            # Navigate to category
            driver.get(cat["href"])
            time.sleep(5)

            # Find manuscript rows
            manuscripts = []

            # Method 1: By MOR ID
            rows_with_mor = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
            print(f"   Found {len(rows_with_mor)} rows with MOR ID")

            for row in rows_with_mor[:3]:  # Process first 3
                ms_data = {
                    "category": cat["text"],
                    "row_text": row.text[:500]
                }

                # Extract manuscript ID
                mor_match = re.search(r'MOR-\d{4}-\d{4}', row.text)
                if mor_match:
                    ms_data["manuscript_id"] = mor_match.group()
                    print(f"\n   📄 Manuscript: {ms_data['manuscript_id']}")

                    # Extract cells
                    cells = row.find_elements(By.TAG_NAME, "td")
                    ms_data["cells"] = []
                    for j, cell in enumerate(cells[:8]):  # First 8 cells
                        text = cell.text.strip()
                        if text:
                            ms_data["cells"].append(text[:100])
                            if j < 4:
                                print(f"      Cell {j}: {text[:50]}...")

                    # Count potential emails
                    email_count = row.text.count('@')
                    ms_data["email_indicators"] = email_count
                    print(f"      Email indicators: {email_count}")

                    manuscripts.append(ms_data)
                    RESULTS["manuscripts"].append(ms_data)

            RESULTS["total_manuscripts"] += len(manuscripts)

            # Try to open first manuscript for details
            if rows_with_mor:
                print("\n   Attempting to open first manuscript...")
                first_row = rows_with_mor[0]

                # Find clickable element
                clicked = False

                # Try manuscript ID link
                try:
                    ms_link = first_row.find_element(By.PARTIAL_LINK_TEXT, "MOR-")
                    ms_link.click()
                    clicked = True
                    print("   Clicked manuscript ID")
                except:
                    pass

                # Try view icon
                if not clicked:
                    try:
                        icons = first_row.find_elements(By.TAG_NAME, "img")
                        for icon in icons:
                            if 'view' in icon.get_attribute('src').lower() or 'check' in icon.get_attribute('src').lower():
                                icon.click()
                                clicked = True
                                print("   Clicked view icon")
                                break
                    except:
                        pass

                if clicked:
                    time.sleep(5)

                    # Check for popup
                    if len(driver.window_handles) > 1:
                        print("   ✅ Popup opened")
                        original = driver.current_window_handle
                        driver.switch_to.window(driver.window_handles[-1])

                        # Extract popup data
                        popup_text = driver.find_element(By.TAG_NAME, "body").text
                        print(f"   Popup text length: {len(popup_text)}")

                        # Extract key details
                        details = {}

                        # Title
                        if "Title" in popup_text:
                            title_match = re.search(r'Title[:\s]*(.+?)[\n\r]', popup_text, re.IGNORECASE)
                            if title_match:
                                details["title"] = title_match.group(1)[:200]
                                print(f"   Title: {details['title'][:100]}...")

                        # Emails
                        emails = re.findall(r'[\w.+-]+@[\w.-]+\.\w+', popup_text)
                        details["emails"] = list(set(emails))
                        print(f"   Unique emails: {len(details['emails'])}")
                        for email in details["emails"][:5]:
                            print(f"      - {email}")

                        # Referee status counts
                        for status in ['Invited', 'Agreed', 'Declined', 'Complete', 'Pending']:
                            count = popup_text.count(status)
                            if count > 0:
                                details[f"status_{status.lower()}"] = count
                                print(f"   {status}: {count}")

                        # Add details to last manuscript
                        if RESULTS["manuscripts"]:
                            RESULTS["manuscripts"][-1]["details"] = details

                        # Close popup
                        driver.close()
                        driver.switch_to.window(original)
                        print("   ✅ Popup closed")

            # Return to AE Center
            driver.get("https://mc.manuscriptcentral.com/mathor")
            time.sleep(3)
            ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Editor")
            ae_link.click()
            time.sleep(3)

        except Exception as e:
            print(f"   ❌ Error in category: {e}")

    # 9. Final Summary
    print("\n" + "="*80)
    print("📊 EXTRACTION COMPLETE - DETAILED RESULTS")
    print("="*80)

    print(f"\n✅ Login successful: {RESULTS['login_successful']}")
    print(f"✅ Categories found: {len(RESULTS['categories_found'])}")
    for cat in RESULTS['categories_found']:
        print(f"   - {cat}")

    print(f"\n✅ Total manuscripts extracted: {RESULTS['total_manuscripts']}")

    for i, ms in enumerate(RESULTS["manuscripts"], 1):
        print(f"\n📄 Manuscript {i}:")
        print(f"   Category: {ms.get('category')}")
        print(f"   ID: {ms.get('manuscript_id', 'Unknown')}")
        print(f"   Email indicators: {ms.get('email_indicators', 0)}")

        if "details" in ms:
            print("   📋 Detailed extraction:")
            if "title" in ms["details"]:
                print(f"      Title: {ms['details']['title'][:100]}...")
            if "emails" in ms["details"]:
                print(f"      Emails: {len(ms['details']['emails'])}")
                for email in ms["details"]["emails"][:3]:
                    print(f"         - {email}")
            for status in ['invited', 'agreed', 'declined', 'complete']:
                key = f"status_{status}"
                if key in ms["details"]:
                    print(f"      {status.capitalize()}: {ms['details'][key]}")

    # Save results
    output_file = f"/tmp/mor_working_extraction_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\n💾 Full results saved to: {output_file}")

except Exception as e:
    print(f"\n❌ FATAL ERROR: {e}")
    import traceback
    traceback.print_exc()

    if driver:
        driver.save_screenshot("/tmp/mor_error_final.png")
        print("Error screenshot: /tmp/mor_error_final.png")

finally:
    if driver:
        print("\nBrowser will close in 15 seconds...")
        time.sleep(15)
        driver.quit()

print("\n" + "="*80)
print("EXTRACTION TEST COMPLETE")
print("="*80)