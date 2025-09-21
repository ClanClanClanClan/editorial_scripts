#!/usr/bin/env python3
"""
MOR COMPLETE EXTRACTION - GET THE TWO MANUSCRIPTS
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
from selenium.webdriver.common.keys import Keys

from core.gmail_verification import fetch_latest_verification_code

print("="*80)
print("🎯 MOR COMPLETE EXTRACTION - GET THE TWO MANUSCRIPTS")
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
    wait = WebDriverWait(driver, 15)
    print("   ✅ Chrome ready")

    # 2. Navigate
    print("\n2. Navigate to MOR")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(5)

    # Handle cookies first
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
        reject.click()
        time.sleep(2)
        print("   ✅ Cookies rejected")
    except:
        print("   No cookie banner")

    # Wait for page to load
    time.sleep(3)

    # 3. Login
    print("\n3. Login Process")
    print("-"*40)

    wait.until(EC.presence_of_element_located((By.ID, "USERID")))
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    login_time = time.time()
    driver.find_element(By.ID, "logInButton").click()
    print("   ✅ Credentials submitted")

    # 4. Handle 2FA
    print("\n4. 2FA Handling")
    print("-"*40)

    time.sleep(5)

    if "verification" in driver.page_source.lower() or "TOKEN_VALUE" in driver.page_source:
        print("   ✅ 2FA dialog detected")

        # Get fresh code
        print("   Fetching verification code...")
        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_time
        )

        if code:
            print(f"   ✅ Got code: {code}")

            # Enter code
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            print("   ✅ Code entered")

            # Click Verify button
            try:
                verify_btn = driver.find_element(By.XPATH, "//button[contains(., 'Verify')]")
                driver.execute_script("arguments[0].click();", verify_btn)
                print("   ✅ Clicked Verify button")
            except:
                # Fallback: press Enter
                token_field = driver.find_element(By.ID, "TOKEN_VALUE")
                token_field.send_keys(Keys.RETURN)
                print("   ✅ Submitted with Enter key")

            time.sleep(10)
        else:
            print("   ❌ No code received!")
            raise Exception("No 2FA code")

    # 5. Check login success
    print("\n5. Login Verification")
    print("-"*40)

    current_url = driver.current_url
    print(f"   Current URL: {current_url}")

    # Check if 2FA dialog is gone
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        if token_field.is_displayed():
            print("   ❌ 2FA still visible - verification failed")
            # Try with another code or resend
    except:
        print("   ✅ 2FA dialog closed")
        RESULTS["login_successful"] = True

    # 6. Navigate to AE Center
    print("\n6. Navigate to Associate Editor Center")
    print("-"*40)

    # Wait for page to load
    time.sleep(5)

    # Find AE Center link
    ae_link = None
    all_links = driver.find_elements(By.TAG_NAME, "a")

    for link in all_links:
        text = link.text.strip()
        if text and "associate editor" in text.lower():
            ae_link = link
            print(f"   ✅ Found: {text}")
            break

    if not ae_link:
        print("   ❌ No AE link found")
        print("   Available links:")
        for i, link in enumerate(all_links[:20], 1):
            if link.text.strip():
                print(f"   {i}. {link.text}")
    else:
        ae_link.click()
        time.sleep(5)
        print("   ✅ In AE Center")

        # 7. Find categories
        print("\n7. Find Manuscript Categories")
        print("-"*40)

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

        # 8. Extract manuscripts
        print("\n8. Extract Manuscripts")
        print("-"*40)

        for i, cat in enumerate(categories[:2], 1):  # First 2 categories
            print(f"\nCategory {i}: {cat['text']}")

            try:
                # Navigate to category
                driver.get(cat["href"])
                time.sleep(5)

                # Find manuscript rows
                rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
                print(f"   Found {len(rows)} manuscripts")

                for j, row in enumerate(rows[:2], 1):  # First 2 per category
                    ms_data = {
                        "category": cat["text"],
                        "row_number": j
                    }

                    # Extract ID
                    mor_match = re.search(r'MOR-\d{4}-\d{4}', row.text)
                    if mor_match:
                        ms_data["manuscript_id"] = mor_match.group()
                        print(f"\n   📄 Manuscript: {ms_data['manuscript_id']}")

                    # Extract cells
                    cells = row.find_elements(By.TAG_NAME, "td")
                    ms_data["cells"] = []
                    for k, cell in enumerate(cells[:6]):
                        text = cell.text.strip()
                        if text:
                            ms_data["cells"].append(text[:100])
                            if k < 4:
                                print(f"      Cell {k}: {text[:50]}...")

                    # Try to open popup
                    try:
                        # Click manuscript ID or view icon
                        ms_link = row.find_element(By.PARTIAL_LINK_TEXT, "MOR-")
                        ms_link.click()
                        time.sleep(5)

                        # Check for popup
                        if len(driver.window_handles) > 1:
                            print("      ✅ Popup opened")
                            original = driver.current_window_handle
                            driver.switch_to.window(driver.window_handles[-1])

                            # Extract popup data
                            popup_text = driver.find_element(By.TAG_NAME, "body").text

                            # Extract title
                            title_match = re.search(r'Title[:\s]*(.+?)[\n\r]', popup_text, re.IGNORECASE)
                            if title_match:
                                ms_data["title"] = title_match.group(1)[:200]
                                print(f"      Title: {ms_data['title'][:80]}...")

                            # Extract emails
                            emails = re.findall(r'[\w.+-]+@[\w.-]+\.[\w]+', popup_text)
                            ms_data["emails"] = list(set(emails))
                            print(f"      Emails: {len(ms_data['emails'])}")
                            for email in ms_data["emails"][:3]:
                                print(f"         - {email}")

                            # Count referee statuses
                            for status in ['Invited', 'Agreed', 'Declined', 'Complete']:
                                count = popup_text.count(status)
                                if count > 0:
                                    ms_data[f"referee_{status.lower()}"] = count
                                    print(f"      Referee {status}: {count}")

                            # Close popup
                            driver.close()
                            driver.switch_to.window(original)
                    except:
                        print("      Could not open popup")

                    RESULTS["manuscripts"].append(ms_data)
                    RESULTS["total_manuscripts"] += 1

                # Return to AE Center
                driver.get("https://mc.manuscriptcentral.com/mathor")
                time.sleep(3)
                try:
                    ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Editor")
                    ae_link.click()
                    time.sleep(3)
                except:
                    pass

            except Exception as e:
                print(f"   Error in category: {e}")

    # 9. Summary
    print("\n" + "="*80)
    print("📊 EXTRACTION COMPLETE - RESULTS")
    print("="*80)

    print(f"\n✅ Login successful: {RESULTS['login_successful']}")
    print(f"✅ Categories found: {len(RESULTS['categories_found'])}")
    for cat in RESULTS["categories_found"]:
        print(f"   - {cat}")

    print(f"\n✅ Total manuscripts extracted: {RESULTS['total_manuscripts']}")

    for i, ms in enumerate(RESULTS["manuscripts"], 1):
        print(f"\n📄 Manuscript {i}:")
        print(f"   Category: {ms.get('category')}")
        print(f"   ID: {ms.get('manuscript_id', 'Unknown')}")
        if "title" in ms:
            print(f"   Title: {ms['title'][:100]}...")
        if "emails" in ms:
            print(f"   Emails: {len(ms['emails'])}")
        for status in ['invited', 'agreed', 'declined', 'complete']:
            key = f"referee_{status}"
            if key in ms:
                print(f"   Referee {status}: {ms[key]}")

    # Save results
    output_file = f"/tmp/mor_complete_extraction_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    if driver:
        driver.save_screenshot("/tmp/mor_complete_error.png")

finally:
    if driver:
        print("\nClosing in 15 seconds...")
        time.sleep(15)
        driver.quit()

print("\n" + "="*80)
print("COMPLETE")
print("="*80)