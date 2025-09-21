#!/usr/bin/env python3
"""
MOR CLEAN EXTRACTION - GET ACTUAL MANUSCRIPT DATA
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
print("🎯 MOR CLEAN EXTRACTION - GETTING ACTUAL DATA")
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
    # 1. Setup Browser
    print("\n1. Browser Setup")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 15)
    print("   ✅ Chrome ready")

    # 2. Navigate to MOR
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
    wait.until(EC.presence_of_element_located((By.ID, "USERID")))

    userid_field = driver.find_element(By.ID, "USERID")
    password_field = driver.find_element(By.ID, "PASSWORD")

    userid_field.clear()
    userid_field.send_keys(os.getenv('MOR_EMAIL'))
    password_field.clear()
    password_field.send_keys(os.getenv('MOR_PASSWORD'))

    login_timestamp = time.time()
    login_btn = driver.find_element(By.ID, "logInButton")
    login_btn.click()
    print(f"   ✅ Login clicked at {time.strftime('%H:%M:%S')}")

    time.sleep(5)

    # 4. Handle 2FA
    print("\n4. 2FA Handling")

    if "TOKEN_VALUE" in driver.page_source or "verification" in driver.page_source.lower():
        print("   2FA detected")
        print("   ⏳ Waiting 15 seconds for NEW 2FA email...")
        time.sleep(15)

        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_timestamp + 5
        )

        if code:
            print(f"   ✅ Got fresh code: {code}")

            # Enter code
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")

            # Click verify
            try:
                verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
                verify_btn.click()
            except:
                driver.execute_script("document.getElementById('VERIFY_BTN').click();")

            print("   Waiting for login to complete...")
            time.sleep(10)
        else:
            raise Exception("No 2FA code received")

    # 5. Verify Login
    print("\n5. Login Verification")

    if "Log In" in driver.title or "login" in driver.current_url.lower():
        # Check for error
        if "verification error" in driver.page_source.lower():
            print("   ❌ 2FA verification failed!")
            driver.save_screenshot("/tmp/mor_2fa_error.png")
        raise Exception("Login failed")

    print("   ✅ Login successful!")
    RESULTS["login_successful"] = True

    # 6. Navigate to AE Center
    print("\n6. Navigate to Associate Editor Center")

    # Find AE Center link
    ae_link = None
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if "associate editor" in link.text.lower() and link.text.strip():
            ae_link = link
            print(f"   Found: {link.text}")
            break

    if ae_link:
        ae_link.click()
        time.sleep(5)
        print("   ✅ In AE Center")

    # 7. Find Categories
    print("\n7. Find Categories")
    categories = []

    for link in driver.find_elements(By.TAG_NAME, "a"):
        text = link.text.strip()
        # ONLY PROCESS "Awaiting Reviewer Reports" - it has the manuscripts
        if text and "Awaiting Reviewer Reports" in text:
            categories.append({
                "text": text,
                "element": link
            })
            print(f"   Found: {text}")

    RESULTS["categories_found"] = [c["text"] for c in categories]

    # 8. Process Each Category
    print("\n8. Extract Manuscripts from Categories")
    print("-"*60)

    for cat in categories:  # Process the category with manuscripts
        print(f"\n📂 Category: {cat['text']}")

        # Click on category link
        cat["element"].click()
        time.sleep(5)

        # Find manuscript rows
        manuscript_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
        print(f"   Found {len(manuscript_rows)} manuscripts")

        # Process first 2 manuscripts
        for i, row in enumerate(manuscript_rows[:2], 1):
            # Extract manuscript ID
            row_text = row.text
            mor_match = re.search(r'MOR-\d{4}-\d+', row_text)

            if mor_match:
                manuscript_id = mor_match.group()
                print(f"\n   📄 Manuscript {i}: {manuscript_id}")

                manuscript_data = {
                    "manuscript_id": manuscript_id,
                    "category": cat["text"],
                    "row_text": row_text[:300]
                }

                # Try to click on manuscript
                try:
                    # Find clickable element - prefer "Take Action" button
                    take_action = None
                    try:
                        take_action = row.find_element(By.XPATH, ".//a[contains(text(), 'Take Action')]")
                    except:
                        # Try check icon
                        try:
                            take_action = row.find_element(By.XPATH, ".//img[contains(@src, 'check')]/parent::*")
                        except:
                            # Try manuscript ID link
                            try:
                                take_action = row.find_element(By.PARTIAL_LINK_TEXT, manuscript_id)
                            except:
                                pass

                    if take_action:
                        # Store current window
                        main_window = driver.current_window_handle

                        # Click to open manuscript
                        take_action.click()
                        time.sleep(5)

                        # Check if popup opened
                        if len(driver.window_handles) > 1:
                            print("      ✅ Opened manuscript details")

                            # Switch to popup
                            for window in driver.window_handles:
                                if window != main_window:
                                    driver.switch_to.window(window)
                                    break

                            # Extract data from popup
                            popup_text = driver.find_element(By.TAG_NAME, "body").text

                            # Extract title
                            title_match = re.search(r'Title[:\s]+(.+?)[\n\r]', popup_text, re.IGNORECASE)
                            if title_match:
                                manuscript_data["title"] = title_match.group(1)[:200]
                                print(f"      Title: {manuscript_data['title'][:80]}...")

                            # Extract emails
                            emails = re.findall(r'[\w.+-]+@[\w.-]+\.[a-z]+', popup_text, re.IGNORECASE)
                            if emails:
                                manuscript_data["emails_found"] = len(set(emails))
                                manuscript_data["sample_emails"] = list(set(emails))[:3]
                                print(f"      Emails found: {manuscript_data['emails_found']}")

                            # Look for referee information
                            referee_count = 0
                            for status in ['Invited', 'Agreed', 'Declined', 'Complete']:
                                count = popup_text.count(status)
                                if count > 0:
                                    manuscript_data[f"referee_{status.lower()}"] = count
                                    referee_count += count

                            if referee_count > 0:
                                print(f"      Referees: {referee_count} total")

                            # Look for author info
                            if "Author" in popup_text:
                                manuscript_data["has_author_info"] = True
                                print("      Has author information")

                            # Close popup and return to main window
                            driver.close()
                            driver.switch_to.window(main_window)
                        else:
                            print("      ⚠️ Manuscript opened in same window")

                            # Extract from current page
                            page_text = driver.find_element(By.TAG_NAME, "body").text

                            # Extract basic info
                            if "Title" in page_text:
                                title_match = re.search(r'Title[:\s]+(.+?)[\n\r]', page_text, re.IGNORECASE)
                                if title_match:
                                    manuscript_data["title"] = title_match.group(1)[:200]
                                    print(f"      Title: {manuscript_data['title'][:80]}...")

                            # Navigate back to AE Center then category
                            driver.get("https://mc.manuscriptcentral.com/mathor")
                            time.sleep(3)
                            # Find and click AE Center again
                            for link in driver.find_elements(By.TAG_NAME, "a"):
                                if "associate editor" in link.text.lower():
                                    link.click()
                                    time.sleep(3)
                                    break
                            # Click category again
                            for link in driver.find_elements(By.TAG_NAME, "a"):
                                if cat["text"] in link.text:
                                    link.click()
                                    time.sleep(3)
                                    break

                except Exception as e:
                    print(f"      ❌ Error opening manuscript: {str(e)[:100]}")

                RESULTS["manuscripts"].append(manuscript_data)
                RESULTS["total_manuscripts"] += 1

    # 9. Summary
    print("\n" + "="*80)
    print("📊 EXTRACTION COMPLETE - ACTUAL DATA")
    print("="*80)

    print(f"\n✅ Login successful: {RESULTS['login_successful']}")
    print(f"✅ Categories found: {len(RESULTS['categories_found'])}")
    for cat in RESULTS['categories_found']:
        print(f"   - {cat}")

    print(f"\n✅ Total manuscripts extracted: {RESULTS['total_manuscripts']}")

    for ms in RESULTS["manuscripts"]:
        print(f"\n📄 {ms['manuscript_id']} ({ms['category']})")
        if "title" in ms:
            print(f"   Title: {ms['title'][:100]}...")
        if "emails_found" in ms:
            print(f"   Emails: {ms['emails_found']} found")
            if "sample_emails" in ms:
                for email in ms["sample_emails"][:2]:
                    print(f"      - {email}")
        if any(k.startswith("referee_") for k in ms):
            print("   Referee status:")
            for status in ['invited', 'agreed', 'declined', 'complete']:
                key = f"referee_{status}"
                if key in ms:
                    print(f"      {status.capitalize()}: {ms[key]}")

    # Save results
    output_file = f"/tmp/mor_clean_extraction_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

    if driver:
        driver.save_screenshot("/tmp/mor_clean_error.png")
        print("Screenshot saved: /tmp/mor_clean_error.png")

finally:
    if driver:
        print("\nClosing in 10 seconds...")
        time.sleep(10)
        driver.quit()

print("\n" + "="*80)
print("CLEAN EXTRACTION COMPLETE")
print("="*80)